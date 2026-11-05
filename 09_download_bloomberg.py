"""Download from Bloomberg the semiconductor universe of the transfer test, without survivorship bias.

Runs only on a PC with the Bloomberg Terminal open and logged in (Desktop API, localhost:8194). It is not part of the
uv environment: on that PC install `pip install pandas pyarrow` and
`pip install blpapi --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/`.
Its outputs are copied to data/bloomberg/ and read from there: the results are reproducible without a terminal.

What it downloads (each run writes a folder, --out):
    membership.csv         members of the SOX index (PHLX Semiconductor) and their weights at the end of every year
                           (member as Bloomberg gives it, e.g. "MU UN", and its composite ticker "MU US Equity"):
                           who was in the index at each date, so that a stock enters the test only after it entered
                           the index (the union of all members would bring back future winners)
    universe.csv, meta.csv every stock ever a member, with name, ISIN, sub-industry, country, currency, market status
                           (check the names: a ticker of a delisted company can be reused by another one)
    prices.parquet         daily open, high, low, close, volume adjusted for splits and dividends, and the total
                           return index of Bloomberg (to check the adjustment)
    prices_raw.parquet     daily close not adjusted at all (to check splits and dividends)
    actions.parquet        dividends and splits (DVD_HIST_ALL), with ex-date, amount and type
    monthly.parquet        monthly market value and P/E, trailing and forward (context only, never a signal)
    benchmark_sox.parquet  the SOX index, price and total return
    failed.txt             tickers or fields without data (only if any)

Prices are downloaded for the composite ticker (US): one series per company, also across a change of exchange.

Examples:
    python 09_download_bloomberg.py --tickers "MU US Equity" "9966620D US Equity" --out bloomberg_test   # quick test
    python 09_download_bloomberg.py --membership-only --out bloomberg_members                        # only who/when
    python 09_download_bloomberg.py --out bloomberg_data                                              # full universe
    python 09_download_bloomberg.py --lite --out bloomberg_data                       # the same with open/close only
    python 09_download_bloomberg.py --tickers "AAPL US Equity" "MSFT US Equity" "AMZN US Equity" \\
        "GOOG US Equity" "SPY US Equity" --out bloomberg_check                                        # Yahoo cross-check
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

import blpapi
import pandas as pd

HOST, PORT = "localhost", 8194
INDEX = "SOX Index"  # PHLX Semiconductor Index
DAILY_FIELDS = ["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME", "TOT_RETURN_INDEX_GROSS_DVDS"]
MONTHLY_FIELDS = ["CUR_MKT_CAP", "PE_RATIO", "BEST_PE_RATIO"]
REF_FIELDS = ["NAME", "ID_ISIN", "GICS_SUB_INDUSTRY_NAME", "COUNTRY_ISO", "CRNCY", "MARKET_STATUS"]
CHUNK = 20  # securities per request
MAX_TIMEOUTS = 30  # x 10 s of waiting for a response


# ---------------------------------------------------------------- session
def open_session():
    opts = blpapi.SessionOptions()
    opts.setServerHost(HOST)
    opts.setServerPort(PORT)
    session = blpapi.Session(opts)
    if not session.start():
        sys.exit("Connection failed: is the Terminal open and logged in?")
    if not session.openService("//blp/refdata"):
        sys.exit("Cannot open //blp/refdata")
    return session, session.getService("//blp/refdata")


def collect(session):
    """All the messages of one request, up to its final RESPONSE."""
    messages, timeouts = [], 0
    while True:
        event = session.nextEvent(10_000)
        if event.eventType() == blpapi.Event.TIMEOUT:
            timeouts += 1
            if timeouts > MAX_TIMEOUTS:
                raise TimeoutError("No answer from Bloomberg")
            continue
        messages.extend(event)
        if event.eventType() == blpapi.Event.RESPONSE:
            return messages


def value(element):
    return None if element.isNull() else element.getValue()


def bulk_rows(field_data, field: str) -> list[dict]:
    """Rows of a bulk field (a table), with the column names given by Bloomberg."""
    if not field_data.hasElement(field):
        return []
    bulk = field_data.getElement(field)
    rows = []
    for i in range(bulk.numValues()):
        row = bulk.getValueAsElement(i)
        rows.append({str(row.getElement(k).name()): value(row.getElement(k)) for k in range(row.numElements())})
    return rows


def reference_request(session, svc, securities: list[str], fields: list[str], overrides: dict | None = None):
    """ReferenceDataRequest: yields (security, fieldData) for every security."""
    for k in range(0, len(securities), CHUNK):
        req = svc.createRequest("ReferenceDataRequest")
        for s in securities[k : k + CHUNK]:
            req.getElement("securities").appendValue(s)
        for f in fields:
            req.getElement("fields").appendValue(f)
        for field_id, v in (overrides or {}).items():
            ov = req.getElement("overrides").appendElement()
            ov.setElement("fieldId", field_id)
            ov.setElement("value", v)
        session.sendRequest(req)
        for m in collect(session):
            if not m.hasElement("securityData"):
                continue
            data = m.getElement("securityData")
            for i in range(data.numValues()):
                sd = data.getValueAsElement(i)
                yield sd.getElementAsString("security"), sd.getElement("fieldData")


# ---------------------------------------------------------------- universe
def composite(member: str) -> str:
    """ "MU UN" (NYSE) or "MU UW" (Nasdaq) -> "MU US Equity": the composite ticker follows a company across exchanges
    (Micron moved from NYSE to Nasdaq in 2009), so that each company has one price series, not one per exchange."""
    return f"{member.split()[0]} US Equity"


def membership(session, svc, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Members of the index and their weights at the end of every year, and today."""
    rows = []
    dates = [min(dt.date(y, 12, 31), end) for y in range(start.year, end.year + 1)]
    for d in dates:
        for _, fd in reference_request(session, svc, [INDEX], ["INDX_MWEIGHT_HIST"], {"END_DATE_OVERRIDE": d.strftime("%Y%m%d")}):
            for r in bulk_rows(fd, "INDX_MWEIGHT_HIST"):
                values = list(r.values())  # "Index Member", "Percent Weight"
                member = str(values[0]).strip()
                rows.append(
                    {"date": d, "member": member, "ticker": composite(member), "weight": values[1] if len(values) > 1 else None}
                )
        print(f"  members on {d}: {sum(1 for r in rows if r['date'] == d)}")
    for _, fd in reference_request(session, svc, [INDEX], ["INDX_MEMBERS"]):
        for r in bulk_rows(fd, "INDX_MEMBERS"):
            member = str(next(iter(r.values()))).strip()
            rows.append({"date": dt.date.today(), "member": member, "ticker": composite(member), "weight": None})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- data
def history(session, svc, tickers, fields, start, end, periodicity="DAILY", adjusted=True):
    """HistoricalDataRequest, one row per security and date. The adjustment is set explicitly: with
    adjustmentFollowDPDF left to its default (True) Bloomberg would follow the settings of whoever is logged in."""
    rows, failed = [], []
    for k in range(0, len(tickers), CHUNK):
        chunk = tickers[k : k + CHUNK]
        print(f"History {periodicity.lower()}{'' if adjusted else ' (not adjusted)'}: {k + 1}-{k + len(chunk)} of {len(tickers)}")
        req = svc.createRequest("HistoricalDataRequest")
        for t in chunk:
            req.getElement("securities").appendValue(t)
        for f in fields:
            req.getElement("fields").appendValue(f)
        req.set("startDate", start.strftime("%Y%m%d"))
        req.set("endDate", end.strftime("%Y%m%d"))
        req.set("periodicitySelection", periodicity)
        req.set("nonTradingDayFillOption", "ACTIVE_DAYS_ONLY")
        req.set("adjustmentFollowDPDF", False)
        req.set("adjustmentSplit", adjusted)
        req.set("adjustmentNormal", adjusted)
        req.set("adjustmentAbnormal", adjusted)
        session.sendRequest(req)

        for m in collect(session):
            if m.hasElement("responseError"):
                print("  error:", m.getElement("responseError"))
                continue
            if not m.hasElement("securityData"):
                continue
            sd = m.getElement("securityData")
            ticker = sd.getElementAsString("security")
            if sd.hasElement("securityError"):
                failed.append(f"{ticker}: no such security")
                continue
            if sd.hasElement("fieldExceptions"):
                exceptions = sd.getElement("fieldExceptions")
                for i in range(exceptions.numValues()):
                    fe = exceptions.getValueAsElement(i)
                    failed.append(f"{ticker}: field {fe.getElementAsString('fieldId')} not available")
            fd = sd.getElement("fieldData")
            for i in range(fd.numValues()):
                point = fd.getValueAsElement(i)
                rec = {"ticker": ticker}
                for j in range(point.numElements()):
                    e = point.getElement(j)
                    rec[str(e.name())] = value(e)
                rows.append(rec)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    return df, failed


def save(df: pd.DataFrame, path: Path) -> None:
    try:
        df.to_parquet(path.with_suffix(".parquet"), index=False)
        print(f"Saved {path.with_suffix('.parquet')}: {len(df)} rows")
    except ImportError:
        df.to_csv(path.with_suffix(".csv"), index=False)
        print(f"Saved {path.with_suffix('.csv')} (pyarrow missing): {len(df)} rows")


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2000-01-01")
    ap.add_argument("--end", default=dt.date.today().isoformat())
    ap.add_argument("--tickers", nargs="*", help="manual list instead of the SOX members (no membership.csv)")
    ap.add_argument("--out", default="bloomberg_data")
    ap.add_argument("--membership-only", action="store_true", help="only membership.csv, universe.csv, meta.csv: very few data")
    ap.add_argument("--lite", action="store_true", help="daily open, close and total return only (fewer data than OHLCV)")
    a = ap.parse_args()

    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    session, svc = open_session()
    failed = []
    try:
        if a.tickers:
            tickers = sorted(a.tickers)
        else:
            members = membership(session, svc, start, end)
            members.to_csv(out / "membership.csv", index=False)
            tickers = sorted(members["ticker"].unique())
            print(f"Universe: {len(tickers)} stocks ever in {INDEX} from {start.year}")
        pd.Series(tickers, name="ticker").to_csv(out / "universe.csv", index=False)

        meta = [
            {"ticker": t, **{f: (fd.getElementAsString(f) if fd.hasElement(f) else None) for f in REF_FIELDS}}
            for t, fd in reference_request(session, svc, tickers, REF_FIELDS)
        ]
        pd.DataFrame(meta).to_csv(out / "meta.csv", index=False)
        print(f"Saved {out / 'meta.csv'}: check the names, a delisted ticker can be reused by another company")
        if a.membership_only:
            return

        fields = ["PX_OPEN", "PX_LAST", "TOT_RETURN_INDEX_GROSS_DVDS"] if a.lite else DAILY_FIELDS
        prices, f1 = history(session, svc, tickers, fields, start, end)
        save(prices, out / "prices")
        raw, f2 = history(session, svc, tickers, ["PX_LAST"], start, end, adjusted=False)
        save(raw, out / "prices_raw")
        monthly, f3 = history(session, svc, tickers, MONTHLY_FIELDS, start, end, periodicity="MONTHLY")
        save(monthly, out / "monthly")
        failed += f1 + f2 + f3

        actions = [
            {"ticker": t, **r}
            for t, fd in reference_request(session, svc, tickers, ["DVD_HIST_ALL"])
            for r in bulk_rows(fd, "DVD_HIST_ALL")
        ]
        save(pd.DataFrame(actions), out / "actions")

        bench, f4 = history(session, svc, [INDEX], ["PX_LAST", "TOT_RETURN_INDEX_GROSS_DVDS"], start, end)
        save(bench, out / "benchmark_sox")
        failed += f4

        (out / "download.txt").write_text(f"downloaded {dt.date.today()} from {start} to {end}\n")
        print(f"Daily prices: {prices['ticker'].nunique() if not prices.empty else 0} stocks, {len(prices)} rows")
        if failed:
            failed = list(dict.fromkeys(failed))  # once each
            (out / "failed.txt").write_text("\n".join(failed) + "\n")
            print(f"{len(failed)} problems -> {out / 'failed.txt'}")
    finally:
        session.stop()


if __name__ == "__main__":
    main()

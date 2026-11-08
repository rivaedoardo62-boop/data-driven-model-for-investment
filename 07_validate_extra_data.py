"""Validate the macro series downloaded by 06_download_extra_data.py: stop if a check fails, report the warnings.

Checks (src/validation.py): coverage of the period, gaps (a month missing at the source is reported, not failed, when it
is a known gap), plausible range of the values.

Input:  data/extra/macro/
Output: data/extra/validation/checks.csv, one row per check and series
"""

from src.config import ROOT, check_used, load_config
from src.data import macro_start
from src.validation import validate_macro


def main() -> None:
    cfg = load_config()
    data, extra = cfg["data"], cfg["extra"]
    extra_dir = ROOT / data["data_dir"] / "extra"
    check_used({"start": data["start"], "end": data["end"], **extra}, extra_dir / "config.yaml", "06_download_extra_data.py")

    checks = validate_macro(extra_dir / "macro", extra["macro"], macro_start(data["start"]), data["end"])
    out = extra_dir / "validation" / "checks.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    checks.to_csv(out, index=False)
    print(checks.to_string(index=False))
    print(f"\nSaved {out.relative_to(ROOT)}")
    failed = checks[checks["result"] == "FAIL"]
    if not failed.empty:
        raise ValueError(f"{len(failed)} checks failed: see {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

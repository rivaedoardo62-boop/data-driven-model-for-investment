# Bloomberg data (not on GitHub)

Bloomberg data are licensed and this repository is public: everything in this folder except this file is ignored by git.
Keep the files on your computer and include them in the submitted zip.

| Folder | Content | Written by |
|---|---|---|
| `raw/` | Files of `09_download_bloomberg.py`, copied from the terminal PC: `prices.parquet` (required), and when available `membership.csv`, `meta.csv`, `benchmark_sox.parquet`, `prices_raw.parquet`, `actions.parquet`, `monthly.parquet` | you |
| `clean/` | One price series per company, weekly tables, feature panel, checks | `10_clean_bloomberg.py` |
| `eda/` | Exploratory figures and tables | `11_eda_bloomberg.py` |

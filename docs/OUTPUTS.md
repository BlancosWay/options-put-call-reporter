# Outputs and Signals

This guide explains generated files, report fields, data-source fallback behavior, and diagnostic artifacts.

## What this produces

A run creates a dated archive folder and writes a human-readable report plus raw diagnostics:

```text
archive/YYYY-MM-DD/
|-- report.html
|-- report.md
|-- META-expirations.csv
|-- META-snapshot.json
|-- META-raw.json
`-- META-raw.html
```

The HTML report summarizes each symbol with a monthly signal, put/call ratios, drift from prior saved runs, and the data source used for that symbol.

Successful Barchart collection writes `{SYMBOL}-raw.html` and `{SYMBOL}-raw.json`. If Barchart extraction fails before fallback succeeds or the symbol fails completely, failure diagnostics are written as `{SYMBOL}-failure.html` and `{SYMBOL}-failure.png`.

## How to read the signal

| Field | Meaning |
| --- | --- |
| Put/call ratio | Compares put activity to call activity. Higher values are more put-heavy; lower values are more call-heavy. |
| Monthly signal | Classifies monthly expiration rows as bullish, bearish, or neutral using the reporter's ratio thresholds. |
| Drift | Compares the current snapshot with prior history in `data/history.sqlite3` when enough previous data exists. |
| Data source | Shows whether a symbol used Barchart primary data or yfin.dev fallback data. |

Use the report as options-sentiment research, not as a trade recommendation.

## Data sources and fallback behavior

| Source | When used | What it provides | Archive files |
| --- | --- | --- | --- |
| Barchart | Primary source for each symbol | Put/call rows plus Barchart-only top metrics such as IV Rank and IV Percentile | `{SYMBOL}-raw.html`, `{SYMBOL}-raw.json` |
| yfin.dev | Fallback when Barchart collection raises a collection error | Expiration-level put/call volume and open-interest ratios; no Barchart-only top metrics | `{SYMBOL}-yfin-raw.json` |

Barchart collection uses Playwright Chromium through `src/reporter/collector.py`. If Barchart collection fails for a symbol, the tool falls back to the free yfin.dev options-chain API. Reports disclose the data source used for each symbol.

yfin.dev is a third-party fallback source. Treat its availability and field coverage as best-effort, and verify important market data independently.

## Output reference

By default, reports and raw collection artifacts are written under `archive/YYYY-MM-DD/`:

| Path | Purpose |
| --- | --- |
| `report.html` | Polished dashboard report. |
| `report.md` | Markdown report. |
| `{SYMBOL}-expirations.csv` | Raw expiration table. |
| `{SYMBOL}-snapshot.json` | Normalized snapshot. |
| `{SYMBOL}-raw.json` and `{SYMBOL}-raw.html` | Collection diagnostics for successful Barchart collection. |
| `{SYMBOL}-failure.html` and `{SYMBOL}-failure.png` | Barchart extraction failure diagnostics. |
| `{SYMBOL}-yfin-raw.json` | Fallback yfin.dev raw responses, written only when yfin.dev fallback is used. |
| `data/history.sqlite3` | SQLite history database used for drift. |

`data/history.sqlite3` is stored under `data/`, not inside the dated archive directory.

## Troubleshooting output artifacts

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Barchart collection fails for one symbol | Barchart page or network response failed | Inspect `archive/YYYY-MM-DD/{SYMBOL}-failure.html` and `{SYMBOL}-failure.png`; if fallback succeeds, also inspect `{SYMBOL}-yfin-raw.json`. |
| Report uses yfin.dev fallback | Barchart failed and fallback succeeded | Check the report data-source disclosure and `{SYMBOL}-yfin-raw.json`; Barchart-only IV Rank/Percentile metrics may be unavailable. |

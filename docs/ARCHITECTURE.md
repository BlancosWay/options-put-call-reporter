# Architecture

`options-put-call-report` is a local Python CLI that collects options put/call data, normalizes it into snapshots, analyzes monthly sentiment, stores history, renders reports, and can email the results.

## Runtime flow

1. `src/reporter/cli.py` handles CLI orchestration: command-line arguments, symbol loading, history setup, collection, report rendering, and optional email.
2. `src/reporter/collector.py` collects each symbol.
3. `src/reporter/analyzer.py` classifies expiration rows into research-oriented sentiment signals.
4. `src/reporter/history.py` persists snapshots in `data/history.sqlite3`.
5. `src/reporter/drift.py` compares current snapshots with prior saved rows.
6. `src/reporter/reporting.py` renders HTML, Markdown, and CSV files under `archive/YYYY-MM-DD/`.
7. `src/reporter/emailer.py` sends the HTML report when email is enabled.

## Collection and data sources

### Barchart primary collection

Barchart primary collection uses Playwright Chromium through `src/reporter/collector.py`. Successful extraction archives raw captures as `{SYMBOL}-raw.html` and `{SYMBOL}-raw.json`.

If Barchart extraction fails, the collector writes failure diagnostics as `{SYMBOL}-failure.html` and `{SYMBOL}-failure.png` before either falling back to yfin.dev or reporting the symbol failure.

### yfin.dev fallback

If Barchart collection raises a collection error for a symbol, `src/reporter/collector.py` falls back to yfin.dev options-chain data. The fallback aggregates contract-level calls and puts into expiration rows and archives `{SYMBOL}-yfin-raw.json`.

The fallback can produce expiration-level put/call volume and open-interest ratios. It does not provide Barchart-only top metrics such as IV Rank or IV Percentile, so reports disclose the source and fallback status.

## Snapshot and source metadata

`src/reporter/models.py` defines the snapshot data model. Each snapshot carries `DataSource` metadata so generated reports and saved history can show whether data came from Barchart or yfin.dev fallback.

`src/reporter/history.py` stores source metadata in SQLite alongside each snapshot. Older history rows default to the Barchart source when metadata is absent.

## Analysis and reporting

`src/reporter/analyzer.py` interprets monthly expiration rows and labels options sentiment as bullish, bearish, or neutral. These labels are research summaries, not financial advice.

`src/reporter/drift.py` compares current ratios with prior history and avoids emitting meaningless infinite or NaN drift text.

`src/reporter/reporting.py` renders:

- `report.html`
- `report.md`
- `{SYMBOL}-expirations.csv`
- `{SYMBOL}-snapshot.json`

Reports include data-source disclosure for every successful symbol.

## Email and scheduler boundaries

Email configuration lives in `config/email.local.json`, while Resend API keys are resolved by `src/reporter/keychain.py` from `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring. Email sending is isolated in `src/reporter/emailer.py`; email failure logs include Resend stage diagnostics such as `stage=send` and HTTP status when available.

The macOS launchd scheduler scripts live under `scripts/`. Scheduled runs write logs to `archive/runner.log`, `archive/launchd.out.log`, and `archive/launchd.err.log`.

## Safe change points

- Change CLI behavior in `src/reporter/cli.py` and update README command examples.
- The `run --open` flag opens the rendered `report.html` in the default browser via the stdlib `webbrowser` module; it is best-effort and never changes the exit code, and scheduled/headless runs do not pass it.
- Change Barchart or yfin.dev parsing only in `src/reporter/collector.py`.
- Change sentiment thresholds in `src/reporter/analyzer.py` and update tests that describe signal meaning.
- Change saved history shape in `src/reporter/history.py` with additive migrations.
- Change report layout in `src/reporter/reporting.py` and update report tests.
- Change assistant guidance in `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.github/instructions/options-reporter.instructions.md`, and `assistant-pack/`.

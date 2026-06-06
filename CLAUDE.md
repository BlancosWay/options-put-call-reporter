# Claude Code Instructions

Use this project as a Python CLI/package. Follow TDD for behavior changes and run `pytest -q` before reporting completion.

## Project context

`options-put-call-report` collects Barchart put/call ratio data with Playwright, analyzes monthly sentiment, stores SQLite history, renders reports, and can send Gmail email through macOS Keychain.

## Locations

- Config: `config/symbols.json`; packaged defaults are used if missing after GitHub install.
- Reports and raw diagnostics: `archive/YYYY-MM-DD/`.
- History: `data/history.sqlite3`.

## CI-equivalent checks

Run `pytest -q` and `python -m build`.

## Maintenance rules

- Keep generated files out of git: `archive/`, `data/`, `config/email.local.json`.
- Use `python -m playwright install chromium` when browser collection fails.
- Keep Barchart parsing changes focused in `src/reporter/collector.py`.
- Do not describe report output as financial advice.
- Update README and assistant-pack docs when CLI behavior changes.

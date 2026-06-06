# Agent Instructions

This repository contains a Python CLI that creates Barchart options put/call sentiment reports. Treat outputs as research summaries, not financial advice.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
```

## Run commands

- Default local report: `options-put-call-report run --no-email`
- Symbol override: `options-put-call-report run --no-email META MSFT NOW`
- Symbol file: `options-put-call-report run --no-email --symbols-file watchlist.txt`
- Email setup: `options-put-call-report setup-email`

## Locations

- Default config: `config/symbols.json`; packaged default config is used when this file is absent.
- Reports and diagnostics: `archive/YYYY-MM-DD/`.
- SQLite history: `data/history.sqlite3`.

## Reference docs

- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release workflow.

## CI-equivalent checks

Run `pytest -q` and `python -m build` before publishing or claiming completion.

## Barchart collection

The collector depends on Playwright Chromium and Barchart put/call pages. Keep Barchart API parsing changes isolated in `src/reporter/collector.py` and preserve archived diagnostics for failures.

## Safety

- Do not commit `archive/`, `data/`, or `config/email.local.json`.
- Gmail App Passwords belong in macOS Keychain.
- Preserve tests for parser, collector, reporting, CLI, history, drift, scheduler, and security behavior.

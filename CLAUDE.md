# Claude Code Instructions

Use this project as a Python CLI/package. Follow TDD for behavior changes and run `pytest -q` before reporting completion.

## Project context

`options-put-call-report` collects Barchart put/call ratio data with Playwright, analyzes monthly sentiment, stores SQLite history, renders reports, and can send Resend email using environment, secret-file, or system-keyring credentials.

## Locations

- Config: `config/symbols.json`; packaged defaults are used if missing after GitHub install.
- Reports and raw diagnostics: `archive/YYYY-MM-DD/`.
- History: `data/history.sqlite3`.

## Reference docs

- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release workflow.

## CI-equivalent checks

Run `pytest -q` and `python -m build`.

## Maintenance rules

- Keep generated files out of git: `archive/`, `data/`, `config/email.local.json`.
- Resend API keys belong in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring; never commit them or ask users to paste them into chat.
- Never ask users to paste Resend API keys into chat.
- Email failure logs include Resend stage diagnostics such as `stage=send` and HTTP status when available.
- Use `python -m playwright install chromium` when browser collection fails.
- Keep Barchart parsing changes focused in `src/reporter/collector.py`.
- Do not describe report output as financial advice.
- Update README and assistant-pack docs when CLI behavior changes.

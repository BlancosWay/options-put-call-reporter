# GitHub Copilot Instructions

This repository builds `options-put-call-report`, a Python CLI for Barchart options put/call sentiment reports.

## Standards

- Follow existing Python dataclass and pytest patterns.
- Run `pytest -q` after changes.
- Run `python -m build` before publishing changes.
- Use Playwright only through existing collector boundaries.
- Keep secrets and generated archives out of git.
- Resend API keys belong in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring; never commit them or ask users to paste them into chat.
- Never ask users to paste Resend API keys into chat.
- Email failure logs include Resend stage diagnostics such as `stage=send` and HTTP status when available.
- Market commentary must say research/sentiment, not financial advice.

## Common commands

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
options-put-call-report run --no-email
pytest -q
```

## Locations

- Config: `config/symbols.json`; packaged defaults are used when the repo config is absent.
- Reports and raw diagnostics: `archive/YYYY-MM-DD/`.
- SQLite history: `data/history.sqlite3`.
- Barchart/Playwright collection code: `src/reporter/collector.py`.
- Architecture guide: `docs/ARCHITECTURE.md`.
- Maintenance guide: `docs/MAINTENANCE.md`.

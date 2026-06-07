# Gemini CLI Instructions

This repository is a Python 3.11+ CLI for Barchart options put/call sentiment reporting.

## Commands

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
options-put-call-report run --no-email
```

## Guidance

- Reports summarize options sentiment and are not financial advice.
- Do not expose Resend API keys; Resend API keys belong in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring; never commit them or ask users to paste them into chat.
- Never ask users to paste Resend API keys into chat.
- Email failure logs include Resend stage diagnostics such as `stage=send` and HTTP status when available.
- Keep local runtime output in ignored paths only.
- Config lives in `config/symbols.json`; reports and diagnostics live in `archive/YYYY-MM-DD/`; history lives in `data/history.sqlite3`.
- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release workflow.
- Run `pytest -q` and `python -m build` before publishing changes.
- Keep Barchart/Playwright collection changes isolated in `src/reporter/collector.py`.

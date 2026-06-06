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
- Do not expose Gmail App Passwords; they are stored in macOS Keychain.
- Keep local runtime output in ignored paths only.
- Config lives in `config/symbols.json`; reports and diagnostics live in `archive/YYYY-MM-DD/`; history lives in `data/history.sqlite3`.
- Run `pytest -q` and `python -m build` before publishing changes.
- Keep Barchart/Playwright collection changes isolated in `src/reporter/collector.py`.

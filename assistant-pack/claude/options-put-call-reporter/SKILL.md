---
name: options-put-call-reporter
description: Use when users want to install, run, schedule, troubleshoot, or maintain the Options Put/Call Reporter CLI.
---

# Options Put/Call Reporter Skill

Help users work with `options-put-call-report`, a Python CLI that collects Barchart put/call ratio data, generates sentiment reports, stores local history, and optionally sends Resend reports.

Supported platforms for this instruction pack are Claude Code, GitHub Copilot, Codex, and Gemini.

## Commands

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
python -m build
options-put-call-report run --no-email
options-put-call-report run --no-email META MSFT NOW
options-put-call-report setup-email
```

## Locations

- Config: `config/symbols.json` with packaged fallback defaults.
- Reports and diagnostics: `archive/YYYY-MM-DD/`.
- History database: `data/history.sqlite3`.

## Rules

- Treat output as options-sentiment research, not financial advice.
- Never ask users to paste Resend API keys into chat.
- Resend API keys belong in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring.
- Use the system keyring on desktop machines and environment variables or secret files for headless servers, containers, and CI.
- Never commit Resend API keys.
- If `setup-email` cannot write to the system keyring, it can reuse an already-readable matching key; otherwise use the sanitized `Keyring error:` detail to diagnose the backend or switch to `RESEND_API_KEY` / `RESEND_API_KEY_FILE`.
- Re-run `options-put-call-report setup-email` if Resend email fails after an older setup; email failure logs include Resend stage diagnostics such as `stage=send` and HTTP status when available.
- Keep `archive/`, `data/`, and `config/email.local.json` out of git.
- When changing code, write tests first and run `pytest -q`.

---
applyTo: "**/*"
---

# Options Reporter Guidance

- CLI entry point: `options-put-call-report`.
- Main orchestration: `src/reporter/cli.py`.
- Live Barchart collection: `src/reporter/collector.py`.
- Report rendering: `src/reporter/reporting.py`.
- Config: `config/symbols.json` with packaged fallback defaults.
- Reports/diagnostics: `archive/YYYY-MM-DD/`.
- History database: `data/history.sqlite3`.
- Architecture guide: `docs/ARCHITECTURE.md`.
- Maintenance guide: `docs/MAINTENANCE.md`.
- CI-equivalent checks: `pytest -q` and `python -m build`.
- Browser setup: `python -m playwright install chromium`.
- Local run: `options-put-call-report run --no-email`.
- Tests live in `tests/` and should use deterministic fixtures.
- Do not commit `archive/`, `data/`, or `config/email.local.json`.
- Treat report output as research and not financial advice.
- Resend API keys belong in macOS Keychain.
- Never ask users to paste Resend API keys into chat.
- Email failure logs include Resend stage diagnostics such as `stage=send` and HTTP status when available.
- Supported agents/platforms: Claude Code, GitHub Copilot, Codex, and Gemini.

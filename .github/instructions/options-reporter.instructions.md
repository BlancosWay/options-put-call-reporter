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
- CI-equivalent checks: `pytest -q` and `python -m build`.
- Browser setup: `python -m playwright install chromium`.
- Local run: `options-put-call-report run --no-email`.
- Tests live in `tests/` and should use deterministic fixtures.
- Do not commit `archive/`, `data/`, or `config/email.local.json`.
- Treat report output as research and not financial advice.
- Gmail App Passwords belong in macOS Keychain.
- Supported agents/platforms: Claude Code, GitHub Copilot, Codex, and Gemini.

# Options Put/Call Reporter Agent Prompt

You help operate and maintain `options-put-call-reporter`.

Supported platforms for the full instruction pack are Claude Code, GitHub Copilot, Codex, and Gemini.

The tool:
- runs as `options-put-call-report`;
- collects Barchart put/call ratio pages with Playwright Chromium;
- generates HTML, Markdown, CSV, JSON, and SQLite history outputs;
- supports default symbols, terminal symbols, and `--symbols-file`;
- stores Gmail App Passwords in macOS Keychain.

Use these commands:

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -q
python -m build
options-put-call-report run --no-email
```

Locations:
- Config: `config/symbols.json`.
- Reports and diagnostics: `archive/YYYY-MM-DD/`.
- History database: `data/history.sqlite3`.

Safety:
- Treat outputs as research and not financial advice.
- Do not expose secrets.
- Do not commit local archives, SQLite data, or email config.

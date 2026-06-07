# Options Put/Call Reporter Agent Prompt

You help operate and maintain `options-put-call-reporter`.

Supported platforms for the full instruction pack are Claude Code, GitHub Copilot, Codex, and Gemini.

The tool:
- runs as `options-put-call-report`;
- collects Barchart put/call ratio pages with Playwright Chromium;
- generates HTML, Markdown, CSV, JSON, and SQLite history outputs;
- supports default symbols, terminal symbols, and `--symbols-file`;
- reads Resend API keys from `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring.

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
- Resend API keys belong in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring.
- Use the system keyring on desktop machines and environment variables or secret files for headless/CI runs.
- Never ask users to paste Resend API keys into chat.
- Never commit Resend API keys.
- If `setup-email` cannot write to the system keyring, it can reuse an already-readable matching key; otherwise use the sanitized `Keyring error:` detail to diagnose the backend or switch to `RESEND_API_KEY` / `RESEND_API_KEY_FILE`.
- Email failure logs include Resend stage diagnostics such as `stage=send` and HTTP status when available.
- Do not expose secrets.
- Do not commit local archives, SQLite data, or email config.

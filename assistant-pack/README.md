# Options Put/Call Reporter Assistant Pack

Portable instructions for using AI assistants with `options-put-call-reporter`.

Supported platforms: Claude Code, GitHub Copilot, Codex, and Gemini.

## Claude Code

Copy `assistant-pack/claude/options-put-call-reporter/` into your Claude/Superpowers skills directory, or paste the `SKILL.md` content into your local skill system.

## GitHub Copilot

Use `.github/copilot-instructions.md` and `.github/instructions/options-reporter.instructions.md` in the repository.

## Codex

Use the root `AGENTS.md` file.

## Gemini

Use the root `GEMINI.md` file.

## Platform-neutral prompt

Paste `assistant-pack/prompts/options-report-agent.md` into assistants that do not support file-based instructions.

## Deeper project context

- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release workflow.

## Safety

Treat generated reports as options-sentiment research, not financial advice. Never paste secrets into chat; Gmail App Passwords should stay in macOS Keychain via `options-put-call-report setup-email`.

## Shared commands and locations

Run `python -m playwright install chromium`, `pytest -q`, `python -m build`, and `options-put-call-report run --no-email` when validating changes. Config lives in `config/symbols.json`, report archives live in `archive/YYYY-MM-DD/`, and history lives in `data/history.sqlite3`.

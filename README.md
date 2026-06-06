# Options Put/Call Reporter

Daily Barchart put/call ratio sentiment reporter for a stock watchlist. The tool collects live options-expiration data, classifies monthly put/call signals, tracks historical drift, renders clean HTML/Markdown/CSV reports, and can optionally email the report through Gmail.

> Not financial advice. This project summarizes options sentiment data for research and automation. Verify all market data independently before making trading or investment decisions.

## Features

- Collects Barchart put/call ratio data with Playwright Chromium.
- Produces a clean HTML dashboard plus Markdown and CSV outputs.
- Tracks history in SQLite and reports day/week/month drift where prior data exists.
- Supports default symbols, terminal symbols, or a plain-text symbol file.
- Sends Gmail reports using a macOS Keychain-stored app password.
- Includes launchd scheduling scripts for local daily runs on macOS.
- Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini.

## Install from GitHub

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/srinadel/options-put-call-reporter.git
python3 -m pipx run --spec playwright playwright install chromium
```

After `ensurepath`, restart your shell or source your shell profile before running `options-put-call-report`.

For development:

```bash
git clone https://github.com/srinadel/options-put-call-reporter.git
cd options-put-call-reporter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## Quickstart

Run the default watchlist and save the report locally:

```bash
options-put-call-report run --no-email
```

Runs print concise progress by default, including the symbol count, each symbol collection step, report rendering, and email send status when email is enabled.

Run a one-off report for symbols entered in the terminal:

```bash
options-put-call-report run --no-email META MSFT NOW
```

Run from a plain text symbol file:

```bash
options-put-call-report run --no-email --symbols-file watchlist.txt
```

Symbol files can use one symbol per line, spaces, commas, and `#` comments:

```text
# watchlist.txt
META, MSFT
NOW AAOI
LITE  # comments are ignored
```

## Outputs

By default, reports and raw collection artifacts are written under `archive/YYYY-MM-DD/`:

- `report.html` - polished dashboard report.
- `report.md` - Markdown report.
- `{SYMBOL}-expirations.csv` - raw expiration table.
- `{SYMBOL}-snapshot.json` - normalized snapshot.
- `{SYMBOL}-raw.json` and `{SYMBOL}-raw.html` - collection diagnostics.

History is stored in `data/history.sqlite3`.

## Email setup

Run the interactive setup command. It asks for sender email, recipient email, and a Gmail App Password. The app password is stored in macOS Keychain under `options-put-call-reporter:gmail-app-password`.

```bash
options-put-call-report setup-email
options-put-call-report run --send-email
```

The local email config is written to `config/email.local.json`, which is intentionally ignored by git.

## Scheduler

Before installing the scheduler, confirm that a manual email run succeeds:

```bash
options-put-call-report run --send-email
```

Install the launchd job from a cloned checkout:

```bash
./scripts/install_launch_agent.sh
launchctl list | grep com.sri.options-put-call-reporter
```

The scheduled job runs at 2:30 PM Pacific Time, which corresponds to 5:30 PM Eastern Time. Logs are written to:

- `archive/runner.log`
- `archive/launchd.out.log`
- `archive/launchd.err.log`

The scheduled runner captures the same concise progress output in these logs.

## Assistant pack

This repository includes assistant instructions for maintaining and operating the tool:

- `AGENTS.md` for Codex-style agents.
- `CLAUDE.md` for Claude Code.
- `GEMINI.md` for Gemini CLI.
- `.github/copilot-instructions.md` for GitHub Copilot.
- `assistant-pack/` for portable skill/prompt files.

See `assistant-pack/README.md` for copy/install guidance.

## Development

```bash
source .venv/bin/activate
pytest -q
python -m build
```

The publishing release checklist adds GitHub Actions CI for Python 3.11 and 3.12.

## Troubleshooting

- If Barchart collection fails after a GitHub/pipx install, run `python3 -m pipx run --spec playwright playwright install chromium`.
- In a development checkout, install Chromium with `python -m playwright install chromium`.
- If a symbol fails, inspect the daily `archive/YYYY-MM-DD/` diagnostics.
- If email fails, confirm the Gmail App Password is present in Keychain and the recipient config exists.
- If running from a fresh GitHub install, the packaged default watchlist is used when `config/symbols.json` is absent.

## Security and privacy

Do not commit `config/email.local.json`, Gmail app passwords, `archive/`, or `data/`. Generated archives can include local diagnostics and market snapshots.

## License

MIT. See `LICENSE`.

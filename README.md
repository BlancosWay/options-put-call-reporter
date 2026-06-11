# Options Put/Call Reporter

[![CI](https://github.com/BlancosWay/options-put-call-reporter/actions/workflows/ci.yml/badge.svg)](https://github.com/BlancosWay/options-put-call-reporter/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A daily command-line reporter that turns Barchart options put/call ratio data into a readable sentiment report for a stock or ETF watchlist. It collects options-expiration data with a headless browser, classifies monthly put/call signals, tracks history for drift, renders HTML/Markdown/CSV reports, and can email the result through Resend.

> [!IMPORTANT]
> This project summarizes options-sentiment data for research and automation. It is **not financial advice**. Verify all market data independently before making any trading or investment decision.

## Features

- **Watchlist driven** — use the packaged defaults, pass symbols on the command line, or point at a plain-text symbol file.
- **Barchart collection with fallback** — Playwright Chromium scrapes Barchart put/call pages, with an automatic yfin.dev options-chain fallback when Barchart collection fails. Every report discloses which source produced each symbol.
- **Monthly sentiment signals** — expiration rows are classified bullish, bearish, or neutral from configurable put/call ratio thresholds.
- **History and drift** — each run is stored in SQLite so reports can show how a symbol's sentiment moved versus prior runs.
- **Multiple report formats** — `report.html`, `report.md`, and per-symbol CSV/JSON snapshots, plus raw diagnostics for every run.
- **Optional email and scheduling** — deliver the HTML report through Resend and automate it with the bundled macOS `launchd` job (or cron / Task Scheduler elsewhere).

## How it works

1. **Resolve the watchlist** from packaged defaults, CLI arguments, or a symbol file.
2. **Collect each symbol** from Barchart (primary) or yfin.dev (fallback), archiving raw captures and failure diagnostics.
3. **Analyze** monthly expirations into put/call sentiment signals and compare against saved history for drift.
4. **Render** HTML, Markdown, CSV, and JSON artifacts under `archive/YYYY-MM-DD/`.
5. **Deliver (optional)** the HTML report by email, on demand or on a schedule.

## Quick start

### Install as a CLI with pipx

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium
options-put-call-report run --no-email
```

### Run from a local checkout

```bash
git clone https://github.com/BlancosWay/options-put-call-reporter.git
cd options-put-call-reporter
python3.11 scripts/setup_local.py
./.venv/bin/options-put-call-report run --no-email
```

Activate the environment with `source .venv/bin/activate` to use the shorter `options-put-call-report ...` commands. For Windows commands and Linux browser dependencies, see [docs/SETUP.md](docs/SETUP.md).

> [!NOTE]
> Collection drives a headless Chromium through Playwright. If a run reports a browser error, (re)install the browser with `python -m playwright install chromium`.

## Usage

| Task | Command |
| --- | --- |
| Run the default watchlist without email | `options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` |
| Open the report in your browser after the run | `options-put-call-report run --no-email --open` |
| Configure Resend email | `options-put-call-report setup-email` |
| Run and send email | `options-put-call-report run --send-email` |

Symbol files accept one symbol per line, spaces, commas, and `#` comments:

```text
# watchlist.txt
META, MSFT
NOW AAOI
LITE  # comments are ignored
```

## Outputs

Each run writes to `archive/YYYY-MM-DD/`:

- `report.html` and `report.md` — the rendered sentiment report.
- `{SYMBOL}-snapshot.json` and `{SYMBOL}-expirations.csv` — per-symbol data.
- `{SYMBOL}-raw.html` / `{SYMBOL}-raw.json` on success, or `{SYMBOL}-failure.html` / `{SYMBOL}-failure.png` and `{SYMBOL}-yfin-raw.json` when Barchart fails and the fallback runs.

Run history is kept in `data/history.sqlite3`. See [docs/OUTPUTS.md](docs/OUTPUTS.md) for the report fields, signal meanings, and fallback artifacts.

## Email

Email delivery uses Resend and reads the API key from `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring. On a desktop machine, `options-put-call-report setup-email` stores the key in the system keyring and writes sender/recipient metadata to ignored local config.

> [!WARNING]
> Never commit a Resend API key or paste one into a chat. Keep it in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring.

See [docs/EMAIL.md](docs/EMAIL.md) for desktop setup, CI/server secrets, keyring behavior, and troubleshooting.

## Scheduling

The bundled scheduler script targets macOS `launchd`. On Linux or Windows, schedule `options-put-call-report run --send-email` with cron, systemd timers, or Task Scheduler.

Confirm a manual email run succeeds first, then install the launchd job from a checkout:

```bash
options-put-call-report run --send-email
./scripts/install_launch_agent.sh
launchctl list | grep com.sri.options-put-call-reporter
```

Scheduler logs are written to `archive/runner.log`, `archive/launchd.out.log`, and `archive/launchd.err.log`.

## Configuration

Symbols and thresholds live in `config/symbols.json`; the packaged defaults are used when that file is absent (for example after a fresh pipx install). Each symbol entry pairs a ticker with its Barchart put/call URL.

## Development

```bash
python3.11 scripts/setup_local.py
source .venv/bin/activate
pytest -q
python -m build
```

CI runs the test suite on Python 3.11 and 3.12 and builds the package. See [docs/MAINTENANCE.md](docs/MAINTENANCE.md) for branch protection, Dependabot auto-merge, and release checks.

## Documentation

| File | Purpose |
| --- | --- |
| [docs/SETUP.md](docs/SETUP.md) | Install paths, local setup, Windows commands, and troubleshooting. |
| [docs/OUTPUTS.md](docs/OUTPUTS.md) | Report files, signal meanings, and fallback diagnostics. |
| [docs/EMAIL.md](docs/EMAIL.md) | Resend setup, key lookup order, and server/CI secrets. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Runtime flow, source metadata, and safe change points. |
| [docs/MAINTENANCE.md](docs/MAINTENANCE.md) | Local validation, CI, auto-merge, and release checks. |
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | Initial GitHub publication. |

This repository also ships assistant instructions for Claude Code (`CLAUDE.md`), GitHub Copilot (`.github/copilot-instructions.md`), Codex (`AGENTS.md`), and Gemini (`GEMINI.md`), plus portable prompts under [assistant-pack/](assistant-pack/README.md).

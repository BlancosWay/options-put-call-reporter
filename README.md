# Options Put/Call Reporter

[![CI](https://github.com/BlancosWay/options-put-call-reporter/actions/workflows/ci.yml/badge.svg)](https://github.com/BlancosWay/options-put-call-reporter/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Daily Barchart put/call ratio sentiment reporter for a stock watchlist. The tool collects options-expiration data, classifies monthly put/call signals, tracks history, renders reports, and can optionally email the report through Resend.

> [!IMPORTANT]
> Not financial advice. This project summarizes options sentiment data for research and automation. Verify all market data independently before making trading or investment decisions.

## Requirements

- **Python 3.11 or newer.** Check with `python3 --version` (macOS/Linux) or `py --version` (Windows). If your default `python3` is older, run the `pipx` commands below with an explicit 3.11+ interpreter such as `python3.11`.
- **Internet access** for the GitHub install, Playwright Chromium download, Barchart collection, yfin.dev fallback, and Resend email.
- **A headless Chromium**, installed through Playwright in the steps below.

## Features

- **Watchlist driven** — use the packaged defaults, pass symbols on the command line, or point at a plain-text symbol file.
- **Barchart collection with fallback** — Playwright Chromium scrapes Barchart, with an automatic yfin.dev options-chain fallback when collection fails. Every report discloses which source produced each symbol.
- **Monthly sentiment signals** — expiration rows are classified bullish, bearish, or neutral from configurable put/call ratio thresholds.
- **History and drift** — each run is stored in SQLite so reports can show how a symbol moved versus prior runs.
- **Multiple formats** — HTML and Markdown reports plus per-symbol CSV/JSON snapshots and raw diagnostics.
- **Optional email and scheduling** — deliver through Resend and automate with the bundled macOS `launchd` job.

## Quick start

> [!NOTE]
> The steps below cover the common macOS/Linux path. See [docs/SETUP.md](docs/SETUP.md) for clear, step-by-step instructions on how to install on each platform (macOS, Linux, and Windows).

### Install as a CLI with pipx

Use this path when you want the CLI installed globally:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium
options-put-call-report run --no-email
```

> [!IMPORTANT]
> `pipx ensurepath` updates your `PATH` only for new shells. Open a new terminal (or `source` your shell profile) before the final command, or call the CLI directly as `~/.local/bin/options-put-call-report run --no-email`.

### Run from a local checkout

Use this path when you cloned the repository and want to run or modify the code:

```bash
git clone https://github.com/BlancosWay/options-put-call-reporter.git
cd options-put-call-reporter
python3.11 scripts/setup_local.py
./.venv/bin/options-put-call-report run --no-email
```

If you prefer activating the environment, run `source .venv/bin/activate`, then use the shorter `options-put-call-report ...` commands.

For Windows commands and Linux browser dependencies, see [docs/SETUP.md](docs/SETUP.md).

> [!NOTE]
> Collection drives a headless Chromium through Playwright. If a run reports a browser error, (re)install it with `python -m playwright install chromium`.

## Common commands

| Task | Command |
| --- | --- |
| Run default watchlist without email | `options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` |
| Run and open the report in your browser | `options-put-call-report run --no-email --open` |
| Configure Resend email | `options-put-call-report setup-email` |
| Run and send email | `options-put-call-report run --send-email` |

Symbol files can use one symbol per line, spaces, commas, and `#` comments:

```text
# watchlist.txt
META, MSFT
NOW AAOI
LITE  # comments are ignored
```

## What it does

1. Start with a watchlist. Use the packaged defaults, type symbols in the terminal, or pass a plain-text symbol file.
2. Collect each symbol's options sentiment. Barchart is the primary source. Falls back to yfin.dev options-chain data when Barchart collection fails.
3. Turn the data into a report you can compare over time. Each run writes HTML/Markdown reports, per-symbol snapshots, raw diagnostics, and SQLite history for drift.
4. Optionally send or schedule the report when you want it automated. Resend handles email delivery, and the macOS launchd scripts can run the report daily.

Reports disclose the data source used for each symbol. Fallback data is visible instead of hidden.

## Outputs and signal meaning

A run writes reports and diagnostics under `archive/YYYY-MM-DD/`, including `report.html`, `report.md`, per-symbol CSV/JSON snapshots, and raw collection diagnostics.

The monthly signal classifies expiration rows as bullish, bearish, or neutral using the reporter's put/call ratio thresholds. Use it as options-sentiment research, not as a trade recommendation.

See [docs/OUTPUTS.md](docs/OUTPUTS.md) for output files, fallback artifacts, and how to read report fields.

## Email

Email delivery uses Resend. Email delivery reads the Resend API key from `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring. On desktop machines, `options-put-call-report setup-email` stores the key in the system keyring and writes sender/recipient metadata to ignored local config.

> [!WARNING]
> Never commit a Resend API key or paste one into a chat. Keep it in `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring.

See [docs/EMAIL.md](docs/EMAIL.md) for desktop setup, CI/server secrets, keyring behavior, and safe troubleshooting.

## Scheduler

The included scheduler script is for macOS `launchd`. On Linux or Windows, schedule `options-put-call-report run --send-email` with cron, systemd timers, or Windows Task Scheduler.

Before installing the scheduler, confirm a manual email run succeeds:

```bash
options-put-call-report run --send-email
```

Install the macOS launchd job from a cloned checkout:

```bash
./scripts/install_launch_agent.sh
launchctl list | grep com.sri.options-put-call-reporter
```

Scheduler logs are written to `archive/runner.log`, `archive/launchd.out.log`, and `archive/launchd.err.log`.

## Documentation

| File | Purpose |
| --- | --- |
| [docs/SETUP.md](docs/SETUP.md) | Install paths, local checkout setup, Windows commands, and setup troubleshooting. |
| [docs/OUTPUTS.md](docs/OUTPUTS.md) | Report files, signal meanings, data-source fallback behavior, and diagnostics. |
| [docs/EMAIL.md](docs/EMAIL.md) | Resend setup, API key lookup order, keyring behavior, and server/CI secret options. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Runtime flow, source metadata, module responsibilities, and safe change points. |
| [docs/MAINTENANCE.md](docs/MAINTENANCE.md) | Local validation, protected `main`, CI, Dependabot auto-merge, and release checks. |
| [docs/PUBLISHING.md](docs/PUBLISHING.md) | Initial GitHub publication. |

This repository ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini for maintaining and operating the tool:

- [`AGENTS.md`](AGENTS.md) for Codex-style agents.
- [`CLAUDE.md`](CLAUDE.md) for Claude Code.
- [`GEMINI.md`](GEMINI.md) for Gemini CLI.
- [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for GitHub Copilot.
- [`assistant-pack/`](assistant-pack/) for portable skill/prompt files.

See [`assistant-pack/README.md`](assistant-pack/README.md) for copy/install guidance.

## Development

```bash
python3.11 scripts/setup_local.py
source .venv/bin/activate
pytest -q
python -m build
```

CI runs the test suite on Python 3.11 and 3.12 and builds the package.

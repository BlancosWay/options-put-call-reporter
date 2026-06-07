# Options Put/Call Reporter

Daily Barchart put/call ratio sentiment reporter for a stock watchlist. The tool collects live options-expiration data, classifies monthly put/call signals, tracks historical drift, renders clean HTML/Markdown/CSV reports, and can optionally email the report through Resend.

> Not financial advice. This project summarizes options sentiment data for research and automation. Verify all market data independently before making trading or investment decisions.

## Table of contents

- [Features](#features)
- [Install from GitHub](#install-from-github)
- [Quickstart](#quickstart)
- [What this produces](#what-this-produces)
- [How to read the signal](#how-to-read-the-signal)
- [Data sources and fallback behavior](#data-sources-and-fallback-behavior)
- [CLI command reference](#cli-command-reference)
- [Outputs](#outputs)
- [Email setup](#email-setup)
- [Scheduler](#scheduler)
- [Documentation for maintainers and agents](#documentation-for-maintainers-and-agents)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Security and privacy](#security-and-privacy)
- [License](#license)

## Features

- Collects Barchart put/call ratio data with Playwright Chromium.
- Falls back to yfin.dev options-chain data when Barchart collection fails.
- Produces a clean HTML dashboard plus Markdown and CSV outputs.
- Reports disclose the data source used for each symbol.
- Tracks history in SQLite and reports day/week/month drift where prior data exists.
- Supports default symbols, terminal symbols, or a plain-text symbol file.
- Sends Resend email reports using a macOS Keychain-stored API key.
- Includes launchd scheduling scripts for local daily runs on macOS.
- Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini.

## Install from GitHub

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
python3 -m pipx run --spec playwright playwright install chromium
```

After `ensurepath`, restart your shell or source your shell profile before running `options-put-call-report`.

For development:

```bash
git clone https://github.com/BlancosWay/options-put-call-reporter.git
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

## What this produces

A run creates a dated archive folder and writes a human-readable report plus raw diagnostics:

```text
archive/YYYY-MM-DD/
|-- report.html
|-- report.md
|-- META-expirations.csv
|-- META-snapshot.json
|-- META-raw.json
`-- META-raw.html
```

The HTML report summarizes each symbol with a monthly signal, put/call ratios, drift from prior saved runs, and the data source used for that symbol.

Successful Barchart collection writes `{SYMBOL}-raw.html` and `{SYMBOL}-raw.json`. If Barchart extraction fails before fallback succeeds or the symbol fails completely, failure diagnostics are written as `{SYMBOL}-failure.html` and `{SYMBOL}-failure.png`.

## How to read the signal

- **Put/call ratio:** compares put activity to call activity. Higher values are more put-heavy; lower values are more call-heavy.
- **Monthly signal:** classifies monthly expiration rows as bullish, bearish, or neutral using the reporter's ratio thresholds.
- **Drift:** compares the current snapshot with prior history in `data/history.sqlite3` when enough previous data exists.
- **Data source:** each generated report discloses whether a symbol used Barchart primary data or yfin.dev fallback data.

Use the report as options-sentiment research, not as a trade recommendation.

## Data sources and fallback behavior

Barchart is the primary source. The collector uses Playwright Chromium to load Barchart put/call pages and stores raw diagnostics in the daily archive.

If Barchart collection fails for a symbol, the tool falls back to the free yfin.dev options-chain API. yfin.dev fallback can still calculate expiration-level put/call volume and open-interest ratios, but it does not provide Barchart-only top metrics such as IV Rank or IV Percentile. Fallback runs write `{SYMBOL}-yfin-raw.json` and mark the report source as `yfin.dev`.

## CLI command reference

| Task | Command |
| --- | --- |
| Run default watchlist without email | `options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` |
| Configure Resend email | `options-put-call-report setup-email` |
| Run and send email | `options-put-call-report run --send-email` |
| Install Playwright Chromium for pipx install | `python3 -m pipx run --spec playwright playwright install chromium` |
| Install Playwright Chromium in a checkout | `python -m playwright install chromium` |

## Outputs

By default, reports and raw collection artifacts are written under `archive/YYYY-MM-DD/`:

- `report.html` - polished dashboard report.
- `report.md` - Markdown report.
- `{SYMBOL}-expirations.csv` - raw expiration table.
- `{SYMBOL}-snapshot.json` - normalized snapshot.
- `{SYMBOL}-raw.json` and `{SYMBOL}-raw.html` - collection diagnostics.
- `{SYMBOL}-failure.html` and `{SYMBOL}-failure.png` - Barchart extraction failure diagnostics.
- `{SYMBOL}-yfin-raw.json` - fallback yfin.dev raw responses, written only when yfin.dev fallback is used.

History is stored in `data/history.sqlite3`.

## Email setup

Create a free Resend account, verify a sender identity or domain, and create a Resend API key. Then run the interactive setup command. It asks for the verified sender address, recipient email, and Resend API key. The API key is stored in macOS Keychain under `options-put-call-reporter:resend-api-key`.

```bash
options-put-call-report setup-email
options-put-call-report run --send-email
```

The local email config is written to `config/email.local.json`, which is intentionally ignored by git.

Email failures include Resend stage diagnostics like `stage=connect` or `stage=send`, the Resend endpoint, sender, recipient, HTTP status when available, and the safe exception type/message; the Resend API key is redacted.

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

## Documentation for maintainers and agents

- `docs/ARCHITECTURE.md` explains runtime flow, source metadata, module responsibilities, and safe change points.
- `docs/MAINTENANCE.md` explains local validation, protected `main`, CI, Dependabot auto-merge, and release checks.
- `docs/PUBLISHING.md` explains initial GitHub publication.
- `CONTRIBUTING.md` explains contributor expectations.
- `SECURITY.md` explains vulnerability reporting and sensitive local files.
- `assistant-pack/README.md` explains portable assistant instructions.

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

CI runs the test suite on Python 3.11 and 3.12 and builds the package.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `options-put-call-report` is not found after install | Shell has not picked up pipx's PATH update | Restart the shell or source your shell profile after `python3 -m pipx ensurepath`. |
| Browser collection fails immediately | Playwright Chromium is missing | For pipx installs, run `python3 -m pipx run --spec playwright playwright install chromium`. In a checkout, run `python -m playwright install chromium`. |
| Barchart collection fails for one symbol | Barchart page or network response failed | Inspect `archive/YYYY-MM-DD/{SYMBOL}-failure.html` and `{SYMBOL}-failure.png`; if fallback succeeds, also inspect `{SYMBOL}-yfin-raw.json`. |
| Report uses yfin.dev fallback | Barchart failed and fallback succeeded | Check the report data-source disclosure and `{SYMBOL}-yfin-raw.json`; Barchart-only IV Rank/Percentile metrics may be unavailable. |
| Email send fails | Resend API key, verified sender, local recipient config, or Resend API request is invalid | Re-run `options-put-call-report setup-email`, confirm `config/email.local.json` exists locally, verify the sender in Resend, and inspect the Resend stage/status in the error. |
| Fresh install has no `config/symbols.json` | GitHub install uses packaged defaults | Run without a config file to use packaged defaults, or pass symbols in the terminal or via `--symbols-file`. |

## Security and privacy

Do not commit `config/email.local.json`, Resend API keys, `archive/`, or `data`. Generated archives can include local diagnostics and market snapshots.

## License

MIT. See `LICENSE`.

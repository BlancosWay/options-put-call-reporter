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
- Sends Resend email reports using a key from the environment, a secret file, or the system keyring.
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

Create a free Resend account, verify a sender identity or domain, and create a Resend API key. The report can find that key from these sources, in order:

1. `RESEND_API_KEY` environment variable.
2. `RESEND_API_KEY_FILE`, a file containing only the API key.
3. The system keyring through Python `keyring`.

Use the interactive setup on desktop machines:

```bash
options-put-call-report setup-email
options-put-call-report run --send-email
```

The setup command asks for the verified sender address, recipient email, and Resend API key. It writes only sender/recipient metadata to `config/email.local.json` and stores the API key in the system keyring: macOS Keychain, Windows Credential Manager, or Linux Secret Service/KWallet. If keyring storage fails but the same key is already readable from the system keyring, setup reuses that existing item and still writes `config/email.local.json`. Other keyring storage failures include the underlying `keyring` exception type and message with the API key omitted.

For CI and secret-manager injection, expose the key as an environment variable without typing the secret into a shell command:

```bash
export RESEND_API_KEY="re_..."
options-put-call-report run --send-email
```

For Linux servers and containers, prefer a mounted secret file. If you need to create one interactively, read the key without echoing it and clear the temporary shell variable after writing the file:

```bash
mkdir -p ~/.config/options-put-call-report
read -r -s -p "Resend API key: " RESEND_API_KEY
printf '\n'
printf '%s\n' "$RESEND_API_KEY" > ~/.config/options-put-call-report/resend-api-key
unset RESEND_API_KEY
chmod 600 ~/.config/options-put-call-report/resend-api-key
export RESEND_API_KEY_FILE=~/.config/options-put-call-report/resend-api-key
options-put-call-report run --send-email
```

The key source only provides the Resend secret. Every `run --send-email` invocation also needs sender/recipient metadata in `config/email.local.json` or a JSON file passed with `--email-config`; that file must contain `from_email` and `to_email`.

| Environment | Install | Setup | Maintenance |
| --- | --- | --- | --- |
| macOS desktop | `python3.11 -m venv .venv && ./.venv/bin/python -m pip install -e ".[dev]"` | Run `options-put-call-report setup-email`; keyring stores in macOS Keychain. | Re-run setup when rotating Resend keys; use Keychain Access to delete stale entries. |
| Windows desktop | Create a Python 3.11+ venv, then `python -m pip install -e ".[dev]"`. | Run `options-put-call-report setup-email`; keyring stores in Windows Credential Manager. | Re-run setup when rotating keys; remove stale credentials from Credential Manager. |
| Linux desktop | Install Python 3.11+, package deps, and a Secret Service/KWallet backend such as GNOME Keyring or KWallet; then install the package. The backend must be installed, running, unlocked, and discoverable by Python `keyring`. | Run `options-put-call-report setup-email` in an unlocked desktop session. | If keyring is locked/unavailable, unlock the desktop keyring or use env/file fallback. |
| Linux headless/server | Install Python 3.11+ and the package. | Set `RESEND_API_KEY` or `RESEND_API_KEY_FILE`; also provide `config/email.local.json` or `--email-config` with `from_email` and `to_email`. | Rotate the host secret and restart the scheduler/process. |
| Docker/Kubernetes | Install package in the image. | Mount the Resend key as a secret file and set `RESEND_API_KEY_FILE`; also mount an email metadata JSON and pass `--email-config` if it is not at `config/email.local.json`. | Rotate the orchestrator secret and restart workloads. |
| GitHub Actions | Install with `python -m pip install -e ".[dev]"`. | Store the key in repository/environment secrets and expose it as `RESEND_API_KEY`; create `config/email.local.json` or pass `--email-config` with `from_email` and `to_email`. | Rotate GitHub secret; never print it in logs. |

Older custom email configs created before Resend support need these email fields in `config/symbols.json` before running setup:

```json
"keychain_service": "options-put-call-reporter:resend-api-key",
"resend_api_url": "https://api.resend.com/emails"
```

Keep your existing archive, database, threshold, and symbol settings.

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
| `setup-email` cannot store the API key | System keyring is locked, unavailable, denied, missing a backend, or refusing to replace a different existing item | Read the `Keyring error:` detail printed by setup, unlock/configure the desktop keyring, delete/rotate the stale item if needed, or use `RESEND_API_KEY` / `RESEND_API_KEY_FILE` instead. |
| Email send fails | Resend API key, verified sender, local recipient config, or Resend API request is invalid | Re-run `options-put-call-report setup-email`, confirm `config/email.local.json` exists locally, verify the sender in Resend, and inspect the Resend stage/status in the error. |
| Fresh install has no `config/symbols.json` | GitHub install uses packaged defaults | Run without a config file to use packaged defaults, or pass symbols in the terminal or via `--symbols-file`. |

## Security and privacy

Do not commit `config/email.local.json`, Resend API keys, `archive/`, or `data`. Generated archives can include local diagnostics and market snapshots.

## License

MIT. See `LICENSE`.

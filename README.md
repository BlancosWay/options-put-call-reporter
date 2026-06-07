# Options Put/Call Reporter

Daily Barchart put/call ratio sentiment reporter for a stock watchlist. The tool collects live options-expiration data, classifies monthly put/call signals, tracks historical drift, renders HTML/Markdown/CSV reports, and can optionally email the report through Resend.

> Not financial advice. This project summarizes options sentiment data for research and automation. Verify all market data independently before making trading or investment decisions.

## Table of contents

- [Features](#features)
- [Choose your setup](#choose-your-setup)
- [Install from GitHub](#install-from-github)
- [Local checkout / development install](#local-checkout--development-install)
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

| Area | What it does |
| --- | --- |
| Collection | Collects Barchart put/call ratio data with Playwright Chromium. |
| Fallback data | Falls back to yfin.dev options-chain data when Barchart collection fails. |
| Reports | Produces HTML, Markdown, CSV, JSON, and raw diagnostic outputs. |
| Transparency | Reports disclose the data source used for each symbol. |
| History | Tracks snapshots in SQLite and reports day/week/month drift when prior data exists. |
| Symbols | Supports packaged defaults, terminal symbols, and plain-text symbol files. |
| Email | Sends Resend email reports using a key from the environment, a secret file, or the system keyring. |
| Scheduling | Includes launchd scripts for local daily runs on macOS. |
| Assistant docs | Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini. |

## Choose your setup

| If you want to... | Use this setup | Command style after setup |
| --- | --- | --- |
| Install and run the tool like an app | [Install from GitHub](#install-from-github) with `pipx` | `options-put-call-report ...` |
| Work from this cloned repository | [Local checkout / development install](#local-checkout--development-install) | Activate `.venv`, then run `options-put-call-report ...` |
| Run from the checkout without activating the venv | Local checkout with `.venv` | `./.venv/bin/options-put-call-report ...` |
| Run on a server, container, or CI | Package install plus env/file secrets | `options-put-call-report ...` with `RESEND_API_KEY` or `RESEND_API_KEY_FILE` |

The docs usually show `options-put-call-report ...` because that is the normal installed command. In a local checkout, either activate the venv first or call the executable by its full path.

| Local checkout option | Example |
| --- | --- |
| Activate once per shell | `source .venv/bin/activate` then `options-put-call-report run --no-email` |
| No activation | `./.venv/bin/options-put-call-report run --no-email` |

## Install from GitHub

Use this path when you want the CLI installed globally through `pipx`.

| Step | Command |
| --- | --- |
| Install `pipx` | `python3 -m pip install --user pipx` |
| Add `pipx` apps to PATH | `python3 -m pipx ensurepath` |
| Install this tool | `python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git` |
| Install Playwright Chromium | `python3 -m pipx run --spec playwright playwright install chromium` |

After `ensurepath`, restart your shell or source your shell profile before running `options-put-call-report`.

## Local checkout / development install

Use this path when you cloned the repository and want to run or modify the code locally.

| Step | macOS/Linux command |
| --- | --- |
| Clone | `git clone https://github.com/BlancosWay/options-put-call-reporter.git` |
| Enter repo | `cd options-put-call-reporter` |
| Create venv | `python3.11 -m venv .venv` |
| Activate venv | `source .venv/bin/activate` |
| Upgrade installer | `python -m pip install --upgrade pip` |
| Install package and dev tools | `python -m pip install -e ".[dev]"` |
| Install Playwright Chromium | `python -m playwright install chromium` |

Windows PowerShell uses the same Python commands, but activates the venv with:

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, run the same commands shown in the rest of this README. Without activation, prefix commands with the venv executable path:

| Shell | No-activation command example |
| --- | --- |
| macOS/Linux | `./.venv/bin/options-put-call-report run --no-email` |
| Windows PowerShell | `.\.venv\Scripts\options-put-call-report.exe run --no-email` |

## Quickstart

| Task | Installed / activated command | Local no-activation command |
| --- | --- | --- |
| Run default watchlist without email | `options-put-call-report run --no-email` | `./.venv/bin/options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` | `./.venv/bin/options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` | `./.venv/bin/options-put-call-report run --no-email --symbols-file watchlist.txt` |
| Configure Resend email | `options-put-call-report setup-email` | `./.venv/bin/options-put-call-report setup-email` |
| Run and send email | `options-put-call-report run --send-email` | `./.venv/bin/options-put-call-report run --send-email` |

Runs print concise progress by default, including the symbol count, each symbol collection step, report rendering, and email send status when email is enabled.

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

| Field | Meaning |
| --- | --- |
| Put/call ratio | Compares put activity to call activity. Higher values are more put-heavy; lower values are more call-heavy. |
| Monthly signal | Classifies monthly expiration rows as bullish, bearish, or neutral using the reporter's ratio thresholds. |
| Drift | Compares the current snapshot with prior history in `data/history.sqlite3` when enough previous data exists. |
| Data source | Shows whether a symbol used Barchart primary data or yfin.dev fallback data. |

Use the report as options-sentiment research, not as a trade recommendation.

## Data sources and fallback behavior

| Source | When used | What it provides | Archive files |
| --- | --- | --- | --- |
| Barchart | Primary source for each symbol | Put/call rows plus Barchart-only top metrics such as IV Rank and IV Percentile | `{SYMBOL}-raw.html`, `{SYMBOL}-raw.json` |
| yfin.dev | Fallback when Barchart collection raises a collection error | Expiration-level put/call volume and open-interest ratios; no Barchart-only top metrics | `{SYMBOL}-yfin-raw.json` |

Barchart collection uses Playwright Chromium through `src/reporter/collector.py`. If Barchart collection fails for a symbol, the tool falls back to the free yfin.dev options-chain API. Reports disclose the data source used for each symbol.

## CLI command reference

| Task | Command |
| --- | --- |
| Run default watchlist without email | `options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` |
| Configure Resend email | `options-put-call-report setup-email` |
| Run and send email | `options-put-call-report run --send-email` |
| Use a custom app config | `options-put-call-report run --config config/symbols.json --no-email` |
| Use a custom email config | `options-put-call-report run --send-email --email-config path/to/email.local.json` |
| Use a fixed run date | `options-put-call-report run --no-email --run-date 2026-06-02T21:30:00` |
| Install Playwright Chromium for pipx install | `python3 -m pipx run --spec playwright playwright install chromium` |
| Install Playwright Chromium in a checkout | `python -m playwright install chromium` |

## Outputs

By default, reports and raw collection artifacts are written under `archive/YYYY-MM-DD/`:

| Path | Purpose |
| --- | --- |
| `report.html` | Polished dashboard report. |
| `report.md` | Markdown report. |
| `{SYMBOL}-expirations.csv` | Raw expiration table. |
| `{SYMBOL}-snapshot.json` | Normalized snapshot. |
| `{SYMBOL}-raw.json` and `{SYMBOL}-raw.html` | Collection diagnostics for successful Barchart collection. |
| `{SYMBOL}-failure.html` and `{SYMBOL}-failure.png` | Barchart extraction failure diagnostics. |
| `{SYMBOL}-yfin-raw.json` | Fallback yfin.dev raw responses, written only when yfin.dev fallback is used. |
| `data/history.sqlite3` | SQLite history database used for drift. |

`data/history.sqlite3` is stored under `data/`, not inside the dated archive directory.

## Email setup

Create a free Resend account, verify a sender identity or domain, and create a Resend API key.

### What email needs

| Requirement | Where it lives | Secret? | Notes |
| --- | --- | --- | --- |
| Resend API key | `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or system keyring | Yes | Never commit it or paste it into chat. |
| Sender address | `config/email.local.json` or `--email-config` file | No | Must be verified in Resend. |
| Recipient address | `config/email.local.json` or `--email-config` file | No | Used as the report recipient. |

Every `run --send-email` invocation also needs sender/recipient metadata in `config/email.local.json` or a JSON file passed with `--email-config`; that file must contain `from_email` and `to_email`.

### API key lookup order

| Priority | Source | Best for |
| --- | --- | --- |
| 1 | `RESEND_API_KEY` environment variable | CI and secret-manager injection. |
| 2 | `RESEND_API_KEY_FILE`, a file containing only the API key | Servers, containers, and mounted secrets. |
| 3 | System keyring through Python `keyring` | Desktop macOS, Windows, and Linux sessions with an unlocked keyring backend. |

### Desktop setup

Use the interactive setup on desktop machines:

```bash
options-put-call-report setup-email
options-put-call-report run --send-email
```

The setup command asks for the verified sender address, recipient email, and Resend API key. It writes only sender/recipient metadata to `config/email.local.json` and stores the API key in the system keyring: macOS Keychain, Windows Credential Manager, or Linux Secret Service/KWallet.

If keyring storage fails but the same key is already readable from the system keyring, setup reuses that existing item and still writes `config/email.local.json`. Other keyring storage failures include the underlying `keyring` exception type and message with the API key omitted.

### Environment variable setup

For CI and secret-manager injection, expose the key as an environment variable without typing the secret into a shell command:

```bash
export RESEND_API_KEY="re_..."
options-put-call-report run --send-email
```

### Secret file setup

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

### Environment-specific guidance

| Environment | Install | Secret setup | Maintenance |
| --- | --- | --- | --- |
| macOS desktop | Use `pipx`, or create a local venv with `python3.11 -m venv .venv && source .venv/bin/activate && python -m pip install -e ".[dev]"`. | Run `options-put-call-report setup-email`; keyring stores in macOS Keychain. | Re-run `options-put-call-report setup-email` when rotating Resend keys; use Keychain Access to delete stale entries. |
| Windows desktop | Create a Python 3.11+ venv, activate it, then run `python -m pip install -e ".[dev]"`. | Run `options-put-call-report setup-email`; keyring stores in Windows Credential Manager. | Re-run setup when rotating keys; remove stale credentials from Credential Manager. |
| Linux desktop | Install Python 3.11+, package deps, and a Secret Service/KWallet backend such as GNOME Keyring or KWallet. | Run `options-put-call-report setup-email` in an unlocked desktop session. | If keyring is locked/unavailable, unlock the desktop keyring or use env/file fallback. |
| Linux headless/server | Install Python 3.11+ and the package. | Set `RESEND_API_KEY` or `RESEND_API_KEY_FILE`; also provide `config/email.local.json` or `--email-config`. | Rotate the host secret and restart the scheduler/process. |
| Docker/Kubernetes | Install package in the image. | Mount the Resend key as a secret file and set `RESEND_API_KEY_FILE`; mount email metadata JSON if needed. | Rotate the orchestrator secret and restart workloads. |
| GitHub Actions | Install with `python -m pip install -e ".[dev]"`. | Store the key in repository/environment secrets and expose it as `RESEND_API_KEY`. | Rotate GitHub secret; never print it in logs. |

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

| Scheduler detail | Value |
| --- | --- |
| Platform | macOS launchd |
| Run time | 2:30 PM Pacific / 5:30 PM Eastern |
| Runner log | `archive/runner.log` |
| launchd stdout | `archive/launchd.out.log` |
| launchd stderr | `archive/launchd.err.log` |

The scheduled runner captures the same concise progress output in these logs.

## Documentation for maintainers and agents

| File | Purpose |
| --- | --- |
| `docs/ARCHITECTURE.md` | Runtime flow, source metadata, module responsibilities, and safe change points. |
| `docs/MAINTENANCE.md` | Local validation, protected `main`, CI, Dependabot auto-merge, and release checks. |
| `docs/PUBLISHING.md` | Initial GitHub publication. |
| `CONTRIBUTING.md` | Contributor expectations. |
| `SECURITY.md` | Vulnerability reporting and sensitive local files. |
| `assistant-pack/README.md` | Portable assistant instructions. |

This repository includes assistant instructions for maintaining and operating the tool:

| Assistant/platform | File or directory |
| --- | --- |
| Codex-style agents | `AGENTS.md` for Codex-style agents. |
| Claude Code | `CLAUDE.md` for Claude Code. |
| Gemini CLI | `GEMINI.md` for Gemini CLI. |
| GitHub Copilot | `.github/copilot-instructions.md` for GitHub Copilot. |
| Portable skill/prompt files | `assistant-pack/` for portable skill/prompt files. |

See `assistant-pack/README.md` for copy/install guidance.

## Development

| Task | Command |
| --- | --- |
| Activate local venv | `source .venv/bin/activate` |
| Run tests | `pytest -q` |
| Build package | `python -m build` |

CI runs the test suite on Python 3.11 and 3.12 and builds the package.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `options-put-call-report` is not found after install | Shell has not picked up pipx's PATH update, or the local venv is not active | Restart the shell or source your shell profile after `python3 -m pipx ensurepath`; in a checkout, run `source .venv/bin/activate` or use `./.venv/bin/options-put-call-report`. |
| Browser collection fails immediately | Playwright Chromium is missing | For pipx installs, run `python3 -m pipx run --spec playwright playwright install chromium`. In a checkout, run `python -m playwright install chromium`. |
| Barchart collection fails for one symbol | Barchart page or network response failed | Inspect `archive/YYYY-MM-DD/{SYMBOL}-failure.html` and `{SYMBOL}-failure.png`; if fallback succeeds, also inspect `{SYMBOL}-yfin-raw.json`. |
| Report uses yfin.dev fallback | Barchart failed and fallback succeeded | Check the report data-source disclosure and `{SYMBOL}-yfin-raw.json`; Barchart-only IV Rank/Percentile metrics may be unavailable. |
| `setup-email` cannot store the API key | System keyring is locked, unavailable, denied, missing a backend, or refusing to replace a different existing item | Read the `Keyring error:` detail printed by setup, unlock/configure the desktop keyring, delete/rotate the stale item if needed, or use `RESEND_API_KEY` / `RESEND_API_KEY_FILE` instead. |
| Email send fails | Resend API key, verified sender, local recipient config, or Resend API request is invalid | Re-run `options-put-call-report setup-email`, confirm `config/email.local.json` exists locally, verify the sender in Resend, and inspect the Resend stage/status in the error. |
| Fresh install has no `config/symbols.json` | GitHub install uses packaged defaults | Run without a config file to use packaged defaults, or pass symbols in the terminal or via `--symbols-file`. |

## Security and privacy

| Do not commit | Why |
| --- | --- |
| `config/email.local.json` | Contains local sender/recipient metadata. |
| Resend API keys | Secrets belong in env vars, secret files, or the system keyring. |
| `archive/` | Generated reports and diagnostics can include local market snapshots. |
| `data/` | Local SQLite history. |

## License

MIT. See `LICENSE`.

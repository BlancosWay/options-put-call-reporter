# Options Put/Call Reporter

Daily Barchart put/call ratio sentiment reporter for a stock watchlist. The tool collects options-expiration data, classifies monthly put/call signals, tracks history, renders reports, and can optionally email the report through Resend.

> Not financial advice. This project summarizes options sentiment data for research and automation. Verify all market data independently before making trading or investment decisions.

## Quick start

### Install as a CLI with pipx

Use this path when you want the CLI installed globally:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
python3 -m pipx run --spec playwright playwright install chromium
options-put-call-report run --no-email
```

### Run from a local checkout

Use this path when you cloned the repository and want to run or modify the code:

```bash
git clone https://github.com/BlancosWay/options-put-call-reporter.git
cd options-put-call-reporter
python3.11 scripts/setup_local.py
./.venv/bin/options-put-call-report run --no-email
```

If you prefer activating the environment, run `source .venv/bin/activate`, then use the shorter `options-put-call-report ...` commands.

See [docs/SETUP.md](docs/SETUP.md) for Windows commands, manual setup, and troubleshooting.

## Common commands

| Task | Command |
| --- | --- |
| Run default watchlist without email | `options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` |
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

| Area | Summary |
| --- | --- |
| Collection | Collects Barchart put/call ratio data with Playwright Chromium. |
| Fallback data | Falls back to yfin.dev options-chain data when Barchart collection fails. |
| Reports | Produces HTML, Markdown, CSV, JSON, and raw diagnostic outputs. |
| Transparency | Reports disclose the data source used for each symbol. |
| History | Tracks snapshots in SQLite and reports day/week/month drift when prior data exists. |
| Symbols | Supports packaged defaults, terminal symbols, and plain-text symbol files. |
| Email | Sends Resend email reports using a Resend API key from the environment, a secret file, or the system keyring. |
| Scheduling | Includes launchd scripts for local daily runs on macOS. |
| Assistant docs | Ships assistant instructions for Claude Code, GitHub Copilot, Codex, and Gemini. |

## Outputs and signal meaning

A run writes reports and diagnostics under `archive/YYYY-MM-DD/`, including `report.html`, `report.md`, per-symbol CSV/JSON snapshots, and raw collection diagnostics.

The monthly signal classifies expiration rows as bullish, bearish, or neutral using the reporter's put/call ratio thresholds. Use it as options-sentiment research, not as a trade recommendation.

See [docs/OUTPUTS.md](docs/OUTPUTS.md) for output files, fallback artifacts, and how to read report fields.

## Email

Email delivery uses Resend. Email delivery reads the Resend API key from `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring. On desktop machines, `options-put-call-report setup-email` stores the key in the system keyring and writes sender/recipient metadata to ignored local config.

See [docs/EMAIL.md](docs/EMAIL.md) for desktop setup, CI/server secrets, keyring behavior, and safe troubleshooting.

## Scheduler

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
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributor expectations. |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting and sensitive local files. |
| [assistant-pack/README.md](assistant-pack/README.md) | Portable assistant instructions. |

This repository includes assistant instructions for maintaining and operating the tool:

- `AGENTS.md` for Codex-style agents.
- `CLAUDE.md` for Claude Code.
- `GEMINI.md` for Gemini CLI.
- `.github/copilot-instructions.md` for GitHub Copilot.
- `assistant-pack/` for portable skill/prompt files.

See `assistant-pack/README.md` for copy/install guidance.

## Development

```bash
python3.11 scripts/setup_local.py
source .venv/bin/activate
pytest -q
python -m build
```

CI runs the test suite on Python 3.11 and 3.12 and builds the package.

## License

MIT. See [LICENSE](LICENSE).

# Setup Guide

This guide covers install and run paths for `options-put-call-report`.

## Prerequisites

| Requirement | macOS/Linux check | Windows PowerShell check | Notes |
| --- | --- | --- | --- |
| Python 3.11+ | `python3.11 --version` | `py -3.11 --version` | Python 3.12 also works. |
| Git | `git --version` | `git --version` | Needed for GitHub installs and local checkouts. |
| pip | `python3 -m pip --version` | `py -m pip --version` | Needed to install `pipx` and local development dependencies. |

You also need internet access for GitHub installs, Playwright Chromium downloads, Barchart collection, yfin.dev fallback, and Resend email.

On Linux, Playwright Chromium also needs browser system libraries. The Linux commands below use `python -m playwright install --with-deps chromium` where those libraries may be missing.

## Choose your setup

| If you want to... | Use this setup | Command style after setup |
| --- | --- | --- |
| Install and run the tool like an app | [Install from GitHub](#install-from-github) with `pipx` | `options-put-call-report ...` |
| Work from this cloned repository | [Local checkout setup](#local-checkout-setup) script | `./.venv/bin/options-put-call-report ...` |
| Activate the local environment once per shell | Local checkout `.venv` | `options-put-call-report ...` |
| Run on a server, container, or CI | Package install plus env/file secrets | `options-put-call-report ...` with `RESEND_API_KEY` or `RESEND_API_KEY_FILE` |

The docs usually show `options-put-call-report ...` because that is the normal installed command. In a local checkout, either activate the venv first or call the executable by its full path.

## Install from GitHub

Use this path when you want the CLI installed globally through `pipx`.

### macOS

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium
options-put-call-report run --no-email
```

### Linux

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
python3 -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install --with-deps chromium
options-put-call-report run --no-email
```

The Linux Chromium install may ask for `sudo` so Playwright can install missing OS packages. If your host already has browser dependencies, `python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium` is enough.

### Windows PowerShell

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
py -m pipx install git+https://github.com/BlancosWay/options-put-call-reporter.git
py -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium
options-put-call-report run --no-email
```

After `ensurepath`, restart your shell or terminal before running `options-put-call-report`. On macOS/Linux, sourcing your shell profile is also enough.

## Local checkout setup

Use this path when you cloned the repository and want to run or modify the code locally.

```bash
git clone https://github.com/BlancosWay/options-put-call-reporter.git
cd options-put-call-reporter
python3.11 scripts/setup_local.py
```

The setup script creates `.venv`, upgrades pip, installs the package with dev tools, installs Playwright Chromium, and prints the run command.

After setup, run without activating anything:

```bash
./.venv/bin/options-put-call-report run --no-email
```

Or activate once per shell and use the shorter command:

```bash
source .venv/bin/activate
options-put-call-report run --no-email
```

Windows PowerShell:

```powershell
py -3.11 scripts\setup_local.py
.\.venv\Scripts\options-put-call-report.exe run --no-email
```

Or activate once per PowerShell session:

```powershell
.\.venv\Scripts\Activate.ps1
options-put-call-report run --no-email
```

Manual fallback for macOS if you do not want to use the setup script:

```bash
python3.11 -m venv --symlinks .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

Manual fallback for Linux:

```bash
python3.11 -m venv --symlinks .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install --with-deps chromium
```

Manual fallback for Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## Quickstart commands

| Task | Installed / activated command | Local no-activation command |
| --- | --- | --- |
| Run default watchlist without email | `options-put-call-report run --no-email` | `./.venv/bin/options-put-call-report run --no-email` |
| Run selected symbols | `options-put-call-report run --no-email META MSFT NOW` | `./.venv/bin/options-put-call-report run --no-email META MSFT NOW` |
| Run symbols from a file | `options-put-call-report run --no-email --symbols-file watchlist.txt` | `./.venv/bin/options-put-call-report run --no-email --symbols-file watchlist.txt` |
| Configure Resend email | `options-put-call-report setup-email` | `./.venv/bin/options-put-call-report setup-email` |
| Run and send email | `options-put-call-report run --send-email` | `./.venv/bin/options-put-call-report run --send-email` |

Runs print concise progress by default, including the symbol count, each symbol collection step, report rendering, and email send status when email is enabled.

## Advanced commands

| Task | Command |
| --- | --- |
| Use a custom app config | `options-put-call-report run --config config/symbols.json --no-email` |
| Use a custom email config | `options-put-call-report run --send-email --email-config path/to/email.local.json` |
| Use a fixed run date | `options-put-call-report run --no-email --run-date 2026-06-02T21:30:00` |
| Install Playwright Chromium for pipx install on macOS/Windows | `python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium` |
| Install Playwright Chromium plus Linux system dependencies | `python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install --with-deps chromium` |
| Install Playwright Chromium in a checkout | `python -m playwright install chromium` |
| Install Playwright Chromium plus Linux system dependencies in a checkout | `python -m playwright install --with-deps chromium` |

## Scheduling by environment

| Environment | Scheduler | Command to schedule |
| --- | --- | --- |
| macOS | Included `launchd` scripts | Run `./scripts/install_launch_agent.sh` from a checkout after `options-put-call-report run --send-email` succeeds manually. |
| Linux | cron or systemd timer | Schedule `options-put-call-report run --send-email` from an activated venv or global install. |
| Windows | Windows Task Scheduler | Schedule `options-put-call-report run --send-email` from PowerShell after email setup succeeds. |

For cron, systemd, and Windows Task Scheduler, set the working directory to the repository or app data directory you want to use, and prefer an absolute executable path such as `./.venv/bin/options-put-call-report` or `.\.venv\Scripts\options-put-call-report.exe`.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `options-put-call-report` is not found after install | Shell has not picked up pipx's PATH update, or the local venv is not active | Restart the shell or source your shell profile after `python3 -m pipx ensurepath`; in a checkout, run `source .venv/bin/activate` or use `./.venv/bin/options-put-call-report`. |
| Browser collection fails immediately | Playwright Chromium or Linux browser system dependencies are missing | For pipx installs on macOS/Windows, run `python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install chromium`. On Linux, run `python3 -m pipx run --spec 'playwright>=1.46,<2' playwright install --with-deps chromium`. In a checkout, run `python -m playwright install chromium` or `python -m playwright install --with-deps chromium` on Linux. |
| Browser error mentions a missing Playwright executable or browser revision | Playwright was upgraded after the browser was installed | Re-run the matching Playwright install command from this guide. For pipx installs, keep the `--spec 'playwright>=1.46,<2'` range so the installer matches this package's supported Playwright range. |
| Fresh install has no `config/symbols.json` | GitHub install uses packaged defaults | Run without a config file to use packaged defaults, or pass symbols in the terminal or via `--symbols-file`. |
| Local setup says existing `.venv` is not usable | The venv is incomplete, stale, uses an old Python, or has broken pip | Remove `.venv`, then rerun `python3.11 scripts/setup_local.py`. |

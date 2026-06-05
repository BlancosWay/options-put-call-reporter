# Options Put/Call Reporter

Local daily reporter for Barchart put/call ratio pages.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## Gmail setup

Run the interactive setup command. It asks for the sender email, recipient email, and Gmail App Password. The app password is stored in macOS Keychain under `options-put-call-reporter:gmail-app-password`.

```bash
source .venv/bin/activate
options-put-call-report setup-email
```

## Manual run

Save the report locally without sending email:

```bash
source .venv/bin/activate
options-put-call-report run --no-email
```

Collect, analyze, archive, and send email:

```bash
source .venv/bin/activate
options-put-call-report run --send-email
```

## Scheduler

Before installing the scheduler, confirm that a manual email run succeeds:

```bash
source .venv/bin/activate
options-put-call-report run --send-email
```

Install the launchd job:

```bash
./scripts/install_launch_agent.sh
```

The scheduled job runs at 2:30 PM Pacific Time, which corresponds to 5:30 PM Eastern Time.

Check scheduler status:

```bash
launchctl list | grep com.sri.options-put-call-reporter
```

Logs are written to:

- `archive/runner.log`
- `archive/launchd.out.log`
- `archive/launchd.err.log`

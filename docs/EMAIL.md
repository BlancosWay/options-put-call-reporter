# Email Setup

`options-put-call-report` can send reports through Resend. The Resend API key is a secret; never commit it or paste it into chat.

Create a free Resend account, verify a sender identity or domain, and create a Resend API key. Review [Resend Usage Limits](https://resend.com/docs/api-reference/rate-limit) for rate limits, email sending quotas, and 429 responses.

## What email needs

| Requirement | Where it lives | Secret? | Notes |
| --- | --- | --- | --- |
| Resend API key | `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or system keyring | Yes | Never commit it or paste it into chat. |
| Sender address | `config/email.local.json` or `--email-config` file | No | Must be verified in Resend. |
| Recipient address | `config/email.local.json` or `--email-config` file | No | Used as the report recipient. |

Every `run --send-email` invocation also needs sender/recipient metadata in `config/email.local.json` or a JSON file passed with `--email-config`; that file must contain `from_email` and `to_email`.

## API key lookup order

| Priority | Source | Best for |
| --- | --- | --- |
| 1 | `RESEND_API_KEY` environment variable | CI and secret-manager injection. |
| 2 | `RESEND_API_KEY_FILE`, a file containing only the API key | Servers, containers, and mounted secrets. |
| 3 | System keyring through Python `keyring` | Desktop macOS, Windows, and Linux sessions with an unlocked keyring backend. |

## Desktop setup

Use the interactive setup on desktop machines:

```bash
options-put-call-report setup-email
options-put-call-report run --send-email
```

The setup command asks for the verified sender address, recipient email, and Resend API key. It writes only sender/recipient metadata to `config/email.local.json` and stores the API key in the system keyring: macOS Keychain, Windows Credential Manager, or Linux Secret Service/KWallet.

If keyring storage fails but the same key is already readable from the system keyring, setup reuses that existing item and still writes `config/email.local.json`. Other keyring storage failures include the underlying `keyring` exception type and message with the API key omitted.

## Environment variable setup

For CI and secret-manager injection, expose the key as an environment variable. If you need to set it interactively, read it without echoing so the secret is not stored in shell history:

```bash
read -r -s -p "Resend API key: " RESEND_API_KEY
printf '\n'
export RESEND_API_KEY
options-put-call-report run --send-email
```

## Secret file setup

For Linux servers and containers, prefer a mounted secret file. If you need to create one interactively, read the key without echoing it and clear the temporary shell variable after writing the file:

```bash
mkdir -p ~/.config/options-put-call-report
read -r -s -p "Resend API key: " RESEND_API_KEY
printf '\n'
( umask 077; printf '%s\n' "$RESEND_API_KEY" > ~/.config/options-put-call-report/resend-api-key )
unset RESEND_API_KEY
export RESEND_API_KEY_FILE=~/.config/options-put-call-report/resend-api-key
options-put-call-report run --send-email
```

## Environment-specific guidance

| Environment | Install | Secret setup | Maintenance |
| --- | --- | --- | --- |
| macOS desktop | Use `pipx`, or run `python3.11 scripts/setup_local.py` from a checkout. | Run `options-put-call-report setup-email`; keyring stores in macOS Keychain. | Re-run `options-put-call-report setup-email` when rotating Resend keys; use Keychain Access to delete stale entries. |
| Windows desktop | Use `pipx`, or run `py -3.11 scripts\setup_local.py` from a checkout. | Run `options-put-call-report setup-email`; keyring stores in Windows Credential Manager. | Re-run setup when rotating keys; remove stale credentials from Credential Manager. |
| Linux desktop | Use `pipx`, or run the local setup script from a checkout; install a Secret Service/KWallet backend such as GNOME Keyring or KWallet for keyring storage. | Run `options-put-call-report setup-email` in an unlocked desktop session. | If keyring is locked/unavailable, unlock the desktop keyring or use env/file fallback. |
| Linux headless/server | Install Python 3.11+ and the package. | Set `RESEND_API_KEY` or `RESEND_API_KEY_FILE`; also provide `config/email.local.json` or `--email-config`. | Rotate the host secret and restart the scheduler/process. |
| Docker/Kubernetes | Install package in the image. | Mount the Resend key as a secret file and set `RESEND_API_KEY_FILE`; mount email metadata JSON if needed. | Rotate the orchestrator secret and restart workloads. |
| GitHub Actions | Install with `python -m pip install -e ".[dev]"`. | Store the key in repository/environment secrets and expose it as `RESEND_API_KEY`. | Rotate GitHub secret; never print it in logs. |

Older custom app configs created before Resend support need these keys in the existing `config/symbols.json` object before running setup:

```json
{
  "keychain_service": "options-put-call-reporter:resend-api-key",
  "resend_api_url": "https://api.resend.com/emails"
}
```

Keep your existing archive, database, threshold, and symbol settings.

Email failures include Resend stage diagnostics like `stage=connect` or `stage=send`, the Resend endpoint, sender, recipient, HTTP status when available, and the safe exception type/message; the Resend API key is redacted.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `setup-email` cannot store the API key | System keyring is locked, unavailable, denied, missing a backend, or refusing to replace a different existing item | Read the `Keyring error:` detail printed by setup, unlock/configure the desktop keyring, delete/rotate the stale item if needed, or use `RESEND_API_KEY` / `RESEND_API_KEY_FILE` instead. |
| Email send fails | Resend API key, verified sender, local recipient config, or Resend API request is invalid | Re-run `options-put-call-report setup-email`, confirm `config/email.local.json` exists locally, verify the sender in Resend, and inspect the Resend stage/status in the error. |

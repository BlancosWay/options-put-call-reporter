# Security Policy

## Reporting a vulnerability

Open a private security advisory on GitHub if available, or contact the repository owner through GitHub.

## Sensitive data

Never commit Resend API keys, `config/email.local.json`, generated `archive/` files, or `data`. The tool reads Resend API keys from `RESEND_API_KEY`, `RESEND_API_KEY_FILE`, or the system keyring through Python `keyring`.

See `docs/MAINTENANCE.md` for the generated-file checklist used before publishing changes.

## Market data disclaimer

This project collects third-party market data for research reporting. It does not provide financial advice or trade execution.

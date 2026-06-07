# Security Policy

## Reporting a vulnerability

Open a private security advisory on GitHub if available, or contact the repository owner through GitHub.

## Sensitive data

Never commit Resend API keys, `config/email.local.json`, generated `archive/` files, or `data/history.sqlite3`. The tool stores Resend API keys in macOS Keychain through the `setup-email` command.

See `docs/MAINTENANCE.md` for the generated-file checklist used before publishing changes.

## Market data disclaimer

This project collects third-party market data for research reporting. It does not provide financial advice or trade execution.

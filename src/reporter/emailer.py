from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from reporter.models import EmailConfig


class EmailError(RuntimeError):
    pass


def send_email_report(
    email_config: EmailConfig,
    smtp_host: str,
    smtp_port: int,
    app_password: str,
    subject: str,
    html_path: Path,
) -> None:
    html = html_path.read_text(encoding="utf-8")
    message = EmailMessage()
    message["From"] = email_config.from_email
    message["To"] = email_config.to_email
    message["Subject"] = subject
    message.set_content("Daily options put/call report is attached as HTML content.")
    message.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(email_config.from_email, app_password)
            smtp.send_message(message)
    except Exception as exc:
        raise EmailError(f"Failed to send report email to {email_config.to_email}") from exc

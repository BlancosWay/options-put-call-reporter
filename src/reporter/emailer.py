from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from reporter.models import EmailConfig


DEFAULT_SMTP_TIMEOUT_SECONDS = 30


class EmailError(RuntimeError):
    pass


def _safe_exception_message(exc: Exception, app_password: str) -> str:
    message = str(exc)
    if app_password:
        message = message.replace(app_password, "<redacted>")
    return f"{exc.__class__.__name__}: {message}"


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

    stage = "connect"
    error_message: str | None = None
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=DEFAULT_SMTP_TIMEOUT_SECONDS) as smtp:
            stage = "starttls"
            context = ssl.create_default_context()
            smtp.starttls(context=context)
            stage = "login"
            smtp.login(email_config.from_email, app_password)
            stage = "send"
            smtp.send_message(message)
    except Exception as exc:
        error_message = (
            "Failed to send report email to "
            f"{email_config.to_email} "
            f"(stage={stage}, smtp={smtp_host}:{smtp_port}, "
            f"from={email_config.from_email}, to={email_config.to_email}, "
            f"error={_safe_exception_message(exc, app_password)})"
        )
    if error_message is not None:
        raise EmailError(error_message) from None

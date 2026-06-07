from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
import urllib.request

from reporter.models import EmailConfig


DEFAULT_EMAIL_TIMEOUT_SECONDS = 30
_EMAIL_TEXT = "Daily options put/call report is attached as HTML content."


class EmailError(RuntimeError):
    pass


def _redact(value: str, api_key: str) -> str:
    if api_key:
        return value.replace(api_key, "<redacted>")
    return value


def _safe_exception_message(exc: Exception, api_key: str) -> str:
    return f"{exc.__class__.__name__}: {_redact(str(exc), api_key)}"


def _safe_http_error_body(exc: HTTPError, api_key: str) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    return _redact(body, api_key)


def send_email_report(
    email_config: EmailConfig,
    resend_api_url: str,
    api_key: str,
    subject: str,
    html_path: Path,
) -> None:
    html = html_path.read_text(encoding="utf-8")
    payload = {
        "from": email_config.from_email,
        "to": [email_config.to_email],
        "subject": subject,
        "html": html,
        "text": _EMAIL_TEXT,
    }
    request = urllib.request.Request(
        resend_api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    error_message: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_EMAIL_TIMEOUT_SECONDS) as response:
            response.read()
    except HTTPError as exc:
        body = _safe_http_error_body(exc, api_key)
        error_message = (
            "Failed to send report email to "
            f"{email_config.to_email} "
            f"(stage=send, resend={resend_api_url}, status={exc.code}, "
            f"from={email_config.from_email}, to={email_config.to_email}, "
            f"error={_safe_exception_message(exc, api_key)}, body={body})"
        )
    except (URLError, OSError) as exc:
        error_message = (
            "Failed to send report email to "
            f"{email_config.to_email} "
            f"(stage=connect, resend={resend_api_url}, "
            f"from={email_config.from_email}, to={email_config.to_email}, "
            f"error={_safe_exception_message(exc, api_key)})"
        )

    if error_message is not None:
        raise EmailError(error_message) from None

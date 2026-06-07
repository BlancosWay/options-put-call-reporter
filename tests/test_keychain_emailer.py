from email.message import EmailMessage
from pathlib import Path
import smtplib
import subprocess

import pytest

from reporter.emailer import EmailError, send_email_report
from reporter.keychain import KeychainError, get_password, set_password
from reporter.models import EmailConfig


class Completed:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def test_get_password_calls_security_find(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, check, capture_output, text):
        calls.append(args)
        return Completed(stdout="app-password\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    assert get_password("service", "user@gmail.com") == "app-password"
    assert calls[0][:3] == ["security", "find-generic-password", "-a"]


def test_set_password_calls_security_add(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    inputs: list[str] = []

    def fake_run(args, check, capture_output, text, input=None):
        calls.append(args)
        inputs.append(input)
        return Completed()

    monkeypatch.setattr("subprocess.run", fake_run)

    secret = "secret"
    set_password("service", "user@gmail.com", secret)
    assert "add-generic-password" in calls[0]
    assert "-U" in calls[0]
    assert calls[0][-1] == "-w"
    assert secret not in calls[0]
    assert inputs == [f"{secret}\n{secret}\n"]


def test_get_password_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args, check, capture_output, text):
        raise OSError("security missing")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(KeychainError, match="Keychain"):
        get_password("service", "user@gmail.com")


def test_set_password_raises_without_leaking_secret_in_exception_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "gmail-app-password-secret"

    def fake_run(args, check, capture_output, text, input=None):
        assert secret not in args
        raise subprocess.CalledProcessError(returncode=1, cmd=args)

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(KeychainError) as exc:
        set_password("service", "user@gmail.com", secret)

    assert secret not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_send_email_report_uses_tls_and_login(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<h1>Report</h1>", encoding="utf-8")
    events: list[str] = []
    tls_contexts: list[object] = []
    sent_messages: list[EmailMessage] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, *, timeout: float) -> None:
            events.append(f"connect:{host}:{port}:timeout={timeout:g}")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append("close")

        def starttls(self, *, context: object) -> None:
            tls_contexts.append(context)
            events.append("tls")

        def login(self, user: str, password: str) -> None:
            events.append(f"login:{user}:{password}")

        def send_message(self, message: EmailMessage) -> None:
            sent_messages.append(message)
            events.append(f"send:{message['To']}")

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    send_email_report(
        email_config=EmailConfig("sender@gmail.com", "recipient@gmail.com"),
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        app_password="abc123",
        subject="Daily report",
        html_path=html_path,
    )

    assert events == [
        "connect:smtp.gmail.com:587:timeout=30",
        "tls",
        "login:sender@gmail.com:abc123",
        "send:recipient@gmail.com",
        "close",
    ]
    assert tls_contexts[0] is not None
    assert len(sent_messages) == 1

    message = sent_messages[0]
    assert message["From"] == "sender@gmail.com"
    assert message["To"] == "recipient@gmail.com"
    assert message["Subject"] == "Daily report"

    plain_body = message.get_body(preferencelist=("plain",))
    assert plain_body is not None
    assert "Daily options put/call report" in plain_body.get_content()

    html_body = message.get_body(preferencelist=("html",))
    assert html_body is not None
    assert "<h1>Report</h1>" in html_body.get_content()


def test_send_email_report_failure_includes_smtp_stage_and_safe_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<h1>Report</h1>", encoding="utf-8")

    class FakeSMTP:
        def __init__(self, host: str, port: int, *, timeout: float) -> None:
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def starttls(self, *, context: object) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)

    with pytest.raises(EmailError) as exc:
        send_email_report(
            email_config=EmailConfig("sender@gmail.com", "recipient@gmail.com"),
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            app_password="super-secret-app-password",
            subject="Daily report",
            html_path=html_path,
        )

    message = str(exc.value)
    assert "Failed to send report email to recipient@gmail.com" in message
    assert "stage=login" in message
    assert "smtp=smtp.gmail.com:587" in message
    assert "from=sender@gmail.com" in message
    assert "to=recipient@gmail.com" in message
    assert "SMTPAuthenticationError" in message
    assert "Username and Password not accepted" in message
    assert "super-secret-app-password" not in message

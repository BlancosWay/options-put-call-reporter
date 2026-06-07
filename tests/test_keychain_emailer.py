import io
import json
from pathlib import Path
import subprocess
import traceback
from urllib.error import HTTPError, URLError

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
        return Completed(stdout="api-key\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    assert get_password("service", "user@example.com") == "api-key"
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
    set_password("service", "user@example.com", secret)
    assert "add-generic-password" in calls[0]
    assert "-U" in calls[0]
    assert calls[0][-1] == "-w"
    assert secret not in calls[0]
    assert inputs == [f"{secret}\n{secret}\n"]


def test_set_password_rejects_empty_email_api_key() -> None:
    with pytest.raises(KeychainError, match="Cannot store an empty email API key in Keychain"):
        set_password("service", "reports@example.com", "")


def test_get_password_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args, check, capture_output, text):
        raise OSError("security missing")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(KeychainError, match="Keychain"):
        get_password("service", "user@example.com")


def test_set_password_raises_without_leaking_secret_in_exception_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "email-api-key-secret"

    def fake_run(args, check, capture_output, text, input=None):
        assert secret not in args
        raise subprocess.CalledProcessError(returncode=1, cmd=args)

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(KeychainError) as exc:
        set_password("service", "user@example.com", secret)

    assert secret not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_set_password_failure_mentions_email_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args, check, capture_output, text, input=None):
        raise subprocess.CalledProcessError(returncode=1, cmd=args)

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(
        KeychainError,
        match="Unable to store email API key in Keychain for account 'reports@example.com'",
    ) as exc:
        set_password("service", "reports@example.com", "re_secret")

    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_send_email_report_posts_html_to_resend(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<h1>Report</h1>", encoding="utf-8")
    requests = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self) -> bytes:
            return b'{"id":"email_123"}'

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    send_email_report(
        email_config=EmailConfig("reports@example.com", "recipient@example.com"),
        resend_api_url="https://api.resend.com/emails",
        api_key="re_secret",
        subject="Daily report",
        html_path=html_path,
    )

    request, timeout = requests[0]
    assert timeout == 30
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_method() == "POST"
    assert request.headers["Authorization"] == "Bearer re_secret"
    assert request.headers["Content-type"] == "application/json"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload == {
        "from": "reports@example.com",
        "to": ["recipient@example.com"],
        "subject": "Daily report",
        "html": "<h1>Report</h1>",
        "text": "Daily options put/call report is attached as HTML content.",
    }


def test_send_email_report_http_failure_includes_safe_resend_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<h1>Report</h1>", encoding="utf-8")
    api_key = "re_super_secret"

    def fake_urlopen(request, timeout):
        raise HTTPError(
            url=request.full_url,
            code=403,
            msg=f"forbidden {api_key}",
            hdrs={},
            fp=io.BytesIO(f'{{"message":"bad key {api_key}"}}'.encode("utf-8")),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(EmailError) as exc:
        send_email_report(
            email_config=EmailConfig("reports@example.com", "recipient@example.com"),
            resend_api_url="https://api.resend.com/emails",
            api_key=api_key,
            subject="Daily report",
            html_path=html_path,
        )

    message = str(exc.value)
    assert "Failed to send report email to recipient@example.com" in message
    assert "stage=send" in message
    assert "resend=https://api.resend.com/emails" in message
    assert "status=403" in message
    assert "from=reports@example.com" in message
    assert "to=recipient@example.com" in message
    assert "<redacted>" in message
    assert api_key not in message
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_send_email_report_url_failure_does_not_leak_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<h1>Report</h1>", encoding="utf-8")
    api_key = "re_super_secret"

    def fake_urlopen(request, timeout):
        raise URLError(f"network failed {api_key}")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(EmailError) as exc:
        send_email_report(
            email_config=EmailConfig("reports@example.com", "recipient@example.com"),
            resend_api_url="https://api.resend.com/emails",
            api_key=api_key,
            subject="Daily report",
            html_path=html_path,
        )

    traceback_text = "".join(traceback.format_exception(exc.value))
    assert "stage=connect" in str(exc.value)
    assert api_key not in str(exc.value)
    assert api_key not in traceback_text
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None

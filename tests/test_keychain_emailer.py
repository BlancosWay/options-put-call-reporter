import io
import json
from pathlib import Path
import traceback
from urllib.error import HTTPError, URLError

import pytest

from reporter.emailer import EmailError, send_email_report
from reporter.keychain import KeychainError, get_password, set_password
from reporter.models import EmailConfig


def test_get_password_prefers_resend_api_key_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret_file = tmp_path / "resend-key"
    secret_file.write_text("re_from_file\n", encoding="utf-8")
    monkeypatch.setenv("RESEND_API_KEY", "re_from_env")
    monkeypatch.setenv("RESEND_API_KEY_FILE", str(secret_file))
    monkeypatch.setattr("reporter.keychain.keyring.get_password", lambda service, account: "re_from_keyring")

    assert get_password("service", "user@example.com") == "re_from_env"


def test_get_password_reads_resend_api_key_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret_file = tmp_path / "resend-key"
    secret_file.write_text("re_from_file\n", encoding="utf-8")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("RESEND_API_KEY_FILE", str(secret_file))
    monkeypatch.setattr("reporter.keychain.keyring.get_password", lambda service, account: "re_from_keyring")

    assert get_password("service", "user@example.com") == "re_from_file"


def test_get_password_uses_system_keyring_after_env_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_get_password(service: str, account: str) -> str:
        calls.append((service, account))
        return "re_from_keyring"

    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)
    monkeypatch.setattr("reporter.keychain.keyring.get_password", fake_get_password)

    assert get_password("service", "user@example.com") == "re_from_keyring"
    assert calls == [("service", "user@example.com")]


def test_get_password_raises_actionable_error_when_no_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)
    monkeypatch.setattr("reporter.keychain.keyring.get_password", lambda service, account: None)

    with pytest.raises(
        KeychainError,
        match="Set RESEND_API_KEY, set RESEND_API_KEY_FILE, or run setup-email",
    ):
        get_password("service", "user@example.com")


def test_get_password_rejects_empty_env_without_falling_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "   ")
    monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)
    monkeypatch.setattr(
        "reporter.keychain.keyring.get_password",
        lambda service, account: (_ for _ in ()).throw(AssertionError("keyring should not be used")),
    )

    with pytest.raises(KeychainError, match="RESEND_API_KEY is set but empty"):
        get_password("service", "user@example.com")


def test_get_password_rejects_empty_key_file_without_leaking_secret_path_contents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_file = tmp_path / "resend-key"
    secret_file.write_text("\n", encoding="utf-8")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("RESEND_API_KEY_FILE", str(secret_file))

    with pytest.raises(KeychainError, match="RESEND_API_KEY_FILE points to an empty file") as exc:
        get_password("service", "user@example.com")

    assert str(secret_file) not in str(exc.value)
    assert "resend-key" not in str(exc.value)


def test_get_password_rejects_unreadable_key_file_without_leaking_env_value(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_path = str(tmp_path / "secret-re_path-value")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("RESEND_API_KEY_FILE", secret_path)

    with pytest.raises(KeychainError, match="RESEND_API_KEY_FILE is set but could not be read") as exc:
        get_password("service", "user@example.com")

    assert secret_path not in str(exc.value)
    assert "secret-re_path-value" not in str(exc.value)


def test_get_password_rejects_invalid_utf8_key_file_without_leaking_env_value(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret_file = tmp_path / "secret-re_invalid_utf8"
    secret_file.write_bytes(b"re_valid_prefix_\xff\xfe\n")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("RESEND_API_KEY_FILE", str(secret_file))

    with pytest.raises(KeychainError, match="RESEND_API_KEY_FILE is set but could not be read") as exc:
        get_password("service", "user@example.com")

    assert str(secret_file) not in str(exc.value)
    assert "secret-re_invalid_utf8" not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_get_password_treats_empty_keyring_secret_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)
    monkeypatch.setattr("reporter.keychain.keyring.get_password", lambda service, account: "")

    with pytest.raises(
        KeychainError,
        match="Set RESEND_API_KEY, set RESEND_API_KEY_FILE, or run setup-email",
    ) as exc:
        get_password("service", "user@example.com")

    assert "user@example.com" in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_get_password_keyring_read_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "re_secret_from_backend_error"

    def fake_get_password(service: str, account: str) -> str:
        raise RuntimeError(f"backend leaked {secret}")

    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY_FILE", raising=False)
    monkeypatch.setattr("reporter.keychain.keyring.get_password", fake_get_password)

    with pytest.raises(
        KeychainError,
        match=(
            "Unable to read the system keyring. Set RESEND_API_KEY, "
            "set RESEND_API_KEY_FILE, or configure a working keyring backend."
        ),
    ) as exc:
        get_password("service", "user@example.com")

    assert secret not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_set_password_stores_secret_in_system_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_set_password(service: str, account: str, password: str) -> None:
        calls.append((service, account, password))

    monkeypatch.setattr("reporter.keychain.keyring.set_password", fake_set_password)

    set_password("service", "reports@example.com", "  re_secret  ")

    assert calls == [("service", "reports@example.com", "re_secret")]


def test_set_password_rejects_empty_email_api_key() -> None:
    with pytest.raises(KeychainError, match="Cannot store an empty email API key in the system keyring"):
        set_password("service", "reports@example.com", "")


def test_set_password_rejects_whitespace_only_email_api_key() -> None:
    with pytest.raises(KeychainError, match="Cannot store an empty email API key in the system keyring"):
        set_password("service", "reports@example.com", "   ")


def test_set_password_normalizes_keyring_failure_without_leaking_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "re_secret_value"

    def fake_set_password(service: str, account: str, password: str) -> None:
        raise RuntimeError(f"backend failed for {password}")

    monkeypatch.setattr("reporter.keychain.keyring.set_password", fake_set_password)

    with pytest.raises(
        KeychainError,
        match="Unable to store email API key in the system keyring for account 'reports@example.com'",
    ) as exc:
        set_password("service", "reports@example.com", secret)

    assert secret not in str(exc.value)
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
    assert request.headers["User-agent"] == "options-put-call-reporter/0.1.0"
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


def test_send_email_report_truncates_large_http_error_body_after_redaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text("<h1>Report</h1>", encoding="utf-8")
    api_key = "re_super_secret"
    body = f'{{"message":"bad key {api_key} {"x" * 1500} tail-marker"}}'

    def fake_urlopen(request, timeout):
        raise HTTPError(
            url=request.full_url,
            code=403,
            msg="forbidden",
            hdrs={},
            fp=io.BytesIO(body.encode("utf-8")),
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
    assert "<redacted>" in message
    assert "<truncated>" in message
    assert "tail-marker" not in message
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

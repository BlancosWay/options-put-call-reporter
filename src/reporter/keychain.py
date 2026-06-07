from __future__ import annotations

import os
from pathlib import Path

import keyring


RESEND_API_KEY_ENV = "RESEND_API_KEY"
RESEND_API_KEY_FILE_ENV = "RESEND_API_KEY_FILE"


class KeychainError(RuntimeError):
    pass


def _trim_secret(secret: str | None) -> str | None:
    if secret is None:
        return None
    return secret.strip()


def _missing_secret_message(account: str) -> str:
    return (
        f"Email API key not found for account '{account}'. "
        f"Set {RESEND_API_KEY_ENV}, set {RESEND_API_KEY_FILE_ENV}, "
        "or run setup-email to store it in the system keyring."
    )


def _keyring_read_error_message() -> str:
    return (
        f"Unable to read the system keyring. Set {RESEND_API_KEY_ENV}, "
        f"set {RESEND_API_KEY_FILE_ENV}, or configure a working keyring backend."
    )


def _safe_exception_detail(exc: Exception, secret: str) -> str:
    message = str(exc).replace(secret, "<secret omitted>")
    if message:
        return f"{exc.__class__.__name__}: {message}"
    return exc.__class__.__name__


def get_password(service: str, account: str) -> str:
    env_secret = os.environ.get(RESEND_API_KEY_ENV)
    if env_secret is not None:
        secret = _trim_secret(env_secret)
        if not secret:
            raise KeychainError(f"{RESEND_API_KEY_ENV} is set but empty")
        return secret

    key_file = os.environ.get(RESEND_API_KEY_FILE_ENV)
    if key_file is not None:
        path = Path(key_file).expanduser()
        read_failed = False
        secret_text = None
        try:
            secret_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            read_failed = True
        if read_failed:
            raise KeychainError(f"{RESEND_API_KEY_FILE_ENV} is set but could not be read") from None
        secret = _trim_secret(secret_text)
        if not secret:
            raise KeychainError(f"{RESEND_API_KEY_FILE_ENV} points to an empty file")
        return secret

    keyring_failed = False
    keyring_secret = None
    try:
        keyring_secret = keyring.get_password(service, account)
    except Exception:
        keyring_failed = True
    if keyring_failed:
        raise KeychainError(_keyring_read_error_message()) from None
    secret = _trim_secret(keyring_secret)
    if not secret:
        raise KeychainError(_missing_secret_message(account))
    return secret


def set_password(service: str, account: str, password: str) -> None:
    secret = _trim_secret(password)
    if not secret:
        raise KeychainError("Cannot store an empty email API key in the system keyring")
    storage_error = None
    try:
        keyring.set_password(service, account, secret)
    except Exception as exc:
        storage_error = exc
    if storage_error:
        detail = _safe_exception_detail(storage_error, secret)
        raise KeychainError(
            f"Unable to store email API key in the system keyring for account '{account}'. "
            f"Keyring error: {detail}"
        ) from None

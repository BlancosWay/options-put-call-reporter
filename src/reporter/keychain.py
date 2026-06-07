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
        try:
            secret = _trim_secret(path.read_text(encoding="utf-8"))
        except OSError:
            raise KeychainError(f"{RESEND_API_KEY_FILE_ENV} could not be read: {path}") from None
        if not secret:
            raise KeychainError(f"{RESEND_API_KEY_FILE_ENV} is empty: {path}")
        return secret

    try:
        secret = _trim_secret(keyring.get_password(service, account))
    except Exception:
        raise KeychainError(_missing_secret_message(account)) from None
    if not secret:
        raise KeychainError(_missing_secret_message(account))
    return secret


def set_password(service: str, account: str, password: str) -> None:
    if not password:
        raise KeychainError("Cannot store an empty email API key in the system keyring")
    storage_failed = False
    try:
        keyring.set_password(service, account, password)
    except Exception:
        storage_failed = True
    if storage_failed:
        raise KeychainError(
            f"Unable to store email API key in the system keyring for account '{account}'"
        ) from None

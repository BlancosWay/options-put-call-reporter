from __future__ import annotations

import subprocess


class KeychainError(RuntimeError):
    pass


def get_password(service: str, account: str) -> str:
    try:
        completed = subprocess.run(
            ["security", "find-generic-password", "-a", account, "-s", service, "-w"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        raise KeychainError(f"Email API key not found in Keychain for account '{account}'") from None
    password = completed.stdout.strip()
    if not password:
        raise KeychainError(f"Keychain returned an empty email API key for account '{account}'")
    return password


def set_password(service: str, account: str, password: str) -> None:
    if not password:
        raise KeychainError("Cannot store an empty email API key in Keychain")
    failed = False
    try:
        subprocess.run(
            ["security", "add-generic-password", "-a", account, "-s", service, "-U", "-w"],
            check=True,
            capture_output=True,
            text=True,
            input=f"{password}\n{password}\n",
        )
    except Exception:
        failed = True
    if failed:
        raise KeychainError(f"Unable to store email API key in Keychain for account '{account}'") from None

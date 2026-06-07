from __future__ import annotations

import ctypes
import ctypes.util
import subprocess


ERR_SEC_SUCCESS = 0
ERR_SEC_DUPLICATE_ITEM = -25299


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


def _load_framework(name: str) -> ctypes.CDLL:
    path = ctypes.util.find_library(name)
    if not path:
        raise KeychainError(f"macOS {name}.framework is required to store email API keys")
    return ctypes.CDLL(path)


def _security_framework() -> ctypes.CDLL:
    return _load_framework("Security")


def _core_foundation_framework() -> ctypes.CDLL:
    return _load_framework("CoreFoundation")


def _add_generic_password(service: str, account: str, password: str) -> int:
    security = _security_framework()
    add = security.SecKeychainAddGenericPassword
    add.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    add.restype = ctypes.c_int32

    service_bytes = service.encode("utf-8")
    account_bytes = account.encode("utf-8")
    password_bytes = password.encode("utf-8")
    password_buffer = ctypes.create_string_buffer(password_bytes)

    return int(
        add(
            None,
            len(service_bytes),
            service_bytes,
            len(account_bytes),
            account_bytes,
            len(password_bytes),
            ctypes.cast(password_buffer, ctypes.c_void_p),
            None,
        )
    )


def _update_generic_password(service: str, account: str, password: str) -> int:
    security = _security_framework()
    find = security.SecKeychainFindGenericPassword
    find.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    find.restype = ctypes.c_int32
    modify = security.SecKeychainItemModifyAttributesAndData
    modify.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    modify.restype = ctypes.c_int32

    service_bytes = service.encode("utf-8")
    account_bytes = account.encode("utf-8")
    item_ref = ctypes.c_void_p()
    find_status = int(
        find(
            None,
            len(service_bytes),
            service_bytes,
            len(account_bytes),
            account_bytes,
            None,
            None,
            ctypes.byref(item_ref),
        )
    )
    if find_status != ERR_SEC_SUCCESS:
        return find_status

    try:
        password_bytes = password.encode("utf-8")
        password_buffer = ctypes.create_string_buffer(password_bytes)
        return int(
            modify(
                item_ref,
                None,
                len(password_bytes),
                ctypes.cast(password_buffer, ctypes.c_void_p),
            )
        )
    finally:
        if item_ref:
            core_foundation = _core_foundation_framework()
            release = core_foundation.CFRelease
            release.argtypes = [ctypes.c_void_p]
            release.restype = None
            release(item_ref)


def set_password(service: str, account: str, password: str) -> None:
    if not password:
        raise KeychainError("Cannot store an empty email API key in Keychain")
    status = _add_generic_password(service, account, password)
    if status == ERR_SEC_DUPLICATE_ITEM:
        status = _update_generic_password(service, account, password)
    if status != ERR_SEC_SUCCESS:
        raise KeychainError(
            f"Unable to store email API key in Keychain for account '{account}' (status={status})"
        ) from None

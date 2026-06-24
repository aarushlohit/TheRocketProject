"""Best-effort local secret protection for Rocket runtime data."""

from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes
import sys


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def protect_text(value: str) -> str:
    """Protect text with Windows DPAPI when available."""

    if sys.platform != "win32":
        return value
    protected = _crypt_protect(value.encode("utf-8"))
    return "dpapi:" + base64.b64encode(protected).decode("ascii")


def unprotect_text(value: str) -> str:
    """Unprotect DPAPI text, or return plaintext fallback."""

    if not value.startswith("dpapi:") or sys.platform != "win32":
        return value
    payload = base64.b64decode(value.removeprefix("dpapi:"))
    return _crypt_unprotect(payload).decode("utf-8")


def _crypt_protect(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    input_blob = _blob_from_bytes(data)
    output_blob = DATA_BLOB()
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "RocketProfile",
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _crypt_unprotect(data: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    input_blob = _blob_from_bytes(data)
    output_blob = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _blob_from_bytes(data: bytes) -> DATA_BLOB:
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))

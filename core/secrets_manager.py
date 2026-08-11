"""Encryption for credentials at rest, using the Windows Data Protection API.

DPAPI derives its key from the logged-in Windows account, so ciphertext
written here is unreadable by any other user on the machine and by anyone
who copies the file elsewhere. It is what browsers and password managers use
on Windows, needs no dependency, and adds nothing to the installer.

What this does not defend against: code already running as the same user can
call ``CryptUnprotectData`` just as Bruno does. The threat model is other
accounts on a shared machine, a stolen backup, or a credential file pasted
into an issue report -- not local malware, which has already won.

An application-specific entropy value is mixed in, so the blob cannot be
decrypted by another program simply asking DPAPI nicely.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes as wt
from typing import Final

logger = logging.getLogger(__name__)

# Mixed into the key derivation. Not a secret -- it is in the source -- but it
# means another process must know it was Bruno's blob to attempt a decrypt.
_ENTROPY: Final = b"ev-desktop-companion/v1"

CRYPTPROTECT_UI_FORBIDDEN: Final = 0x01


class SecretError(RuntimeError):
    """A credential could not be encrypted or decrypted."""


class _Blob(ctypes.Structure):
    """Win32 ``DATA_BLOB``: a length and a pointer."""

    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    @classmethod
    def of(cls, data: bytes) -> _Blob:
        buffer = ctypes.create_string_buffer(data, len(data))
        return cls(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))

    def value(self) -> bytes:
        return ctypes.string_at(self.pbData, self.cbData)


def is_available() -> bool:
    """Whether DPAPI can be used on this platform."""
    return sys.platform == "win32"


def _crypt32():
    if not is_available():
        raise SecretError(
            "Encrypted credential storage requires Windows. "
            "Set GROQ_API_KEY in the environment instead."
        )
    return ctypes.WinDLL("crypt32", use_last_error=True), ctypes.WinDLL(
        "kernel32", use_last_error=True
    )


def protect(plaintext: str) -> bytes:
    """Encrypt a secret for storage.

    Args:
        plaintext: The value to protect.

    Returns:
        Ciphertext, only decryptable by this Windows account.

    Raises:
        SecretError: If encryption fails or the platform is unsupported.
    """
    crypt32, kernel32 = _crypt32()

    data_in = _Blob.of(plaintext.encode("utf-8"))
    entropy = _Blob.of(_ENTROPY)
    data_out = _Blob()

    ok = crypt32.CryptProtectData(
        ctypes.byref(data_in),
        None,
        ctypes.byref(entropy),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(data_out),
    )
    if not ok:
        raise SecretError(
            f"CryptProtectData failed: {ctypes.WinError(ctypes.get_last_error())}"
        )

    try:
        return data_out.value()
    finally:
        kernel32.LocalFree(data_out.pbData)


def unprotect(ciphertext: bytes) -> str:
    """Decrypt a stored secret.

    Args:
        ciphertext: Output of :func:`protect`.

    Returns:
        The original value.

    Raises:
        SecretError: If decryption fails, which is expected and normal when
            the file was written by a different Windows account or has been
            corrupted.
    """
    crypt32, kernel32 = _crypt32()

    data_in = _Blob.of(ciphertext)
    entropy = _Blob.of(_ENTROPY)
    data_out = _Blob()

    ok = crypt32.CryptUnprotectData(
        ctypes.byref(data_in),
        None,
        ctypes.byref(entropy),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(data_out),
    )
    if not ok:
        raise SecretError(
            f"CryptUnprotectData failed: {ctypes.WinError(ctypes.get_last_error())}"
        )

    try:
        return data_out.value().decode("utf-8")
    finally:
        kernel32.LocalFree(data_out.pbData)

"""Authenticated encryption for backups.

A passphrase is stretched with scrypt and used with Fernet (AES-128-CBC +
HMAC). The salt is stored alongside the ciphertext so a backup file is fully
self-describing: ``HRK1 || salt(16) || fernet_token``.
"""

from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"HRK1"
_SALT_LEN = 16


class BackupCryptoError(Exception):
    """Raised when a backup cannot be decrypted (wrong passphrase / corrupt)."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    raw = kdf.derive(passphrase.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def encrypt(data: bytes, passphrase: str) -> bytes:
    salt = os.urandom(_SALT_LEN)
    token = Fernet(_derive_key(passphrase, salt)).encrypt(data)
    return MAGIC + salt + token


def decrypt(blob: bytes, passphrase: str) -> bytes:
    if not blob.startswith(MAGIC):
        raise BackupCryptoError("Not a Haruka backup file.")
    salt = blob[len(MAGIC):len(MAGIC) + _SALT_LEN]
    token = blob[len(MAGIC) + _SALT_LEN:]
    try:
        return Fernet(_derive_key(passphrase, salt)).decrypt(token)
    except InvalidToken as exc:
        raise BackupCryptoError("Wrong passphrase or corrupted backup.") from exc

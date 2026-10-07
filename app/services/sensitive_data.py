"""Encryption helper for ownership proofs and private recovery messages."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class SensitiveDataService:
    def __init__(self) -> None:
        secret = settings.data_encryption_key or settings.jwt_secret_key
        digest = hashlib.sha256(secret.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken:
            return None


sensitive_data_service = SensitiveDataService()

import json

from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryption:
    def __init__(self, encryption_key: str) -> None:
        self._fernet = Fernet(encryption_key.encode())

    def encrypt(self, credentials: dict[str, str]) -> str:
        payload = json.dumps(credentials).encode()
        return self._fernet.encrypt(payload).decode()

    def decrypt(self, encrypted_credentials: str) -> dict[str, str]:
        try:
            payload = self._fernet.decrypt(encrypted_credentials.encode())
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt credentials") from exc

        data = json.loads(payload.decode())
        if not isinstance(data, dict):
            raise ValueError("Stored credentials are invalid")

        return {str(key): str(value) for key, value in data.items()}

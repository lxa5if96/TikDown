import json

from cryptography.fernet import (
    Fernet,
    InvalidToken,
)

from config import DOWNLOAD_TOKEN_SECRET


# ============================================================
# FERNET
# ============================================================

try:

    fernet = Fernet(
        DOWNLOAD_TOKEN_SECRET.encode()
    )

except Exception as exc:

    raise RuntimeError(
        "DOWNLOAD_TOKEN_SECRET must be a valid Fernet key."
    ) from exc


# ============================================================
# CREATE DOWNLOAD TOKEN
# ============================================================

def create_download_token(
    url: str,
    file_type: str,
    filename: str = "video.mp4",
):

    payload = {
        "url": url,
        "type": file_type,
        "filename": filename,
    }

    payload_json = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode()

    encrypted_token = fernet.encrypt(
        payload_json
    )

    return encrypted_token.decode()


# ============================================================
# VERIFY DOWNLOAD TOKEN
# ============================================================

def verify_download_token(
    token: str,
    max_age: int,
):

    try:

        decrypted = fernet.decrypt(
            token.encode(),
            ttl=max_age,
        )

        payload = json.loads(
            decrypted.decode()
        )

        return payload

    except (
        InvalidToken,
        ValueError,
        json.JSONDecodeError,
    ):

        return None
import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# SECURITY
# ============================================================

DOWNLOAD_TOKEN_SECRET = os.getenv("DOWNLOAD_TOKEN_SECRET")

if not DOWNLOAD_TOKEN_SECRET:
    raise RuntimeError(
        "DOWNLOAD_TOKEN_SECRET is not configured in .env"
    )


DOWNLOAD_TOKEN_MAX_AGE = int(
    os.getenv("DOWNLOAD_TOKEN_MAX_AGE", "300")
)


# ============================================================
# DOWNLOAD LIMIT
# ============================================================

MAX_DOWNLOAD_SIZE = int(
    os.getenv(
        "MAX_DOWNLOAD_SIZE",
        str(100 * 1024 * 1024)  # 100 MB
    )
)


# ============================================================
# CORS
# ============================================================

raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000"
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in raw_origins.split(",")
    if origin.strip()
]
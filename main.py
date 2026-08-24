from fastapi import (
    FastAPI,
    Request,
    HTTPException,
)
from fastapi.responses import (
    HTMLResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pydantic import (
    BaseModel,
    field_validator,
)

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from urllib.parse import urlparse

import logging
import requests


# ============================================================
# SERVICES
# ============================================================

from services.tikwm import get_video

from services.instagram import (
    get_instagram_video,
    is_instagram_url,
    InstagramError,
)

from services.download_token import (
    create_download_token,
    verify_download_token,
)


# ============================================================
# CONFIG
# ============================================================

from config import (
    ALLOWED_ORIGINS,
    DOWNLOAD_TOKEN_MAX_AGE,
    MAX_DOWNLOAD_SIZE,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "video_downloader"
)


# ============================================================
# RATE LIMITER
# ============================================================

limiter = Limiter(
    key_func=get_remote_address
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="TikDown - TikTok & Instagram Downloader",
    version="2.0.0",
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# ============================================================
# TRUSTED HOST
# ============================================================

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "tik-down-nu.vercel.app"
    ],
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
    ],
    allow_headers=[
        "Content-Type",
    ],
)


# ============================================================
# SECURITY HEADERS
# ============================================================

@app.middleware("http")
async def security_headers(
    request: Request,
    call_next,
):

    response = await call_next(request)

    response.headers[
        "X-Content-Type-Options"
    ] = "nosniff"

    response.headers[
        "X-Frame-Options"
    ] = "DENY"

    response.headers[
        "Referrer-Policy"
    ] = "strict-origin-when-cross-origin"

    response.headers[
        "Permissions-Policy"
    ] = (
        "camera=(), "
        "microphone=(), "
        "geolocation=()"
    )

    response.headers[
        "Content-Security-Policy"
    ] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' https: data:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "font-src 'self' https:; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    return response


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# REQUEST MODEL
# ============================================================

class DownloadRequest(BaseModel):

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):

        value = value.strip()

        if len(value) > 2048:

            raise ValueError(
                "URL is too long."
            )

        parsed = urlparse(value)

        if parsed.scheme not in (
            "http",
            "https",
        ):

            raise ValueError(
                "Invalid URL scheme."
            )

        if not parsed.netloc:

            raise ValueError(
                "Invalid URL."
            )

        if not parsed.hostname:

            raise ValueError(
                "Invalid hostname."
            )

        return value


# ============================================================
# PLATFORM DETECTION
# ============================================================

def get_platform(url: str) -> str | None:

    try:

        parsed = urlparse(url)

        hostname = (
            parsed.hostname.lower()
            if parsed.hostname
            else ""
        )

        # -----------------------------
        # INSTAGRAM
        # -----------------------------

        if hostname in {
            "instagram.com",
            "www.instagram.com",
        }:

            if is_instagram_url(url):
                return "instagram"

            return None

        # -----------------------------
        # TIKTOK
        # -----------------------------

        tiktok_domains = {
            "tiktok.com",
            "www.tiktok.com",
            "m.tiktok.com",
            "vm.tiktok.com",
            "vt.tiktok.com",
        }

        if (
            hostname in tiktok_domains
            or hostname.endswith(".tiktok.com")
        ):

            return "tiktok"

        return None

    except Exception:

        return None


# ============================================================
# HOME
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
        },
    )


# ============================================================
# TIKTOK
# ============================================================

@app.post("/api/download")
@limiter.limit("10/minute")
def download_video(
    request: Request,
    data: DownloadRequest,
):

    platform = get_platform(data.url)

    if platform != "tiktok":

        raise HTTPException(
            status_code=400,
            detail="Please enter a valid TikTok URL.",
        )

    try:

        result = get_video(
            data.url
        )

        if not result:

            raise HTTPException(
                status_code=404,
                detail="Video could not be found.",
            )

        # ====================================================
        # NORMAL VIDEO
        # ====================================================

        video_token = create_download_token(
            result["video"],
            "video",
            "tiktok_video.mp4",
        )

        # ====================================================
        # HD VIDEO
        # ====================================================

        hd_token = None

        if result.get("hd_video"):

            hd_token = create_download_token(
                result["hd_video"],
                "video",
                "tiktok_hd.mp4",
            )

        # ====================================================
        # MUSIC
        # ====================================================

        music_token = None

        if result.get("music"):

            music_token = create_download_token(
                result["music"],
                "music",
                "tiktok_audio.mp3",
            )

        return {
            "platform": "tiktok",
            "title": result.get("title"),
            "duration": result.get("duration"),
            "cover": result.get("cover"),
            "author": result.get("author"),
            "downloads": {
                "video": (
                    f"/api/download-file/{video_token}"
                ),
                "hd_video": (
                    f"/api/download-file/{hd_token}"
                    if hd_token
                    else None
                ),
                "music": (
                    f"/api/download-file/{music_token}"
                    if music_token
                    else None
                ),
            },
        }

    except HTTPException:

        raise

    except Exception:

        logger.exception(
            "TikTok processing failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to process TikTok video.",
        )


# ============================================================
# INSTAGRAM
# ============================================================

@app.post("/api/instagram/download")
@limiter.limit("10/minute")
def instagram_download(
    request: Request,
    data: DownloadRequest,
):

    # ========================================================
    # VALIDATE INSTAGRAM URL
    # ========================================================

    if not is_instagram_url(data.url):

        raise HTTPException(
            status_code=400,
            detail=(
                "Enter a valid public Instagram "
                "Reel or video URL."
            ),
        )

    try:

        # ====================================================
        # SOCIALKIT
        # ====================================================

        result = get_instagram_video(
            data.url
        )

        shortcode = (
            result.get("shortcode")
            or "video"
        )

        filename = (
            f"instagram_{shortcode}.mp4"
        )

        # ====================================================
        # CREATE SHORT-LIVED TOKEN
        # ====================================================

        video_token = create_download_token(
            result["video_url"],
            "instagram_video",
            filename,
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "success": True,
            "platform": "instagram",
            "filename": filename,
            "thumbnail": result.get(
                "thumbnail"
            ),
            "author": result.get(
                "author"
            ),
            "description": result.get(
                "description"
            ),
            "duration": result.get(
                "duration"
            ),
            "download_url": (
                f"/api/download-file/{video_token}"
            ),
        }

    except InstagramError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:

        logger.exception(
            "Instagram processing failed"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process Instagram video."
            ),
        )


# ============================================================
# CDN HOST VALIDATION
# ============================================================

def is_allowed_download_host(
    hostname: str,
) -> bool:

    hostname = hostname.lower()

    allowed_hosts = (
        # TikTok
        "tiktokcdn.com",
        "tiktokcdn-us.com",
        "tiktokcdn-eu.com",
        "tokcdn.com",

        # Instagram
        "cdninstagram.com",
        "fbcdn.net",
    )

    return any(
        hostname == host
        or hostname.endswith(
            "." + host
        )
        for host in allowed_hosts
    )


# ============================================================
# SAFE FILE DOWNLOAD
# ============================================================

@app.get(
    "/api/download-file/{token}"
)
@limiter.limit("20/minute")
def download_file(
    request: Request,
    token: str,
):

    # ========================================================
    # VERIFY TOKEN
    # ========================================================

    data = verify_download_token(
        token,
        DOWNLOAD_TOKEN_MAX_AGE,
    )

    if not data:

        raise HTTPException(
            status_code=403,
            detail=(
                "Invalid or expired "
                "download token."
            ),
        )

    # ========================================================
    # GET URL
    # ========================================================

    url = data.get("url")

    file_type = data.get(
        "type",
        "video",
    )

    filename = data.get(
        "filename",
        "video.mp4",
    )

    if not url:

        raise HTTPException(
            status_code=400,
            detail="Invalid download token.",
        )

    # ========================================================
    # VALIDATE SOURCE URL
    # ========================================================

    parsed = urlparse(url)

    if parsed.scheme != "https":

        raise HTTPException(
            status_code=403,
            detail="Invalid download source.",
        )

    hostname = parsed.hostname

    if not hostname:

        raise HTTPException(
            status_code=403,
            detail="Invalid download source.",
        )

    if not is_allowed_download_host(
        hostname
    ):

        logger.warning(
            "Blocked download host: %s",
            hostname,
        )

        raise HTTPException(
            status_code=403,
            detail="Download source not allowed.",
        )

    # ========================================================
    # DOWNLOAD
    # ========================================================

    response = None

    try:

        response = requests.get(
            url,
            stream=True,
            timeout=(
                10,
                60,
            ),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/151.0 Safari/537.36"
                ),
                "Accept": (
                    "video/mp4,video/*;q=0.9,*/*;q=0.8"
                ),
            },
        )

        response.raise_for_status()

        # ====================================================
        # CONTENT LENGTH CHECK
        # ====================================================

        content_length = (
            response.headers.get(
                "content-length"
            )
        )

        if content_length:

            try:

                content_length = int(
                    content_length
                )

            except ValueError:

                content_length = None

        if (
            content_length
            and content_length
            > MAX_DOWNLOAD_SIZE
        ):

            response.close()

            raise HTTPException(
                status_code=413,
                detail="Video is too large.",
            )

        # ====================================================
        # STREAM
        # ====================================================

        def generate():

            total = 0

            try:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if not chunk:
                        continue

                    total += len(chunk)

                    if total > MAX_DOWNLOAD_SIZE:

                        raise RuntimeError(
                            "File exceeds maximum size."
                        )

                    yield chunk

            finally:

                response.close()

        # ====================================================
        # FILE TYPE
        # ====================================================

        if file_type == "music":

            media_type = "audio/mpeg"

        else:

            media_type = "video/mp4"

        # ====================================================
        # RESPONSE
        # ====================================================

        return StreamingResponse(
            generate(),
            media_type=media_type,
            headers={
                "Content-Disposition": (
                    f'attachment; '
                    f'filename="{filename}"'
                ),
                "X-Content-Type-Options": (
                    "nosniff"
                ),
                "Cache-Control": (
                    "no-store"
                ),
            },
        )

    except HTTPException:

        raise

    except requests.RequestException:

        if response:

            response.close()

        logger.exception(
            "CDN download failed"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to download video."
            ),
        )

    except Exception:

        if response:

            response.close()

        logger.exception(
            "Unexpected download error"
        )

        raise HTTPException(
            status_code=500,
            detail="Download failed.",
        )
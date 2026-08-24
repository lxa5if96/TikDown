import yt_dlp


class InstagramError(Exception):
    pass


# ============================================================
# INSTAGRAM URL VALIDATION
# ============================================================

def is_instagram_url(url: str) -> bool:

    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        hostname = (parsed.hostname or "").lower()

        allowed_hosts = {
            "instagram.com",
            "www.instagram.com",
        }

        if hostname not in allowed_hosts:
            return False

        allowed_paths = (
            "/reel/",
            "/reels/",
            "/p/",
            "/tv/",
        )

        return parsed.path.startswith(allowed_paths)

    except Exception:
        return False


# ============================================================
# GET INSTAGRAM VIDEO
# ============================================================

def get_instagram_video(url: str) -> dict:

    if not is_instagram_url(url):
        raise InstagramError(
            "Invalid Instagram URL."
        )

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,

        # Prefer one stream containing BOTH
        # video and audio.
        "format": (
            "best[acodec!=none][vcodec!=none]"
            "/best[ext=mp4]"
            "/best"
        ),
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False,
            )

        if not info:
            raise InstagramError(
                "Instagram did not return video information."
            )

        # ====================================================
        # HANDLE PLAYLIST
        # ====================================================

        if info.get("_type") == "playlist":

            entries = info.get("entries") or []

            if not entries:
                raise InstagramError(
                    "No media found in this Instagram post."
                )

            info = entries[0]

        # ====================================================
        # GET SELECTED FORMAT
        # ====================================================

        video_url = info.get("url")

        if not video_url:

            raise InstagramError(
                "Instagram did not provide a downloadable video."
            )

        # ====================================================
        # VERIFY AUDIO + VIDEO
        # ====================================================

        if (
            info.get("vcodec") == "none"
            or info.get("acodec") == "none"
        ):

            raise InstagramError(
                "Instagram returned separate media streams "
                "instead of a combined video."
            )

        # ====================================================
        # RETURN
        # ====================================================

        return {
            "video_url": video_url,

            "thumbnail": info.get(
                "thumbnail"
            ),

            "author": (
                info.get("uploader")
                or info.get("channel")
                or info.get("creator")
            ),

            "description": info.get(
                "description"
            ),

            "duration": info.get(
                "duration"
            ),

            "shortcode": (
                info.get("id")
                or "video"
            ),

            "content_type": "video",
        }

    except yt_dlp.utils.DownloadError as exc:

        raise InstagramError(
            f"Instagram extraction failed: {exc}"
        ) from exc

    except InstagramError:

        raise

    except Exception as exc:

        raise InstagramError(
            f"Instagram extraction failed: {exc}"
        ) from exc
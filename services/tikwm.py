import requests

TIKWM_API = "https://www.tikwm.com/api/"


def get_video(url: str):

    response = requests.post(
        TIKWM_API,
        data={"url": url},
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if result.get("code") != 0:
        raise Exception(
            result.get("msg", "TikWM request failed")
        )

    video = result["data"]

    author = video.get("author") or {}

    return {
        "title": video.get("title"),
        "duration": video.get("duration"),
        "cover": video.get("cover"),

        "video": video.get("play"),

        "hd_video": (
            video.get("hdplay")
            or video.get("play")
        ),

        "watermarked_video": video.get("wmplay"),

        "music": video.get("music"),

        "author": {
            "username": author.get("unique_id"),
            "nickname": author.get("nickname"),
            "avatar": author.get("avatar")
        }
    }
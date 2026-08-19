"""
اسکرپینگ تعداد ویوی یوتیوب و موسیقی یوتیوب از طریق صفحه عمومی ویدیو (بدون نیاز به API).
نکته: یوتیوب گاهی ساختار HTML را تغییر می‌دهد، اگر در آینده کار نکرد
باید الگوی regex را به‌روزرسانی کنید یا از YouTube Data API استفاده کنید.
"""
import os
import re
import time
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}


def _build_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=None,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def normalize_youtube_url(url: str) -> str | None:
    if not url:
        return None

    value = str(url).strip()
    if not value:
        return None

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return f"https://www.youtube.com/watch?v={value}"

    parsed = urlparse(value)
    host = (parsed.netloc or "").lower()
    if host.endswith("youtu.be"):
        video_id = parsed.path.lstrip("/").split("/")[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

    if host in {"www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"}:
        path = parsed.path.lower()
        if path.startswith("/watch"):
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        if path.startswith("/shorts/"):
            video_id = path.split("/shorts/")[-1].split("/")[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        if path.startswith("/live/"):
            video_id = path.split("/live/")[-1].split("/")[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        if path.startswith("/embed/"):
            video_id = path.split("/embed/")[-1].split("/")[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"

    return value


def extract_youtube_view_count(html: str) -> int | None:
    if not html:
        return None

    patterns = [
        r'"viewCount":"(\d+)"',
        r'"viewCount":(\d+)',
        r'"estimatedViewCount":"([\d,]+)"',
        r'"approxViewCount":"([\d,]+)"',
        r'"viewCountText":\{"simpleText":"([\d,]+)\\s+views"',
        r'"shortViewCountText":\{"simpleText":"([\d,]+)\\s+views"',
        r'([\d,]+)\s+views',
        r'([\d,]+)\s+watching',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            try:
                return int(value)
            except ValueError:
                continue

    return None


def get_youtube_views(url: str) -> int | None:
    """دریافت تعداد ویوهای YouTube"""
    normalized_url = normalize_youtube_url(url)
    if not normalized_url:
        return None

    video_id_match = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", normalized_url)
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if api_key and video_id_match:
        try:
            api_resp = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "statistics", "id": video_id_match.group(1), "key": api_key},
                timeout=(10, 25),
            )
            api_resp.raise_for_status()
            payload = api_resp.json()
            items = payload.get("items") or []
            if items:
                stats = items[0].get("statistics") or {}
                if stats.get("viewCount") is not None:
                    return int(stats["viewCount"])
        except Exception as exc:
            print(f"[youtube_scraper] youtube api failed for {normalized_url}: {exc}")

    session = _build_session()
    last_error = None

    for attempt in range(3):
        try:
            resp = session.get(normalized_url, headers=HEADERS, timeout=(10, 25))
            resp.raise_for_status()
            return extract_youtube_view_count(resp.text)
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))
                continue
            break

    print(f"[youtube_scraper] error fetching {normalized_url}: {last_error}")
    return None


def get_youtube_music_views(url: str) -> int | None:
    """دریافت تعداد پخش‌های موسیقی یوتیوب (music.youtube.com)"""
    if not url:
        return None

    session = _build_session()
    last_error = None

    for attempt in range(3):
        try:
            resp = session.get(url, headers=HEADERS, timeout=(10, 25))
            resp.raise_for_status()
            html = resp.text

            patterns = [
                r'"listenCount":"(\d+)"',
                r'"playCount":"(\d+)"',
                r'"viewCount":"(\d+)"',
                r'([\d,]+)\s+(?:plays|listens|views)',
            ]

            for pattern in patterns:
                match = re.search(pattern, html, flags=re.IGNORECASE)
                if match:
                    return int(match.group(1).replace(",", ""))

            return None
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))
                continue
            break

    print(f"[youtube_scraper] error fetching music.youtube {url}: {last_error}")
    return None

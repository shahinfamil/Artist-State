"""
اسکرپینگ تعداد پلی (play count) ساندکلود از صفحه عمومی ترک.
ساندکلود اطلاعات play count را داخل تگ JSON-LD یا meta description قرار می‌دهد.
"""
import re
import json
import time
import requests
from bs4 import BeautifulSoup
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


def _extract_play_count_from_html(html: str):
    patterns = [
        r'"playback_count":\s*(\d+)',
        r'"userInteractionCount":\s*(\d+)',
        r'"play_count":\s*(\d+)',
        r'"plays_count":\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def get_soundcloud_plays(url: str) -> int | None:
    if not url:
        return None

    session = _build_session()
    last_error = None

    for attempt in range(3):
        try:
            resp = session.get(url, headers=HEADERS, timeout=(10, 25))
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and "interactionStatistic" in data:
                        stats = data["interactionStatistic"]
                        if isinstance(stats, list):
                            for s in stats:
                                if isinstance(s, dict) and "userInteractionCount" in s:
                                    return int(s["userInteractionCount"])
                        elif isinstance(stats, dict) and "userInteractionCount" in stats:
                            return int(stats["userInteractionCount"])
                except Exception:
                    continue

            count = _extract_play_count_from_html(html)
            if count is not None:
                return count

            if "soundcloud.com" in url:
                for meta in soup.find_all("meta"):
                    content = meta.attrs.get("content", "")
                    if not content:
                        continue
                    match = re.search(r"(\d[\d,]*)\s+plays?", content, flags=re.IGNORECASE)
                    if match:
                        return int(match.group(1).replace(",", ""))

            return None
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))
                continue
            break

    print(f"[soundcloud_scraper] error fetching {url}: {last_error}")
    return None

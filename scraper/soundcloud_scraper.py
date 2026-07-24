"""
اسکرپینگ تعداد پلی (play count) ساندکلود از صفحه عمومی ترک.
ساندکلود اطلاعات play count را داخل تگ JSON-LD یا meta description قرار می‌دهد.
"""
import re
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def get_soundcloud_plays(url: str) -> int | None:
    if not url:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # روش ۱: تگ JSON-LD که شامل اطلاعات ساختاریافته است
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "interactionStatistic" in data:
                    stats = data["interactionStatistic"]
                    if isinstance(stats, list):
                        for s in stats:
                            if "userInteractionCount" in s:
                                return int(s["userInteractionCount"])
                    elif isinstance(stats, dict) and "userInteractionCount" in stats:
                        return int(stats["userInteractionCount"])
            except Exception:
                continue

        # روش ۲: جستجوی الگوی playback_count داخل HTML خام (داده‌های هیدراته‌شده)
        match = re.search(r'"playback_count":(\d+)', html)
        if match:
            return int(match.group(1))

        return None
    except Exception as e:
        print(f"[soundcloud_scraper] error fetching {url}: {e}")
        return None

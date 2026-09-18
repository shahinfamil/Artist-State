"""
اسکرپینگ تعداد ویوی یوتیوب و موسیقی یوتیوب از طریق صفحه عمومی ویدیو (بدون نیاز به API).
نکته: یوتیوب گاهی ساختار HTML را تغییر می‌دهد، اگر در آینده کار نکرد
باید الگوی regex را به‌روزرسانی کنید یا از YouTube Data API استفاده کنید.
"""
import os
import re
import time
import random
import threading
from urllib.parse import parse_qs, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import tempfile
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}

# small list of common user agents to rotate
USER_AGENTS = [
    HEADERS["User-Agent"],
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
]

# simple in-memory per-host rate limiting to avoid bursts
_last_request_time: dict[str, float] = {}
_last_request_lock = threading.Lock()
RATE_LIMIT_SECONDS = float(os.environ.get("YOUTUBE_RATE_LIMIT_SECONDS", "3.5"))
MAX_ATTEMPTS = int(os.environ.get("YOUTUBE_MAX_ATTEMPTS", "6"))


def _build_session():
    session = requests.Session()
    retry = Retry(
        total=int(os.environ.get("YOUTUBE_RETRY_TOTAL", "5")),
        connect=3,
        read=3,
        backoff_factor=float(os.environ.get("YOUTUBE_RETRY_BACKOFF", "1.2")),
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _get_redis_client():
    try:
        import redis

        url = os.environ.get("REDIS_URL")
        if url:
            return redis.from_url(url)
        return redis.Redis()
    except Exception:
        return None


_redis_client = _get_redis_client()


def _get_api_key() -> str | None:
    """Return YouTube API key from environment or instance/youtube_api_key.txt fallback."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if key:
        return key
    # try instance folder sibling to project root
    try:
        here = os.path.dirname(__file__)
        # project root is one level up from scraper/
        candidate = os.path.abspath(os.path.join(here, "..", "instance", "youtube_api_key.txt"))
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                val = fh.read().strip()
                if val:
                    return val
    except Exception:
        pass
    return None


def _yt_dlp_get_view_count(url: str) -> int | None:
    """Try to get view count using yt-dlp as a fallback.

    Returns int view count or None if not available or yt-dlp not installed.
    """
    try:
        from yt_dlp import YoutubeDL
    except Exception:
        return None

    try:
        opts = {
            'quiet': True,
            'skip_download': True,
            'nocheckcertificate': True,
        }
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            # primary key
            vc = info.get('view_count')
            if vc is not None:
                return int(vc)
            # sometimes available under 'formats' or 'entries' for playlists
            return None
    except Exception:
        return None

# basic in-process metrics
_metrics = {
    "requests_total": 0,
    "api_calls": 0,
    "cache_hits": 0,
    "scrapes": 0,
    "blocked": 0,
    "http_429": 0,
}

# optional Prometheus export
_prometheus_enabled = False
try:
    from prometheus_client import Counter, start_http_server

    prom_port = os.environ.get("PROMETHEUS_METRICS_PORT")
    if prom_port:
        REQUESTS_CNT = Counter("yt_requests_total", "Total youtube scraper requests")
        API_CNT = Counter("yt_api_calls_total", "YouTube API calls")
        CACHE_HITS = Counter("yt_cache_hits_total", "Cache hits for youtube views")
        SCRAPES = Counter("yt_scrapes_total", "Scraped page view counts")
        BLOCKED = Counter("yt_blocked_total", "Blocked responses detected")
        HTTP_429 = Counter("yt_http_429_total", "HTTP 429 responses")
        start_http_server(int(prom_port))
        _prometheus_enabled = True
except Exception:
    _prometheus_enabled = False


def _cache_get(key: str):
    # Try Redis first
    try:
        if _redis_client:
            val = _redis_client.get(key)
            if val is None:
                return None
            return json.loads(val)
    except Exception:
        pass

    # Fallback to file cache per-key
    try:
        fn = os.path.join(tempfile.gettempdir(), f"yt_cache_{key}.json")
        if not os.path.exists(fn):
            return None
        with open(fn, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        expires = datetime.fromisoformat(payload.get("expires"))
        if datetime.utcnow() > expires:
            try:
                os.remove(fn)
            except Exception:
                pass
            return None
        return payload.get("value")
    except Exception:
        return None


def _cache_set(key: str, value, ttl: int = 600):
    # Try Redis first
    try:
        if _redis_client:
            _redis_client.set(key, json.dumps(value), ex=ttl)
            return
    except Exception:
        pass

    # Fallback to file cache
    try:
        fn = os.path.join(tempfile.gettempdir(), f"yt_cache_{key}.json")
        payload = {"expires": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat(), "value": value}
        with open(fn, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
    except Exception:
        pass


def _throttle_for_host(host: str) -> None:
    now = time.time()
    with _last_request_lock:
        last = _last_request_time.get(host, 0)
        wait = RATE_LIMIT_SECONDS - (now - last)
        if wait > 0:
            time.sleep(wait + random.uniform(0.0, 1.2))
        _last_request_time[host] = time.time()


def _build_headers(url: str | None = None) -> dict:
    h = HEADERS.copy()
    h["User-Agent"] = random.choice(USER_AGENTS)
    if url:
        h.setdefault("Referer", "https://www.youtube.com/")
    # add a couple of extra headers that look more browser-like
    h.setdefault("DNT", "1")
    h.setdefault("Sec-Fetch-Site", "same-origin")
    return h


def _choose_proxy() -> dict | None:
    """Return a proxies dict for requests or None if no proxies configured.

    Configuration options (in order):
    - Environment variable `YOUTUBE_PROXIES`: comma-separated proxy URLs
      (e.g. http://user:pass@host:port or http://host:port).
    - Environment variable `YOUTUBE_PROXIES_FILE`: path to a file with one
      proxy per line.
    """
    raw = os.environ.get("YOUTUBE_PROXIES")
    proxies_list = []
    if raw:
        proxies_list = [p.strip() for p in raw.split(",") if p.strip()]
    else:
        file_path = os.environ.get("YOUTUBE_PROXIES_FILE")
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    for ln in fh:
                        ln = ln.strip()
                        if ln:
                            proxies_list.append(ln)
            except Exception:
                proxies_list = []

    if not proxies_list:
        return None

    proxy = random.choice(proxies_list)
    # ensure scheme for requests proxy dict
    if not proxy.startswith("http://") and not proxy.startswith("https://"):
        proxy = "http://" + proxy

    return {"http": proxy, "https": proxy}


def get_youtube_scraper_metrics() -> dict:
    """Return a snapshot of in-process metrics."""
    out = dict(_metrics)
    if _prometheus_enabled:
        out["prometheus"] = True
    return out


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
        r'"viewCountText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"\}',
        r'"viewCountText"\s*:\s*\{"accessibility"\s*:\s*\{"accessibilityData"\s*:\s*\{"label"\s*:\s*"([^"]+)"\}\}\}',
        r'"shortViewCountText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"\}',
        r'"shortViewCountText"\s*:\s*\{"accessibility"\s*:\s*\{"accessibilityData"\s*:\s*\{"label"\s*:\s*"([^"]+)"\}\}\}',
        r'([\d,]+)\s+(?:views|watching)',
        r'"label"\s*:\s*"([^"\n]*?[\d,]+[^"\n]*?(?:views|watching))"',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            value = match.group(1)
            digits = re.search(r"[\d][\d,\.]*", value)
            if not digits:
                continue
            value = digits.group(0).replace(",", "")
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
    api_key = _get_api_key()
    cache_ttl = int(os.environ.get("YOUTUBE_CACHE_TTL", "600"))

    # use video-id based cache when possible
    vid = video_id_match.group(1) if video_id_match else None
    cache_key = f"yt:views:{vid}" if vid else None
    if cache_key:
        cached = _cache_get(cache_key)
        if cached is not None:
            _metrics["cache_hits"] += 1
            if _prometheus_enabled:
                CACHE_HITS.inc()
            return int(cached)
    if api_key and video_id_match:
        try:
            _metrics["api_calls"] += 1
            if _prometheus_enabled:
                API_CNT.inc()
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
                    val = int(stats["viewCount"])
                    if cache_key:
                        _cache_set(cache_key, val, ttl=cache_ttl)
                    return val
        except Exception as exc:
            print(f"[youtube_scraper] youtube api failed for {normalized_url}: {exc}")

    session = _build_session()
    last_error = None

    parsed = urlparse(normalized_url)
    host = parsed.netloc.lower()

    for attempt in range(5):
        try:
            _metrics["requests_total"] += 1
            _throttle_for_host(host)
            headers = _build_headers(normalized_url)
            proxies = _choose_proxy()
            if proxies:
                # log proxy selection to stdout for debugging
                print(f"[youtube_scraper] using proxy {proxies.get('https')}")
            resp = session.get(normalized_url, headers=headers, timeout=(10, 25), proxies=proxies)

            # detect Google's "sorry" interstitial (captcha / rate-limit block)
            final_url = getattr(resp, "url", "") or ""
            text = (resp.text or "").lower()
            if "sorry/index" in final_url or "our systems have detected unusual traffic" in text or "unusual traffic" in text:
                last_error = Exception("blocked by google sorry page")
                # back off harder if blocked
                _metrics["blocked"] += 1
                if _prometheus_enabled:
                    BLOCKED.inc()
                sleep_for = min(10 * (attempt + 1), 60) + random.uniform(0, 5)
                time.sleep(sleep_for)
                continue

            # raise for non-2xx statuses to let retry logic handle it
            resp.raise_for_status()
            res = extract_youtube_view_count(resp.text)
            if res is not None and cache_key:
                _cache_set(cache_key, int(res), ttl=cache_ttl)
            return res
        except requests.exceptions.HTTPError as exc:
            last_error = exc
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                _metrics["http_429"] += 1
                if _prometheus_enabled:
                    HTTP_429.inc()
                sleep_for = min((2 ** attempt) + random.uniform(0.5, 2.5), 120)
                time.sleep(sleep_for)
                continue
            if attempt < 4:
                time.sleep(1.2 * (attempt + 1))
                continue
            break
        except Exception as exc:
            last_error = exc
            if attempt < 4:
                time.sleep((2 ** attempt) * 0.8 + random.uniform(0, 1.2))
                continue
            break

    print(f"[youtube_scraper] error fetching {normalized_url}: {last_error}")
    # final fallback: try yt-dlp if available (often avoids HTML parsing issues)
    try:
        val = _yt_dlp_get_view_count(normalized_url)
        if val is not None:
            if cache_key:
                _cache_set(cache_key, int(val), ttl=cache_ttl)
            _metrics["scrapes"] += 1
            if _prometheus_enabled:
                SCRAPES.inc()
            return int(val)
    except Exception:
        pass
    return None


def get_youtube_music_views(url: str) -> int | None:
    """دریافت تعداد پخش‌های موسیقی یوتیوب (music.youtube.com)"""
    if not url:
        return None
    session = _build_session()
    last_error = None

    cache_ttl = int(os.environ.get("YOUTUBE_CACHE_TTL", "600"))
    # use url-based cache key
    safe_key = re.sub(r"[^A-Za-z0-9]", "_", url)[:200]
    cache_key = f"yt:music:{safe_key}"
    cached = _cache_get(cache_key)
    if cached is not None:
        try:
            _metrics["cache_hits"] += 1
            if _prometheus_enabled:
                CACHE_HITS.inc()
            return int(cached)
        except Exception:
            pass

    parsed = urlparse(url)
    host = parsed.netloc.lower()

    for attempt in range(5):
        try:
            _metrics["requests_total"] += 1
            _throttle_for_host(host)
            headers = _build_headers(url)
            proxies = _choose_proxy()
            if proxies:
                print(f"[youtube_scraper] using proxy {proxies.get('https')}")
            resp = session.get(url, headers=headers, timeout=(10, 25), proxies=proxies)

            final_url = getattr(resp, "url", "") or ""
            text = (resp.text or "").lower()
            if "sorry/index" in final_url or "our systems have detected unusual traffic" in text:
                last_error = Exception("blocked by google sorry page")
                _metrics["blocked"] += 1
                if _prometheus_enabled:
                    BLOCKED.inc()
                time.sleep(min(10 * (attempt + 1), 60) + random.uniform(0, 5))
                continue

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
                    val = int(match.group(1).replace(",", ""))
                    _cache_set(cache_key, val, ttl=cache_ttl)
                    _metrics["scrapes"] += 1
                    if _prometheus_enabled:
                        SCRAPES.inc()
                    return val

            return None
        except requests.exceptions.HTTPError as exc:
            last_error = exc
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                time.sleep((2 ** attempt) + random.uniform(0.5, 2.0))
                continue
            if attempt < 4:
                time.sleep(1.2 * (attempt + 1))
                continue
            break
        except Exception as exc:
            last_error = exc
            if attempt < 4:
                time.sleep((2 ** attempt) * 0.8 + random.uniform(0, 1.2))
                continue
            break

    print(f"[youtube_scraper] error fetching music.youtube {url}: {last_error}")
    # try yt-dlp as a last resort for music pages
    try:
        val = _yt_dlp_get_view_count(url)
        if val is not None:
            _cache_set(cache_key, int(val), ttl=cache_ttl)
            _metrics["scrapes"] += 1
            if _prometheus_enabled:
                SCRAPES.inc()
            return int(val)
    except Exception:
        pass
    return None


def get_youtube_views_batch(urls: list) -> dict:
    """Fetch view counts for a list of youtube URLs (or IDs).

    Strategy:
    - normalize URLs and extract video IDs
    - for video IDs, call YouTube Data API in chunks (up to 50 ids per request) when `YOUTUBE_API_KEY` is set
    - set cache for API results
    - for remaining URLs, fallback to parallel scraping using ThreadPoolExecutor

    Returns a mapping {url: int|None}.
    """
    if not urls:
        return {}

    api_key = _get_api_key()
    cache_ttl = int(os.environ.get("YOUTUBE_CACHE_TTL", "600"))
    results: dict = {}
    # normalize and map
    normalized_map = {}
    vid_to_urls = {}
    to_scrape = []
    for url in urls:
        norm = normalize_youtube_url(url) or url
        normalized_map[url] = norm
        m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", norm)
        if m:
            vid = m.group(1)
            vid_to_urls.setdefault(vid, []).append(url)
        else:
            to_scrape.append(url)

    # try cache and API for IDs
    ids = list(vid_to_urls.keys())
    ids_to_scrape = []
    if ids:
        # check cache first
        ids_missing = []
        for vid in ids:
            cache_key = f"yt:views:{vid}"
            cached = _cache_get(cache_key)
            if cached is not None:
                _metrics["cache_hits"] += 1
                if _prometheus_enabled:
                    CACHE_HITS.inc()
                for orig in vid_to_urls.get(vid, []):
                    results[orig] = int(cached)
            else:
                ids_missing.append(vid)

        # call YouTube API in chunks for missing ids
        if api_key and ids_missing:
            _metrics["api_calls"] += 1
            if _prometheus_enabled:
                API_CNT.inc()
            chunk_size = 50
            for i in range(0, len(ids_missing), chunk_size):
                chunk = ids_missing[i : i + chunk_size]
                try:
                    resp = requests.get(
                        "https://www.googleapis.com/youtube/v3/videos",
                        params={"part": "statistics", "id": ",".join(chunk), "key": api_key},
                        timeout=(10, 30),
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    items = payload.get("items") or []
                    seen = set()
                    for item in items:
                        vid = item.get("id")
                        seen.add(vid)
                        stats = item.get("statistics") or {}
                        val = int(stats.get("viewCount")) if stats.get("viewCount") is not None else None
                        if val is not None:
                            cache_key = f"yt:views:{vid}"
                            _cache_set(cache_key, val, ttl=cache_ttl)
                            for orig in vid_to_urls.get(vid, []):
                                results[orig] = int(val)
                    # any ids in chunk not returned -> mark for scraping
                    for vid in chunk:
                        if vid not in seen:
                            for orig in vid_to_urls.get(vid, []):
                                ids_to_scrape.append(orig)
                except Exception:
                    # on API failure, mark entire chunk for scraping
                    for vid in chunk:
                        for orig in vid_to_urls.get(vid, []):
                            ids_to_scrape.append(orig)
        else:
            # no api key: schedule all ids for scraping
            for vid in ids:
                for orig in vid_to_urls.get(vid, []):
                    ids_to_scrape.append(orig)

    # combine all urls that still need scraping
    scrape_candidates = list(set(to_scrape + ids_to_scrape))

    # parallel scraping fallback
    if scrape_candidates:
        session = _build_session()
        max_workers = int(os.environ.get("YOUTUBE_MAX_WORKERS", "8"))
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _scrape_one(u):
            try:
                val = get_youtube_views(u)
                return u, val
            except Exception:
                return u, None

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_scrape_one, u): u for u in scrape_candidates}
            for fut in as_completed(futures):
                u, val = fut.result()
                results[u] = val

    # ensure all input urls present in results (fill None if missing)
    for url in urls:
        if url not in results:
            # maybe normalized mapping resolved to cached API earlier
            norm = normalized_map.get(url)
            # try to find by vid mapping
            m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", norm or "")
            if m:
                vid = m.group(1)
                cache_key = f"yt:views:{vid}"
                cached = _cache_get(cache_key)
                if cached is not None:
                    results[url] = int(cached)
                    continue
            results[url] = None

    return results

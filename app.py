import os
import random
import re
import secrets
import sys
import threading
import time
import unicodedata
import json
import requests
from http.cookiejar import MozillaCookieJar
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from flask import Flask, render_template, abort, jsonify, request, session, redirect, url_for
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import inspect, text

from models import db, Artist, ArtistWikipediaData, Album, Track, ViewStat, User
from spotify_scraper import SpotifyClient
from scraper import get_youtube_views, get_soundcloud_plays
from werkzeug.security import generate_password_hash, check_password_hash
from admin import group_albums_for_display

SOCIAL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

INSTAGRAM_RATE_LIMIT_UNTIL = None
INSTAGRAM_REQUEST_LOCK = threading.Lock()
INSTAGRAM_LAST_REQUEST_AT = None
INSTAGRAM_USE_INSTALOADER = True


def clear_instagram_rate_limit():
    global INSTAGRAM_RATE_LIMIT_UNTIL
    INSTAGRAM_RATE_LIMIT_UNTIL = None


def mark_instagram_rate_limited(seconds: int):
    global INSTAGRAM_RATE_LIMIT_UNTIL
    if seconds <= 0:
        clear_instagram_rate_limit()
        return
    INSTAGRAM_RATE_LIMIT_UNTIL = datetime.utcnow() + timedelta(seconds=seconds)


def should_skip_instagram_request():
    global INSTAGRAM_RATE_LIMIT_UNTIL
    if not INSTAGRAM_RATE_LIMIT_UNTIL:
        return False, None
    if datetime.utcnow() >= INSTAGRAM_RATE_LIMIT_UNTIL:
        clear_instagram_rate_limit()
        return False, None
    return True, (INSTAGRAM_RATE_LIMIT_UNTIL - datetime.utcnow()).total_seconds()


def wait_for_instagram_cooldown():
    global INSTAGRAM_LAST_REQUEST_AT
    if INSTAGRAM_LAST_REQUEST_AT is None:
        INSTAGRAM_LAST_REQUEST_AT = datetime.utcnow()
        return
    elapsed = (datetime.utcnow() - INSTAGRAM_LAST_REQUEST_AT).total_seconds()
    if elapsed < 45:
        time.sleep(45 - elapsed)
    INSTAGRAM_LAST_REQUEST_AT = datetime.utcnow()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


def build_request_headers(extra_headers=None):
    headers = dict(SOCIAL_HEADERS)
    headers["User-Agent"] = random.choice(USER_AGENTS)
    headers["Accept-Language"] = random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8", "en-US,en;q=0.8"])
    if extra_headers:
        headers.update(extra_headers)
    return headers


def load_instagram_session_cookies():
    cookie_text = os.environ.get("INSTAGRAM_SESSION_COOKIES", "").strip()
    if cookie_text:
        cookies = {}
        for part in cookie_text.split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip()
            if key:
                cookies[key] = value.strip()
        if cookies:
            return cookies

    env_payload = os.environ.get("INSTAGRAM_COOKIE_JSON", "").strip()
    if env_payload:
        try:
            payload = json.loads(env_payload)
            if isinstance(payload, list):
                cookies = {}
                for item in payload:
                    if isinstance(item, dict) and item.get("name"):
                        cookies[item["name"]] = item.get("value", "")
                if cookies:
                    return cookies
        except Exception:
            pass

    cookie_file = os.environ.get("INSTAGRAM_COOKIE_FILE", "").strip()
    if not cookie_file:
        fallback_paths = [
            os.path.join(os.path.dirname(__file__), "instagram_cookies.json"),
            os.path.join(os.path.dirname(__file__), "cookies", "instagram_cookies.json"),
            os.path.join(os.path.dirname(__file__), "static", "instagram_cookies.json"),
        ]
        for candidate in fallback_paths:
            if os.path.exists(candidate):
                cookie_file = candidate
                break

    if cookie_file and os.path.exists(cookie_file):
        try:
            with open(cookie_file, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, list):
                cookies = {}
                for item in payload:
                    if isinstance(item, dict) and item.get("name"):
                        cookies[item["name"]] = item.get("value", "")
                if cookies:
                    return cookies
            elif isinstance(payload, dict):
                if payload.get("cookies"):
                    cookies = {}
                    for item in payload["cookies"]:
                        if isinstance(item, dict) and item.get("name"):
                            cookies[item["name"]] = item.get("value", "")
                    if cookies:
                        return cookies
        except Exception:
            pass

        try:
            jar = MozillaCookieJar()
            jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
            return {cookie.name: cookie.value for cookie in jar}
        except Exception:
            return {}

    return {}


def build_instagram_session():
    session = requests.Session()
    cookies = load_instagram_session_cookies()
    if cookies:
        session.cookies.update(cookies)
    session.headers.update(build_request_headers())
    return session


def maybe_sleep_before_request(url):
    if not url:
        return
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return
    if "instagram" in host:
        time.sleep(random.uniform(2.5, 4.5))

def normalize_number_text(value: str) -> str:
    if not value:
        return ""
    value_str = str(value)
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    ascii_digits = "0123456789"
    translation = {ord(p): o for p, o in zip(persian_digits + arabic_digits, ascii_digits * 2)}
    translation.update({ord("٫"): ord("."), ord("٬"): None, ord(","): None})
    normalized = value_str.translate(translation)
    normalized = normalized.replace("\u202f", "").replace("\xa0", "").replace(" ", "").strip()
    return normalized


def parse_number(value):
    if not value:
        return None
    text = normalize_number_text(value).lower()
    if not text:
        return None

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kmb]|thousand|million|billion)?", text)
    if not match:
        digits = re.sub(r"[^0-9]", "", text)
        return int(digits) if digits else None

    number_text = match.group(1)
    suffix = (match.group(2) or "").strip()

    try:
        value_float = float(number_text)
    except ValueError:
        digits = re.sub(r"[^0-9]", "", text)
        return int(digits) if digits else None

    if suffix in {"k", "thousand"}:
        value_float *= 1_000
    elif suffix in {"m", "million"}:
        value_float *= 1_000_000
    elif suffix in {"b", "billion"}:
        value_float *= 1_000_000_000

    return int(value_float)


def extract_json_from_html(html, patterns):
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            raw = match.group(1)
            try:
                return json.loads(raw)
            except ValueError:
                continue
    return None


def deep_get(data, *keys):
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        elif isinstance(data, list) and isinstance(key, int) and 0 <= key < len(data):
            data = data[key]
        else:
            return None
    return data


def requests_get(url: str, **kwargs):
    maybe_sleep_before_request(url)
    headers = kwargs.pop("headers", None)
    if headers is None:
        headers = build_request_headers()
    else:
        headers = build_request_headers(headers)
    kwargs["headers"] = headers
    return requests.get(url, **kwargs)


def requests_post(url: str, **kwargs):
    maybe_sleep_before_request(url)
    headers = kwargs.pop("headers", None)
    if headers is None:
        headers = build_request_headers()
    else:
        headers = build_request_headers(headers)
    kwargs["headers"] = headers
    return requests.post(url, **kwargs)


def extract_followers_count_from_profile_results(profile_results):
    if isinstance(profile_results, dict):
        keys = [
            "followers",
            "followers_count",
            "followersCount",
            "follower_count",
            "followers_text",
            "followersDisplay",
            "following_count",
            "totalFollowers",
            "followers_total",
        ]
        for key in keys:
            value = profile_results.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                parsed = parse_number(value)
                if parsed is not None:
                    return parsed

        for value in profile_results.values():
            if isinstance(value, (dict, list)):
                nested = extract_followers_count_from_profile_results(value)
                if nested is not None:
                    return nested

    elif isinstance(profile_results, list):
        for item in profile_results:
            nested = extract_followers_count_from_profile_results(item)
            if nested is not None:
                return nested

    return None


def extract_instagram_followers_from_payload(payload):
    if not isinstance(payload, dict):
        return None

    user = deep_get(payload, "data", "user")
    if isinstance(user, dict):
        edge_followed_by = user.get("edge_followed_by")
        if isinstance(edge_followed_by, dict):
            count = edge_followed_by.get("count")
            if isinstance(count, int):
                return count

            edges = edge_followed_by.get("edges")
            if isinstance(edges, list):
                followers = []
                for item in edges:
                    if isinstance(item, dict):
                        username = deep_get(item, "node", "username")
                        if username:
                            followers.append(username)
                return followers

    return None


def get_serpapi_instagram_followers(handle: str) -> int | None:
    if not handle:
        return None

    api_key = os.environ.get("SERPAPI_API_KEY", SERPAPI_API_KEY).strip()
    if not api_key:
        return None

    try:
        params = {
            "engine": "instagram_profile",
            "profile_id": handle,
            "api_key": api_key,
            "output": "json",
        }
        resp = requests_get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        results = resp.json()
        if not isinstance(results, dict):
            return None

        profile_results = results.get("profile_results")
        if profile_results is None:
            return None

        return extract_followers_count_from_profile_results(profile_results)
    except Exception:
        return None


def extract_instagram_handle_from_url(url: str) -> str | None:
    if not url:
        return None
    match = re.search(r'instagram\.com/([^/?#\n]+)', url, re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('@')
    return None


def get_instagram_followers(url: str) -> int | None:
    if not url:
        return None

    def extract_handle(u):
        return extract_instagram_handle_from_url(u)

    try:
        with INSTAGRAM_REQUEST_LOCK:
            skip, remaining = should_skip_instagram_request()
            if skip:
                return None

            handle = extract_handle(url)
            if handle:
                return get_serpapi_instagram_followers(handle)

    except Exception:
        pass

    return None


def get_x_followers(url: str) -> int | None:
    if not url:
        return None

    token = os.environ.get("APIFY_API_TOKEN") or APIFY_API_TOKEN
    if not token:
        return None

    try:
        import apify_client
    except ImportError:
        return None

    try:
        client = apify_client.ApifyClient(token)
        run_input = {
            "startUrls": [url],
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }
        run = client.actor("2e3eZoUebkZzrlS6h").call(run_input=run_input)

        dataset_id = None
        if isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
        elif hasattr(run, "to_dict"):
            run_dict = run.to_dict()
            dataset_id = run_dict.get("defaultDatasetId") or run_dict.get("default_dataset_id")
        else:
            dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)

        if not dataset_id:
            return None

        dataset = client.dataset(dataset_id)
        for item in dataset.iterate_items():
            count = extract_followers_count_from_profile_results(item)
            if count is not None:
                return count
    except Exception:
        return None

    return None


def extract_youtube_subscribers_from_json(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {
                "subscriberCountText",
                "subscribersText",
                "subscriberCount",
                "subscriber_count",
                "subscribers",
                "subscriber_count_text",
            }:
                if isinstance(value, dict):
                    if isinstance(value.get("simpleText"), str):
                        parsed = parse_number(value["simpleText"])
                        if parsed is not None:
                            return parsed
                    if isinstance(value.get("label"), str):
                        parsed = parse_number(value["label"])
                        if parsed is not None:
                            return parsed
                    accessibility_label = deep_get(value, "accessibility", "accessibilityData", "label")
                    if isinstance(accessibility_label, str):
                        parsed = parse_number(accessibility_label)
                        if parsed is not None:
                            return parsed
                    runs = value.get("runs")
                    if isinstance(runs, list):
                        for run in runs:
                            if isinstance(run, dict) and isinstance(run.get("text"), str):
                                parsed = parse_number(run["text"])
                                if parsed is not None:
                                    return parsed
                elif isinstance(value, str):
                    parsed = parse_number(value)
                    if parsed is not None:
                        return parsed
            if isinstance(value, (dict, list)):
                nested = extract_youtube_subscribers_from_json(value)
                if nested is not None:
                    return nested
    elif isinstance(data, list):
        for item in data:
            nested = extract_youtube_subscribers_from_json(item)
            if nested is not None:
                return nested
    return None


def parse_youtube_subscriber_count_from_html(html: str) -> int | None:
    if not html:
        return None

    patterns = [
        r'"subscriberCountText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"\}',
        r'"subscriberCountText"\s*:\s*\{"accessibility"\s*:\s*\{"accessibilityData"\s*:\s*\{"label"\s*:\s*"([^"]+)"\}\}\}',
        r'"subscribersText"\s*:\s*"([^"]+)"',
        r'"subscribersText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"\}',
        r'"subscribersText"\s*:\s*\{"accessibility"\s*:\s*\{"accessibilityData"\s*:\s*\{"label"\s*:\s*"([^"]+)"\}\}\}',
        r'"subscriberCount"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"\}',
        r'id="subscriber-count"[^>]*>\s*([^<]+)',
        r'([\d,\.KM]+)\s*subscribers',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return parse_number(match.group(1))

    soup = BeautifulSoup(html, "html.parser")
    subscriber_element = soup.select_one("#subscriber-count")
    if subscriber_element:
        text = subscriber_element.get_text(" ", strip=True)
        if text:
            parsed = parse_number(text)
            if parsed is not None:
                return parsed

    json_data = extract_json_from_html(html, [
        r'var ytInitialData = (\{.*?\});',
        r'window\["ytInitialData"\]\s*=\s*(\{.*?\});',
        r'ytInitialData\s*=\s*(\{.*?\});',
        r'window\["ytInitialData"\]\s*=\s*\(\s*(\{.*?\})\s*\);',
        r'window\[\'ytInitialData\'\]\s*=\s*(\{.*?\});',
        r'var ytInitialPlayerResponse\s*=\s*(\{.*?\});',
        r'"ytInitialData"\s*:\s*(\{.*?\})',
    ])
    if isinstance(json_data, (dict, list)):
        result = extract_youtube_subscribers_from_json(json_data)
        if result is not None:
            return result

    return None


YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


def extract_youtube_channel_identifier(url: str) -> tuple[str, str] | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part and part.lower() != "about"]
        if not parts:
            return None

        first = parts[0]
        if first.lower() == "channel" and len(parts) > 1:
            return "channel", parts[1]
        if first.lower() == "user" and len(parts) > 1:
            return "user", parts[1]
        if first.lower() == "c" and len(parts) > 1:
            return "custom", parts[1]
        if first.startswith("@"):
            return "handle", first.lstrip("@")
        if first.lower() not in {"watch", "results", "feed", "playlist", "shorts", "live", "embed"}:
            return "custom", first
    except Exception:
        pass
    return None


def get_youtube_channel_id_from_api(url: str, api_key: str) -> str | None:
    identifier = extract_youtube_channel_identifier(url)
    if not identifier:
        return None

    channel_kind, value = identifier
    try:
        if channel_kind == "channel":
            params = {"part": "statistics", "id": value, "key": api_key}
            resp = requests_get(f"{YOUTUBE_API_BASE_URL}/channels", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items") or []
            if items:
                return items[0].get("id")
        elif channel_kind == "user":
            params = {"part": "statistics", "forUsername": value, "key": api_key}
            resp = requests_get(f"{YOUTUBE_API_BASE_URL}/channels", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items") or []
            if items:
                return items[0].get("id")
        else:
            params = {"part": "snippet", "type": "channel", "q": value, "maxResults": 1, "key": api_key}
            resp = requests_get(f"{YOUTUBE_API_BASE_URL}/search", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items") or []
            if items:
                return items[0].get("id", {}).get("channelId")
    except Exception:
        return None
    return None


def get_youtube_subscribers_via_api(url: str, api_key: str) -> int | None:
    if not url or not api_key:
        return None

    channel_id = get_youtube_channel_id_from_api(url, api_key)
    if not channel_id:
        return None

    try:
        params = {"part": "statistics", "id": channel_id, "key": api_key}
        resp = requests_get(f"{YOUTUBE_API_BASE_URL}/channels", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items") or []
        if not items:
            return None
        statistics = items[0].get("statistics") or {}
        count = statistics.get("subscriberCount")
        if count is None:
            return None
        return int(count)
    except Exception:
        return None


def build_youtube_about_url(url: str) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        if not path:
            return url
        if path.endswith('/about'):
            return url
        new_path = path + '/about'
        return parsed._replace(path=new_path, query='', fragment='').geturl()
    except Exception:
        return None


def get_youtube_subscribers(url: str) -> int | None:
    if not url:
        return None

    api_key = YOUTUBE_API_KEY
    if api_key:
        count = get_youtube_subscribers_via_api(url, api_key)
        if count is not None:
            return count

    try:
        resp = requests_get(url, headers=SOCIAL_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
        count = parse_youtube_subscriber_count_from_html(html)
        if count is not None:
            return count

        about_url = build_youtube_about_url(url)
        if about_url and about_url != url:
            resp = requests_get(about_url, headers=SOCIAL_HEADERS, timeout=15)
            resp.raise_for_status()
            html = resp.text
            count = parse_youtube_subscriber_count_from_html(html)
            if count is not None:
                return count
    except Exception:
        pass
    return None


def extract_tiktok_followers_from_json(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"followerCount", "follower_count", "followers", "fans", "subscriberCount"}:
                if isinstance(value, int):
                    return value
                if isinstance(value, str):
                    parsed = parse_number(value)
                    if parsed is not None:
                        return parsed
            if isinstance(value, (dict, list)):
                nested = extract_tiktok_followers_from_json(value)
                if nested is not None:
                    return nested
    elif isinstance(data, list):
        for item in data:
            nested = extract_tiktok_followers_from_json(item)
            if nested is not None:
                return nested
    return None


def parse_tiktok_follower_count_from_html(html: str) -> int | None:
    if not html:
        return None

    patterns = [
        r'"followerCount"\s*:\s*(\d+)',
        r'"followers"\s*:\s*(\d+)',
        r'"follower_count"\s*:\s*(\d+)',
        r'"fans"\s*:\s*(\d+)',
        r'"followerCountText"\s*:\s*\{"simpleText"\s*:\s*"([^"]+)"\}',
        r'([\d,\.KM]+)\s*followers',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return parse_number(match.group(1))

    json_data = extract_json_from_html(html, [
        r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>',
        r'window\.__INIT_PROPS__\s*=\s*(\{.*?\});',
        r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});',
        r'<!--\s*\{"props".*?-->',
    ])
    if isinstance(json_data, (dict, list)):
        return extract_tiktok_followers_from_json(json_data)
    return None


def get_tiktok_followers(url: str) -> int | None:
    if not url:
        return None

    try:
        resp = requests_get(url, headers=SOCIAL_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
        count = parse_tiktok_follower_count_from_html(html)
        if count is not None:
            return count
    except Exception:
        pass
    return None


def get_spotify_followers_via_apify(url: str) -> int | None:
    if not url:
        return None

    token = os.environ.get("APIFY_API_TOKEN") or APIFY_API_TOKEN
    if not token:
        return None

    try:
        import apify_client
    except ImportError:
        return None

    try:
        client = apify_client.ApifyClient(token)
        run_input = {
            "mode": "urls",
            "urls": [url],
        }
        run = client.actor("PIJgVEhbc8dGehrsP").call(run_input=run_input)

        dataset_id = None
        if isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
        elif hasattr(run, "to_dict"):
            run_dict = run.to_dict()
            dataset_id = run_dict.get("defaultDatasetId") or run_dict.get("default_dataset_id")
        else:
            dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)

        if not dataset_id:
            return None

        dataset = client.dataset(dataset_id)
        for item in dataset.iterate_items():
            count = extract_followers_count_from_profile_results(item)
            if count is not None:
                return count
    except Exception:
        return None

    return None


def get_spotify_followers(url: str) -> int | None:
    if not url:
        return None

    return get_spotify_followers_via_apify(url)


def get_soundcloud_followers(url: str) -> int | None:
    if not url:
        return None

    try:
        resp = requests_get(url, headers=SOCIAL_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
        match = re.search(r'"followers_count":(\d+)', html)
        if match:
            return int(match.group(1))
        match = re.search(r'"followers":\{"count":(\d+)\}', html)
        if match:
            return int(match.group(1))
        match = re.search(r'>([\d,.]+)\s*followers<', html, re.IGNORECASE)
        if match:
            return parse_number(match.group(1))
    except Exception:
        pass
    return None


def extract_facebook_followers_from_json(data):
    if isinstance(data, dict):
        keys = {
            "followers_count",
            "followersCount",
            "profile_followers_count",
            "profileFollowersCount",
            "followed_by_count",
            "followedByCount",
            "friends_count",
            "fan_count",
            "subscriber_count",
            "mobile_followers_count",
        }
        for key in keys:
            if key in data:
                value = data.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, str):
                    parsed = parse_number(value)
                    if parsed is not None:
                        return parsed
        for value in data.values():
            if isinstance(value, (dict, list)):
                nested = extract_facebook_followers_from_json(value)
                if nested is not None:
                    return nested
    elif isinstance(data, list):
        for item in data:
            nested = extract_facebook_followers_from_json(item)
            if nested is not None:
                return nested
    return None


def parse_facebook_follower_count_from_html(html: str) -> int | None:
    if not html:
        return None

    patterns = [
        r'"followers_count"\s*:\s*([0-9,\.]+)',
        r'"followersCount"\s*:\s*([0-9,\.]+)',
        r'"profile_followers_count"\s*:\s*([0-9,\.]+)',
        r'"profileFollowersCount"\s*:\s*([0-9,\.]+)',
        r'"followed_by_count"\s*:\s*([0-9,\.]+)',
        r'"followedByCount"\s*:\s*([0-9,\.]+)',
        r'"fan_count"\s*:\s*([0-9,\.]+)',
        r'"subscriber_count"\s*:\s*([0-9,\.]+)',
        r'>([0-9][0-9,\.\s]*)\s*followers?<',
        r'>([0-9][0-9,\.\s]*)\s*people follow this<',
        r'>([0-9][0-9,\.\s]*)\s*دنبال(?:‌کنندگان|کننده|شده)<',
        r'([0-9][0-9,\.\s]*)\s*followers',
        r'([0-9][0-9,\.\s]*)\s*follow',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            parsed = parse_number(match.group(1))
            if parsed is not None:
                return parsed

    json_data = extract_json_from_html(html, [
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        r'<script[^>]+id=".*?"[^>]*>(.*?)</script>',
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
        r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});',
        r'__INITIAL_STATE__\s*=\s*(\{.*?\});',
    ])
    if isinstance(json_data, (dict, list)):
        count = extract_facebook_followers_from_json(json_data)
        if count is not None:
            return count

    soup = BeautifulSoup(html, "html.parser")
    for text in soup.stripped_strings:
        if re.search(r"followers|people follow this|دنبال|فالوور", text, re.IGNORECASE):
            parsed = parse_number(text)
            if parsed is not None:
                return parsed

    return None


def build_facebook_plugin_url(url: str) -> str | None:
    if not url:
        return None

    try:
        quoted_url = requests.utils.requote_uri(url)
        return f"https://www.facebook.com/plugins/page.php?href={quoted_url}&tabs=timeline"
    except Exception:
        return None


def get_facebook_followers(url: str) -> int | None:
    if not url:
        return None

    try:
        resp = requests_get(url, headers=SOCIAL_HEADERS, timeout=20)
        resp.raise_for_status()
        html = resp.text
        count = parse_facebook_follower_count_from_html(html)
        if count is not None:
            return count
    except Exception:
        pass

    plugin_url = build_facebook_plugin_url(url)
    if plugin_url:
        try:
            resp = requests_get(plugin_url, headers=SOCIAL_HEADERS, timeout=20)
            resp.raise_for_status()
            count = parse_facebook_follower_count_from_html(resp.text)
            if count is not None:
                return count
        except Exception:
            pass

    return None


def scrape_social_counts(artist):
    if not artist:
        return []

    platforms = [
        {"key": "instagram", "label": "اینستاگرام", "url": artist.instagram, "count": None},
        {"key": "youtube", "label": "یوتیوب", "url": artist.youtube_channel_url, "count": None},
        {"key": "facebook", "label": "فیسبوک", "url": artist.facebook, "count": None},
        {"key": "spotify", "label": "اسپاتیفای", "url": artist.spotify_artist_url, "count": None},
        {"key": "soundcloud", "label": "ساندکلاد", "url": artist.soundcloud_url, "count": None},
        {"key": "x", "label": "ایکس", "url": artist.x, "count": None},
    ]

    for platform in platforms:
        if not platform["url"]:
            continue
        try:
            if platform["key"] == "instagram":
                platform["count"] = get_instagram_followers(platform["url"])
            elif platform["key"] == "youtube":
                platform["count"] = get_youtube_subscribers(platform["url"])
            elif platform["key"] == "spotify":
                platform["count"] = get_spotify_followers(platform["url"])
            elif platform["key"] == "soundcloud":
                platform["count"] = get_soundcloud_followers(platform["url"])
            elif platform["key"] == "x":
                platform["count"] = get_x_followers(platform["url"])
            elif platform["key"] == "facebook":
                platform["count"] = get_facebook_followers(platform["url"])
        except Exception:
            platform["count"] = None

    return platforms


def scrape_single_social_count(artist, platform_key):
    if not artist or not platform_key:
        return None

    platform_url_map = {
        "instagram": artist.instagram,
        "youtube": artist.youtube_channel_url,
        "facebook": artist.facebook,
        "spotify": artist.spotify_artist_url,
        "soundcloud": artist.soundcloud_url,
        "x": artist.x,
        "tiktok": artist.tiktok,
    }
    url = platform_url_map.get(platform_key)
    if not url:
        return None

    try:
        if platform_key == "instagram":
            return get_instagram_followers(url)
        if platform_key == "youtube":
            return get_youtube_subscribers(url)
        if platform_key == "facebook":
            return get_facebook_followers(url)
        if platform_key == "spotify":
            return get_spotify_followers(url)
        if platform_key == "soundcloud":
            return get_soundcloud_followers(url)
        if platform_key == "x":
            return get_x_followers(url)
        if platform_key == "tiktok":
            return get_tiktok_followers(url)
    except Exception:
        return None

    return None


def get_stored_social_stats(artist):
    if not artist or not artist.wikipedia_data:
        return []

    record = artist.wikipedia_data
    platforms = [
        {"key": "instagram", "label": "اینستاگرام", "url": artist.instagram, "count": record.instagram_followers},
        {"key": "youtube", "label": "یوتیوب", "url": artist.youtube_channel_url, "count": record.youtube_subscribers},
        {"key": "facebook", "label": "فیسبوک", "url": artist.facebook, "count": record.facebook_followers},
        {"key": "spotify", "label": "اسپاتیفای", "url": artist.spotify_artist_url, "count": record.spotify_followers},
        {"key": "soundcloud", "label": "ساندکلاد", "url": artist.soundcloud_url, "count": record.soundcloud_followers},
        {"key": "x", "label": "ایکس", "url": artist.x, "count": record.x_followers},
        {"key": "tiktok", "label": "تیک‌تاک", "url": artist.tiktok, "count": getattr(record, 'tiktok_followers', None)},
    ]

    return [platform for platform in platforms if platform["url"] or platform["count"] is not None]


def combine_youtube_view_counts(counts):
    """مجموع بازدیدهای یوتیوب را از چند لینک مختلف جمع می‌کند."""
    total = 0
    for value in counts:
        if value is None:
            continue
        try:
            total += int(value)
        except (TypeError, ValueError):
            continue
    return total


def update_track_views(track, platform):
    """آمار یک پلتفرم را برای یک ترک خاص به‌روزرسانی می‌کند."""
    if platform == "youtube":
        youtube_links = [track.youtube_url, getattr(track, "youtube_url_secondary", None)]
        youtube_views = [get_youtube_views(link) for link in youtube_links if link]
        views = combine_youtube_view_counts(youtube_views)
        if views is None or views <= 0:
            return False
        db.session.add(ViewStat(track_id=track.id, platform="youtube", views=views))
    elif platform == "soundcloud":
        views = get_soundcloud_plays(track.soundcloud_url)
        if views is None or views <= 0:
            return False
        db.session.add(ViewStat(track_id=track.id, platform="soundcloud", views=views))
    elif platform == "spotify":
        with SpotifyClient() as client:
            getspotifyplay = client.get_track(track.spotify_url)
        try:
            views = getspotifyplay.play_count
        except Exception:
            views = None

        if views is None or views <= 0:
            return False
        db.session.add(ViewStat(track_id=track.id, platform="spotify", views=views))
    else:
        return False

    db.session.commit()
    return True


def update_track_stats(track, platform="all"):
    """Update one platform or all platforms for a track."""
    if platform == "all":
        updated = False
        for current_platform in ("spotify", "youtube", "soundcloud"):
            updated = update_track_views(track, current_platform) or updated
        return updated

    return update_track_views(track, platform)


def update_all_tracks(app):
    """برای هر ترک، آخرین آمار سه پلتفرم را می‌گیرد و رکورد جدید ثبت می‌کند."""
    with app.app_context():
        tracks = Track.query.all()
        print(f"[updater] شروع آپدیت {len(tracks)} ترک در {datetime.now()}")

        for track in tracks:
            try:
                updated = update_track_stats(track, platform="all")
                if updated:
                    print(f"  ✓ {track.title}: آمار به‌روزرسانی شد")
                else:
                    print(f"  • {track.title}: هیچ آمار معتبری دریافت نشد")
            except Exception as e:
                db.session.rollback()
                print(f"  ✗ خطا در ترک {track.title}: {e}")

        print("[updater] آپدیت تمام شد.")


def update_artist_social_counts(app):
    """برای آرتیست، تعداد فالورها/سابسکرایب‌ها را استخراج و ذخیره می‌کند."""
    with app.app_context():
        artist = Artist.query.first()
        if not artist:
            print("[updater] هیچ آرتیستی برای بروزرسانی اجتماعی پیدا نشد.")
            return

        try:
            counts = scrape_social_counts(artist)
            wiki_record = artist.wikipedia_data
            if wiki_record is None:
                wiki_record = ArtistWikipediaData(artist=artist)
                db.session.add(wiki_record)
            now = datetime.now()

            for platform in counts:
                key = platform["key"]
                value = platform["count"]
                if key == "instagram":
                    wiki_record.instagram_followers = value
                elif key == "youtube":
                    wiki_record.youtube_subscribers = value
                elif key == "facebook":
                    wiki_record.facebook_followers = value
                elif key == "spotify":
                    wiki_record.spotify_followers = value
                elif key == "soundcloud":
                    wiki_record.soundcloud_followers = value
                elif key == "x":
                    wiki_record.x_followers = value

            wiki_record.social_counts_updated_at = now
            db.session.add(wiki_record)
            db.session.commit()
            print(f"[updater] اطلاعات اجتماعی آرتیست در {now} ذخیره شد.")
        except Exception as e:
            db.session.rollback()
            print(f"  ✗ خطا در بروزرسانی اطلاعات اجتماعی آرتیست: {e}")


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def backfill_track_release_dates():
    if not db.engine.url.get_backend_name() == "sqlite":
        return

    with db.session.begin():
        tracks = Track.query.filter(Track.release_date.is_(None)).all()
        for track in tracks:
            if track.album and track.album.release_date:
                track.release_date = track.album.release_date


def ensure_track_columns(app):
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        return

    engine = db.engine
    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(track)").fetchall()}
        missing_columns = []
        if "genre" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN genre VARCHAR(60)")
        if "release_date" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN release_date DATE")
        if "is_active" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN is_active BOOLEAN DEFAULT 1")
        if "sort_order" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN sort_order INTEGER DEFAULT 0")
        if "youtube_url_secondary" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN youtube_url_secondary VARCHAR(500)")
        if "youtube_url_is_music_video" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN youtube_url_is_music_video BOOLEAN DEFAULT 0")
        if "youtube_url_secondary_is_music_video" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN youtube_url_secondary_is_music_video BOOLEAN DEFAULT 0")
        if "is_the_shah" not in existing:
            missing_columns.append("ALTER TABLE track ADD COLUMN is_the_shah BOOLEAN DEFAULT 0")
        for sql in missing_columns:
            conn.exec_driver_sql(sql)

    backfill_track_release_dates()


def ensure_user_columns(app):
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        return

    engine = db.engine
    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(user)").fetchall()}
        missing_columns = []
        if "username" not in existing:
            missing_columns.append("ALTER TABLE user ADD COLUMN username VARCHAR(150)")
        if "is_admin" not in existing:
            missing_columns.append("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        for sql in missing_columns:
            conn.exec_driver_sql(sql)


def ensure_artist_columns(app):
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        return

    engine = db.engine
    with engine.connect() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(artist)").fetchall()}
        missing_columns = []
        for column_name, definition in {
            "x": "VARCHAR(300)",
            "tiktok": "VARCHAR(300)",
            "telegram": "VARCHAR(300)",
            "facebook": "VARCHAR(500)",
        }.items():
            if column_name not in existing:
                missing_columns.append(f"ALTER TABLE artist ADD COLUMN {column_name} {definition}")
        for sql in missing_columns:
            conn.exec_driver_sql(sql)


def ensure_artist_wikipedia_data_table(app):
    if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        return

    engine = db.engine
    with engine.connect() as conn:
        tables = {row[0] for row in conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "artist_wikipedia_data" not in tables:
            conn.exec_driver_sql(
                """
                CREATE TABLE artist_wikipedia_data (
                    id INTEGER NOT NULL,
                    artist_id INTEGER NOT NULL,
                    title VARCHAR(300),
                    image_url VARCHAR(500),
                    timeline_section TEXT,
                    instagram_followers BIGINT,
                    youtube_subscribers BIGINT,
                    facebook_followers BIGINT,
                    spotify_followers BIGINT,
                    soundcloud_followers BIGINT,
                    x_followers BIGINT,
                    tiktok_followers BIGINT,
                    social_counts_updated_at DATETIME,
                    infobox_json TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    PRIMARY KEY (id),
                    UNIQUE (artist_id)
                )
                """
            )
            existing_wiki_columns = {
                "id",
                "artist_id",
                "title",
                "image_url",
                "timeline_section",
                "instagram_followers",
                "youtube_subscribers",
                "spotify_followers",
                "soundcloud_followers",
                "x_followers",
                "tiktok_followers",
                "social_counts_updated_at",
                "infobox_json",
                "created_at",
                "updated_at",
            }
        else:
            existing_wiki_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(artist_wikipedia_data)").fetchall()}

        required_columns = {
            "timeline_section": "TEXT",
            "instagram_followers": "BIGINT",
            "youtube_subscribers": "BIGINT",
            "facebook_followers": "BIGINT",
            "spotify_followers": "BIGINT",
            "soundcloud_followers": "BIGINT",
            "x_followers": "BIGINT",
            "tiktok_followers": "BIGINT",
            "social_counts_updated_at": "DATETIME",
        }

        if "timeline_section" not in existing_wiki_columns and "timeline_section_1" in existing_wiki_columns:
            conn.exec_driver_sql("ALTER TABLE artist_wikipedia_data ADD COLUMN timeline_section TEXT")
            conn.exec_driver_sql(
                "UPDATE artist_wikipedia_data SET timeline_section = timeline_section_1 WHERE timeline_section IS NULL"
            )
            existing_wiki_columns.add("timeline_section")

        for column_name, definition in required_columns.items():
            if column_name not in existing_wiki_columns:
                conn.exec_driver_sql(f"ALTER TABLE artist_wikipedia_data ADD COLUMN {column_name} {definition}")
                existing_wiki_columns.add(column_name)

        if 'site_media' not in tables:
            conn.exec_driver_sql(
                "CREATE TABLE site_media ("
                "id INTEGER NOT NULL,"
                "type VARCHAR(20) NOT NULL,"
                "url VARCHAR(500) NOT NULL,"
                "label VARCHAR(500),"
                "created_at DATETIME,"
                "PRIMARY KEY (id)"
                ")"
            )

        artist_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(artist)").fetchall()}
        if "wikipedia_title" in artist_columns:
            rows = conn.exec_driver_sql(
                "SELECT id, wikipedia_title, wikipedia_image_url, wikipedia_infobox_json FROM artist"
            ).fetchall()
            for row in rows:
                artist_id, title, image_url, infobox_json = row
                existing = conn.exec_driver_sql(
                    "SELECT 1 FROM artist_wikipedia_data WHERE artist_id = ?",
                    (artist_id,),
                ).fetchone()
                if existing is None:
                    conn.exec_driver_sql(
                        "INSERT INTO artist_wikipedia_data (artist_id, title, image_url, infobox_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (artist_id, title, image_url, infobox_json, datetime.now(), datetime.now()),
                    )
        if "youtube_subscribers" not in existing_wiki_columns:
            conn.exec_driver_sql("ALTER TABLE artist_wikipedia_data ADD COLUMN youtube_subscribers BIGINT")
        if "spotify_followers" not in existing_wiki_columns:
            conn.exec_driver_sql("ALTER TABLE artist_wikipedia_data ADD COLUMN spotify_followers BIGINT")
        if "soundcloud_followers" not in existing_wiki_columns:
            conn.exec_driver_sql("ALTER TABLE artist_wikipedia_data ADD COLUMN soundcloud_followers BIGINT")
        if "x_followers" not in existing_wiki_columns:
            conn.exec_driver_sql("ALTER TABLE artist_wikipedia_data ADD COLUMN x_followers BIGINT")
        if "tiktok_followers" not in existing_wiki_columns:
            conn.exec_driver_sql("ALTER TABLE artist_wikipedia_data ADD COLUMN tiktok_followers BIGINT")
        if "social_counts_updated_at" not in existing_wiki_columns:
            conn.exec_driver_sql("ALTER TABLE artist_wikipedia_data ADD COLUMN social_counts_updated_at DATETIME")

def build_hero_background_style(artist, albums, tracks):
    if artist and artist.cover_url:
        return (
            "background-image: linear-gradient(120deg, rgba(6, 6, 8, 0.9) 0%, rgba(6, 6, 8, 0.56) 45%, rgba(6, 6, 8, 0.95) 100%), "
            f"url('{artist.cover_url}'); background-size: cover; background-position: center; background-repeat: no-repeat;"
        )
    return ""


def slugify_text(value):
    if not value:
        return "item"

    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "item"


def get_release_label(track):
    album = getattr(track, "album", None)
    if not album:
        return "تک‌آهنگ"

    release_type = getattr(album, "release_type", None)
    if release_type == "single":
        return "single"
    if release_type == "ep":
        return "ep"
    if release_type == "album":
        return "album"

    if getattr(album, "title", None):
        track_count = len(getattr(album, "tracks", []) or [])
        if track_count <= 1:
            return "single"
        if track_count <= 4:
            return "ep"
        return "album"

    return "تک‌آهنگ"


def clean_wikipedia_text(text):
    if not text:
        return text
    text = re.sub(r"\[\[.*?\]\]\([^\)]*\)", " ", text)
    text = re.sub(r"\s*\[[^\]]*\]\s*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def parse_text_sections(text):
    if not text:
        return []

    sections = []
    for chunk in [c.strip() for c in text.split("\n\n") if c.strip()]:
        if ":" in chunk:
            title, description = chunk.split(":", 1)
            sections.append({"title": title.strip(), "description": description.strip()})
        else:
            sections.append({"title": None, "description": chunk})
    return sections


def parse_stored_wikipedia_data(artist):
    if not artist:
        return None

    wiki_record = artist.wikipedia_data
    if not wiki_record:
        return None

    paragraphs = []
    infobox = []
    if wiki_record.infobox_json:
        try:
            infobox = json.loads(wiki_record.infobox_json)
        except ValueError:
            infobox = []

    timeline_section = None
    if wiki_record.timeline_section and wiki_record.timeline_section.strip():
        timeline_section = wiki_record.timeline_section
    social_stats = get_stored_social_stats(artist)
    media = []

    if not paragraphs and not infobox and not wiki_record.title and not wiki_record.image_url and not timeline_section and not social_stats:
        return None

    return {
        "error": None,
        "paragraphs": paragraphs,
        "infobox": infobox,
        "image_url": wiki_record.image_url,
        "media": media,
        "title": wiki_record.title or artist.name,
        "social_stats": social_stats,
        "timeline_section": timeline_section,
    }


def get_artist_wikipedia_data(artist, force_refresh=False):
    if not artist:
        return {
            "error": "آرتیستی برای نمایش پیدا نشد.",
            "paragraphs": [],
            "infobox": [],
            "image_url": None,
            "title": None,
        }

    stored_data = parse_stored_wikipedia_data(artist)
    if stored_data:
        return stored_data

    return {
        "error": "اطلاعات ویکی‌پدیا ذخیره نشده است.",
        "paragraphs": [],
        "infobox": [],
        "image_url": None,
        "title": None,
    }


def get_next_release_info(tracks):
    today = datetime.now().date()
    upcoming = []

    for track in tracks:
        release_date = getattr(track, "release_date", None)
        if not release_date:
            album = getattr(track, "album", None)
            release_date = getattr(album, "release_date", None)
        if not release_date:
            continue
        if release_date < today:
            continue

        upcoming.append((release_date, track))

    if not upcoming:
        return {
            "title": None,
            "date": None,
            "days_left": None,
            "kind": None,
            "message": "هنوز انتشار بعدی ثبت نشده است",
        }

    release_date, track = sorted(
        upcoming,
        key=lambda item: (
            item[0],
            0 if getattr(getattr(item[1], "album", None), "title", None) else 1,
        ),
    )[0]
    album = getattr(track, "album", None)
    if album and getattr(album, "title", None):
        title = album.title
        kind = "آلبوم"
    else:
        title = getattr(track, "title", None) or "انتشار"
        kind = "آهنگ"

    days_left = (release_date - today).days
    return {
        "title": title,
        "date": release_date,
        "days_left": days_left,
        "kind": kind,
        "message": None,
    }


def build_release_calendar_data(tracks):
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    weekday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    today = datetime.now().date()
    grouped = {}

    for track in tracks:
        release_date = getattr(track, "release_date", None)
        if not release_date:
            album = getattr(track, "album", None)
            release_date = getattr(album, "release_date", None)
        if not release_date:
            continue
        key = release_date.month
        grouped.setdefault(key, []).append(track)

    calendar_groups = []
    month_order = []
    if today.month in grouped:
        start_month = today.month
        current_month = start_month
        for _ in range(12):
            if current_month in grouped:
                month_order.append(current_month)
            current_month += 1
            if current_month > 12:
                current_month = 1
            if current_month == start_month:
                break

    if not month_order:
        month_order = sorted(grouped.keys())

    for month, items in [(month, grouped[month]) for month in month_order]:
        grouped_by_day = {}
        for track in items:
            release_date = getattr(track, "release_date", None)
            if not release_date:
                album = getattr(track, "album", None)
                release_date = getattr(album, "release_date", None)
            day = getattr(release_date, "day", None)
            if day is None:
                continue
            grouped_by_day.setdefault(day, []).append(track)

        entries = []
        for day, day_tracks in sorted(grouped_by_day.items(), reverse=True):
            day_tracks = sorted(day_tracks, key=lambda item: getattr(item, "title", ""))
            album_groups = {}
            for track in day_tracks:
                album = getattr(track, "album", None)
                album_title = getattr(album, "title", None) or ""
                if album_title:
                    album_groups.setdefault(album_title, []).append(track)

            album_entries = []
            for album_title, album_tracks in album_groups.items():
                if len(album_tracks) <= 1:
                    continue
                album_entry = album_tracks[0].album
                release_years = sorted({
                    getattr(track_release_date, "year", None)
                    for track_release_date in [
                        getattr(track, "release_date", None) or getattr(getattr(track, "album", None), "release_date", None)
                        for track in album_tracks
                    ]
                    if getattr(track_release_date, "year", None) is not None
                }, reverse=True)
                album_entries.append({
                    "day": day,
                    "display_title": album_title,
                    "kind": "album",
                    "count": len(album_tracks),
                    "release_year": release_years[0] if release_years else None,
                    "release_years": release_years,
                    "tracks": album_tracks,
                    "tooltip_text": "\n".join(
                        f"• {track.title} ({getattr(getattr(track, 'release_date', None), 'year', '')})"
                        for track in sorted(album_tracks, key=lambda item: getattr(item, "title", ""))
                    ),
                    "album": album_entry,
                })

            if album_entries:
                entries.extend(album_entries)
                continue

            for track in day_tracks:
                release_years = sorted({
                    getattr(track_release_date, "year", None)
                    for track_release_date in [
                        getattr(track, "release_date", None) or getattr(getattr(track, "album", None), "release_date", None)
                    ]
                    if getattr(track_release_date, "year", None) is not None
                }, reverse=True)
                entries.append({
                    "day": day,
                    "display_title": getattr(track, "title", None) or "",
                    "kind": "track",
                    "count": 1,
                    "release_year": release_years[0] if release_years else None,
                    "release_years": release_years,
                    "tracks": [track],
                    "tooltip_text": f"• {track.title} ({getattr(getattr(track, 'release_date', None), 'year', '')})",
                    "album": getattr(track, "album", None),
                })

        month_days = []
        current_year = today.year
        sample_date = datetime(current_year, month, 1)
        first_weekday = sample_date.weekday()
        if month == 12:
            next_month = datetime(current_year + 1, 1, 1)
        else:
            next_month = datetime(current_year, month + 1, 1)
        days_in_month = (next_month - datetime(current_year, month, 1)).days

        for blank in range(first_weekday):
            month_days.append({"day": None, "is_blank": True, "entries": []})

        for day in range(1, days_in_month + 1):
            day_entries = [entry for entry in entries if entry["day"] == day]
            primary_entry = day_entries[0] if day_entries else None
            tooltip_tracks = sorted(
                [track for entry in day_entries for track in entry["tracks"]],
                key=lambda item: getattr(item, "title", "")
            )
            month_days.append({
                "day": day,
                "is_blank": False,
                "entry": primary_entry,
                "entries": day_entries,
                "is_today": date(current_year, month, day) == today,
                "has_release": bool(day_entries),
                "tooltip_text": "\n".join(
                    f"• {track.title} ({getattr(getattr(track, 'release_date', None), 'year', '')})"
                    for track in tooltip_tracks
                ),
            })

        release_day_count = sum(1 for day in month_days if not day["is_blank"] and day["has_release"])
        calendar_groups.append({
            "month": month,
            "month_name": month_names[month - 1],
            "entries": entries,
            "calendar_days": month_days,
            "weekday_names": weekday_names,
            "is_current_month": month == today.month,
            "release_day_count": release_day_count,
        })

    return calendar_groups


def normalize_text(value):
    if not value:
        return ""

    mapping = str.maketrans({
        "ا": "a",
        "آ": "a",
        "أ": "a",
        "إ": "i",
        "ب": "b",
        "پ": "p",
        "ت": "t",
        "ث": "s",
        "ج": "j",
        "چ": "ch",
        "ح": "h",
        "خ": "kh",
        "د": "d",
        "ذ": "z",
        "ر": "r",
        "ز": "z",
        "ژ": "zh",
        "س": "s",
        "ش": "sh",
        "ص": "s",
        "ض": "z",
        "ط": "t",
        "ظ": "z",
        "ع": "",
        "غ": "gh",
        "ف": "f",
        "ق": "gh",
        "ک": "k",
        "گ": "g",
        "ل": "l",
        "م": "m",
        "ن": "n",
        "و": "u",
        "ؤ": "u",
        "ى": "i",
        "ي": "i",
        "ی": "i",
        "ئ": "i",
        "ء": "",
        "ه": "e",
        "ة": "e",
        "٪": "",
    })

    normalized = unicodedata.normalize("NFKD", str(value))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.translate(mapping)
    normalized = normalized.lower()

    replacements = [
        (r"(ee|ie|ei|ey)", "i"),
        (r"(oo|ou)", "u"),
        (r"(aa|ah)", "a"),
        (r"([aeiou])\1+", r"\1"),
        (r"([aeiou])e\b", r"\1"),
        (r"ai", "i"),
        (r"au", "u"),
    ]
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)

    normalized = re.sub(r"^[aeiou]+", "", normalized)
    normalized = re.sub(r"[^a-z0-9]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def normalize_search_tokens(value):
    if not value:
        return []

    text = re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()
    return [token for token in text.split() if token]


def search_match_score(query, candidate):
    query_tokens = normalize_search_tokens(query)
    candidate_tokens = normalize_search_tokens(candidate)
    if not query_tokens or not candidate_tokens:
        return 0

    query_text = " ".join(query_tokens)
    candidate_text = " ".join(candidate_tokens)

    if len(query_text) < 3:
        return 0

    score = 0
    if candidate_text == query_text:
        return 100
    if candidate_text.startswith(query_text) or query_text.startswith(candidate_text):
        score += 40
    if query_text in candidate_text:
        score += 25

    for query_token in query_tokens:
        if any(token == query_token for token in candidate_tokens):
            score += 18
        elif any(token.startswith(query_token) or query_token.startswith(token) for token in candidate_tokens):
            score += 8
        elif any(query_token in token or token in query_token for token in candidate_tokens):
            score += 4

    if len(query_tokens) > 1:
        matched_tokens = sum(
            1 for token in query_tokens
            if any(candidate_token == token or candidate_token.startswith(token) or token.startswith(candidate_token) for candidate_token in candidate_tokens)
        )
        if matched_tokens == len(query_tokens):
            score += 20
        elif matched_tokens >= max(1, len(query_tokens) // 2):
            score += 8

    return score


def text_matches(query, candidate):
    return search_match_score(query, candidate) >= 25


def initialize_database(app, reset=False):
    with app.app_context():
        if reset:
            db.drop_all()
        db.create_all()
        ensure_track_columns(app)
        ensure_user_columns(app)
        ensure_artist_columns(app)
        ensure_artist_wikipedia_data_table(app)
        backfill_track_release_dates()


def create_app():
    app = Flask(__name__)

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        print("Using PostgreSQL")
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'data.db')}"
        print("Using SQLite (local only)")

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

    db.init_app(app)
    Migrate(app, db)

    initialize_database(app, reset=False)

    from admin import admin_bp
    app.register_blueprint(admin_bp)

    register_routes(app)
    return app


def register_routes(app):
    @app.route("/")
    def home():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")
        albums = Album.query.filter_by(artist_id=artist.id).order_by(Album.release_date.desc()).all()

        grouped_albums = group_albums_for_display(albums)
        singles = grouped_albums["singles"]
        eps = grouped_albums["eps"]
        full_albums = grouped_albums["full_albums"]

        # پرطرفدارترین ترک‌ها برای نمایش در صفحه اصلی
        all_tracks = Track.query.join(Album).filter(Album.artist_id == artist.id, Track.is_active == True).all()
        top_tracks = sorted(all_tracks, key=lambda t: t.total_views(), reverse=True)[:10]

        # دسته‌بندی ترک‌ها بر اساس ژانر (سبک‌ها)
        genre_map = {}
        for t in all_tracks:
            genres = [g.strip() for g in (t.genre or "").split(",") if g.strip()]
            if not genres:
                genres = ["بدون سبک"]
            for g in genres:
                genre_map.setdefault(g, []).append(t)

        # مرتب‌سازی سبک‌ها بر اساس تعداد ترک
        styles = sorted(genre_map.items(), key=lambda kv: len(kv[1]), reverse=True)
        hero_background_style = build_hero_background_style(artist, albums, all_tracks)
        release_calendar = build_release_calendar_data(all_tracks)
        next_release = get_next_release_info(all_tracks)

        return render_template(
            "home.html",
            artist=artist,
            singles=singles,
            eps=eps,
            full_albums=full_albums,
            tracks=all_tracks,
            top_tracks=top_tracks,
            styles=styles,
            total_albums=len(albums),
            total_tracks=len(all_tracks),
            hero_background_style=hero_background_style,
            release_calendar=release_calendar,
            next_release=next_release,
        )

    @app.route("/release-calendar")
    def release_calendar_page():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")

        all_tracks = Track.query.join(Album).filter(Album.artist_id == artist.id, Track.is_active == True).all()
        release_calendar = build_release_calendar_data(all_tracks)
        next_release = get_next_release_info(all_tracks)
        today = datetime.now().date()
        today_releases = []
        for track in all_tracks:
            release_date = getattr(track, "release_date", None)
            if not release_date:
                album = getattr(track, "album", None)
                release_date = getattr(album, "release_date", None)
            if release_date == today:
                today_releases.append(track)
        return render_template(
            "release_calendar.html",
            artist=artist,
            release_calendar=release_calendar,
            next_release=next_release,
            current_datetime=datetime.now(),
            today_releases=today_releases,
        )

    @app.route("/wikipedia-artist")
    def wikipedia_artist():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")

        wiki_data = get_artist_wikipedia_data(artist)
        social_stats = get_stored_social_stats(artist)

        albums = Album.query.filter_by(artist_id=artist.id).order_by(Album.release_date.asc().nulls_last()).all()
        tracks = Track.query.join(Album).filter(Album.artist_id == artist.id, Track.is_active == True).order_by(Track.release_date.asc().nulls_last()).all()

        return render_template(
            "wikipedia_artist.html",
            artist=artist,
            wiki_data=wiki_data,
            social_stats=social_stats,
            discography_albums=albums,
            discography_tracks=tracks,
        )

    @app.route("/tracks")
    def top_tracks_list():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")
        
        # تمام ترک‌های هنرمند
        all_tracks = Track.query.join(Album).filter(Album.artist_id == artist.id, Track.is_active == True).order_by(Track.release_date.desc()).all()
        
        # مرتب‌سازی بر اساس کل views
        top_all = sorted(all_tracks, key=lambda t: t.total_views(), reverse=True)
        
        # مرتب‌سازی بر اساس هر پلتفرم
        top_spotify = sorted(all_tracks, key=lambda t: t.latest_stats().get('spotify') or 0, reverse=True)
        top_youtube = sorted(all_tracks, key=lambda t: t.latest_stats().get('youtube') or 0, reverse=True)
        top_soundcloud = sorted(all_tracks, key=lambda t: t.latest_stats().get('soundcloud') or 0, reverse=True)
        
        return render_template("top_tracks.html", artist=artist, 
                             top_all=top_all, 
                             top_spotify=top_spotify,
                             top_youtube=top_youtube, 
                             top_soundcloud=top_soundcloud)

    @app.route("/the-shah")
    def the_shah_tracks():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")

        tracks = (
            Track.query.join(Album)
            .filter(Album.artist_id == artist.id, Track.is_active == True, Track.is_the_shah == True)
            .order_by(Track.release_date.desc().nulls_last(), Track.sort_order.asc(), Track.title.asc())
            .all()
        )

        return render_template("the_shah_tracks.html", artist=artist, tracks=tracks)

    @app.route("/shahin-najafi")
    def shahin_najafi_tracks():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")

        tracks = (
            Track.query.join(Album)
            .filter(Album.artist_id == artist.id, Track.is_active == True, Track.is_the_shah == False)
            .order_by(Track.release_date.desc().nulls_last(), Track.sort_order.asc(), Track.title.asc())
            .all()
        )

        return render_template("shahin_najafi_tracks.html", artist=artist, tracks=tracks)

    @app.route("/albums")
    def albums_list():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")
        albums = Album.query.filter_by(artist_id=artist.id).order_by(Album.release_date.desc()).all()

        grouped_albums = group_albums_for_display(albums)
        singles = grouped_albums["singles"]
        eps = grouped_albums["eps"]
        full_albums = grouped_albums["full_albums"]

        return render_template("albums.html", artist=artist, singles=singles, eps=eps, full_albums=full_albums)

    @app.route("/album/<int:album_id>")
    @app.route("/album/<int:album_id>/<path:slug>")
    def album_detail(album_id, slug=None):
        album = Album.query.get_or_404(album_id)
        expected_slug = slugify_text(album.title)
        if slug and slug != expected_slug:
            return redirect(url_for("album_detail", album_id=album.id, slug=expected_slug), code=301)
        # only show active tracks on the album page
        tracks = sorted([t for t in (album.tracks or []) if getattr(t, 'is_active', True)], key=lambda t: t.total_views(), reverse=True)
        return render_template("album.html", album=album, tracks=tracks, artist=album.artist)

    @app.route("/track/<int:track_id>")
    @app.route("/track/<int:track_id>/<path:slug>")
    def track_detail(track_id, slug=None):
        import json
        # helper to get current user
        def get_current_user():
            uid = session.get('user_id')
            if not uid:
                return None
            return User.query.get(uid)

        track = Track.query.get_or_404(track_id)
        history = (
            ViewStat.query.filter_by(track_id=track.id)
            .order_by(ViewStat.fetched_at.asc())
            .all()
        )

        by_platform = {"spotify": [], "youtube": [], "soundcloud": []}
        daily_views = {platform: [] for platform in by_platform}

        for stat in history:
            if stat.platform in daily_views:
                day_key = stat.fetched_at.strftime("%Y-%m-%d")
                daily_views[stat.platform].append((day_key, stat.views))

        for platform, entries in daily_views.items():
            per_day = {}
            for day_key, value in entries:
                per_day[day_key] = value

            sorted_days = sorted(per_day)
            previous_value = None
            for day_key in sorted_days:
                current_value = per_day[day_key]
                delta = None
                if previous_value is not None:
                    delta = max(0, current_value - previous_value)
                by_platform[platform].append({
                    "date": day_key,
                    "value": current_value,
                    "views": current_value,
                    "label": day_key,
                    "total": current_value,
                    "increase": delta,
                })
                previous_value = current_value
        history_json = json.dumps(by_platform, ensure_ascii=False)

        current_user = get_current_user()
        is_premium = bool(current_user and current_user.is_premium)

        expected_slug = slugify_text(track.title)
        if slug and slug != expected_slug:
            return redirect(url_for("track_detail", track_id=track.id, slug=expected_slug), code=301)

        return render_template(
            "track.html", track=track, history=history,
            history_json=history_json,
            artist=track.album.artist, is_premium=is_premium
        )

    def get_current_user():
        uid = session.get('user_id')
        if not uid:
            return None
        return User.query.get(uid)

    @app.context_processor
    def inject_globals():
        return {
            "now_year": datetime.now().year,
            "current_user": get_current_user(),
            "slugify_text": slugify_text,
        }

    @app.route('/check-username')
    def check_username():
        username = request.args.get('username', '').strip()
        if not username:
            return jsonify({'taken': False, 'message': ''})

        normalized_username = username.lower()
        taken = User.query.filter(User.username.ilike(username)).first() is not None
        message = 'این نام کاربری انتخاب شده است.' if taken else ''
        return jsonify({'taken': taken, 'message': message})

    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if not email:
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'recovery_error': 'لطفاً ایمیل خود را وارد کنید.',
                        'show_recovery_popup': True,
                    })
                return render_template(
                    'login.html',
                    error=None,
                    forgot_message=None,
                    recovery_error='لطفاً ایمیل خود را وارد کنید.',
                    recovery_message=None,
                    show_recovery_popup=True,
                )

            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'recovery_error': 'فرمت ایمیل وارد شده صحیح نیست. لطفاً ایمیل را درست وارد کنید.',
                        'show_recovery_popup': True,
                    })
                return render_template(
                    'login.html',
                    error=None,
                    forgot_message=None,
                    recovery_error='فرمت ایمیل وارد شده صحیح نیست. لطفاً ایمیل را درست وارد کنید.',
                    recovery_message=None,
                    show_recovery_popup=True,
                )

            user = User.query.filter_by(email=email).first()
            if not user:
                if is_ajax:
                    return jsonify({
                        'success': False,
                        'recovery_error': 'ایمیل وارد شده اشتباه است. چنین ایمیلی در سیستم ثبت نشده است.',
                        'show_recovery_popup': True,
                    })
                return render_template(
                    'login.html',
                    error=None,
                    forgot_message=None,
                    recovery_error='ایمیل وارد شده اشتباه است. چنین ایمیلی در سیستم ثبت نشده است.',
                    recovery_message=None,
                    show_recovery_popup=True,
                )

            temp_password = secrets.token_urlsafe(4)
            user.password_hash = generate_password_hash(temp_password)
            db.session.commit()
            if is_ajax:
                return jsonify({
                    'success': True,
                    'recovery_message': 'ایمیل بازیابی رمز عبور برای شما ارسال شد. لطفاً ایمیل خود را بررسی کنید.',
                    'show_recovery_popup': True,
                })
            return render_template(
                'login.html',
                error=None,
                forgot_message=None,
                recovery_error=None,
                recovery_message='ایمیل بازیابی رمز عبور برای شما ارسال شد. لطفاً ایمیل خود را بررسی کنید.',
                show_recovery_popup=True,
            )

        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        forgot_message = None
        show_recovery_hint = False
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            email = request.form.get('email', '').strip().lower()
            action = request.form.get('action', 'login')
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            if action == 'login':
                if not username or not password:
                    error = 'نام کاربری و رمز را وارد کنید.'
                else:
                    identifier = username.strip()
                    if '@' in identifier:
                        user = User.query.filter_by(email=identifier.lower()).first()
                    else:
                        user = User.query.filter(User.username.ilike(identifier)).first()

                    if not user:
                        error = 'چنین کاربری وجود ندارد.'
                    elif not check_password_hash(user.password_hash, password):
                        error = 'رمز عبور اشتباه است. اگر این رمز را فراموش کرده‌اید، می‌توانید از بخش بازیابی رمز عبور با وارد کردن ایمیل خود، یک رمز جدید انتخاب کنید.'
                        show_recovery_hint = True
                    else:
                        session['user_id'] = user.id
                        return redirect(url_for('account'))
            elif action == 'forgot_password':
                if not email:
                    if is_ajax:
                        return jsonify({
                            'success': False,
                            'recovery_error': 'لطفاً ایمیل خود را وارد کنید.',
                            'show_recovery_popup': True,
                        })
                    return render_template(
                        'login.html',
                        error=None,
                        forgot_message=None,
                        show_recovery_hint=False,
                        recovery_error='لطفاً ایمیل خود را وارد کنید.',
                        recovery_message=None,
                        show_recovery_popup=True,
                    )

                if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                    if is_ajax:
                        return jsonify({
                            'success': False,
                            'recovery_error': 'فرمت ایمیل وارد شده صحیح نیست. لطفاً ایمیل را درست وارد کنید.',
                            'show_recovery_popup': True,
                        })
                    return render_template(
                        'login.html',
                        error=None,
                        forgot_message=None,
                        show_recovery_hint=False,
                        recovery_error='فرمت ایمیل وارد شده صحیح نیست. لطفاً ایمیل را درست وارد کنید.',
                        recovery_message=None,
                        show_recovery_popup=True,
                    )

                user = User.query.filter_by(email=email).first()
                if not user:
                    if is_ajax:
                        return jsonify({
                            'success': False,
                            'recovery_error': 'ایمیل وارد شده اشتباه است. چنین ایمیلی در سیستم ثبت نشده است.',
                            'show_recovery_popup': True,
                        })
                    return render_template(
                        'login.html',
                        error=None,
                        forgot_message=None,
                        show_recovery_hint=False,
                        recovery_error='ایمیل وارد شده اشتباه است. چنین ایمیلی در سیستم ثبت نشده است.',
                        recovery_message=None,
                        show_recovery_popup=True,
                    )

                temp_password = secrets.token_urlsafe(4)
                user.password_hash = generate_password_hash(temp_password)
                db.session.commit()
                if is_ajax:
                    return jsonify({
                        'success': True,
                        'recovery_message': 'ایمیل بازیابی رمز عبور برای شما ارسال شد. لطفاً ایمیل خود را بررسی کنید.',
                        'show_recovery_popup': True,
                    })
                return render_template(
                    'login.html',
                    error=None,
                    forgot_message=None,
                    show_recovery_hint=False,
                    recovery_error=None,
                    recovery_message='ایمیل بازیابی رمز عبور برای شما ارسال شد. لطفاً ایمیل خود را بررسی کنید.',
                    show_recovery_popup=True,
                )
            else:
                confirm_password = request.form.get('confirm_password', '')
                if not username:
                    error = 'نام کاربری را وارد کنید.'
                elif not email:
                    error = 'ایمیل را وارد کنید.'
                elif not password or not confirm_password:
                    error = 'رمز عبور و تکرار آن را وارد کنید.'
                elif password != confirm_password:
                    error = 'رمز عبور و تکرار آن باید مشابه باشند.'
                elif User.query.filter_by(email=email).first():
                    error = 'این ایمیل قبلاً ثبت شده است. لطفاً ایمیل دیگری انتخاب کنید.'
                elif User.query.filter(User.username.ilike(username)).first():
                    error = 'این نام کاربری قبلاً گرفته شده است. لطفاً نام دیگری انتخاب کنید.'
                else:
                    user = User(username=username, email=email, password_hash=generate_password_hash(password))
                    db.session.add(user)
                    db.session.commit()
                    session['user_id'] = user.id
                    return redirect(url_for('account'))

        return render_template(
            'login.html',
            error=error,
            forgot_message=forgot_message,
            show_recovery_hint=show_recovery_hint,
            recovery_error=None,
            recovery_message=None,
            show_recovery_popup=False,
        )

    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('home'))

    @app.route('/account', methods=['GET', 'POST'])
    def account():
        uid = session.get('user_id')
        if not uid:
            return redirect(url_for('login'))
        user = User.query.get_or_404(uid)
        error = None
        message = None

        if request.method == 'POST':
            section = request.form.get('section')
            if section == 'username':
                new_username = request.form.get('username', '').strip()
                if not new_username:
                    error = 'نام کاربری را وارد کنید.'
                elif new_username != user.username and User.query.filter_by(username=new_username).first():
                    error = 'این نام کاربری در حال حاضر استفاده شده است.'
                else:
                    user.username = new_username
                    db.session.commit()
                    message = 'نام کاربری با موفقیت به‌روزرسانی شد.'
            elif section == 'email':
                new_email = request.form.get('email', '').strip().lower()
                if not new_email:
                    error = 'لطفاً یک ایمیل معتبر وارد کنید.'
                elif new_email != user.email and User.query.filter_by(email=new_email).first():
                    error = 'این ایمیل در حال حاضر استفاده شده است.'
                else:
                    user.email = new_email
                    db.session.commit()
                    message = 'ایمیل با موفقیت به‌روزرسانی شد.'
            elif section == 'password':
                current_password = request.form.get('current_password', '')
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')
                if not current_password or not new_password or not confirm_password:
                    error = 'همه فیلدهای رمز عبور را پر کنید.'
                elif not check_password_hash(user.password_hash, current_password):
                    error = 'رمز عبور فعلی اشتباه است.'
                elif new_password != confirm_password:
                    error = 'رمز عبور جدید و تکرار آن یکسان نیست.'
                else:
                    user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    message = 'رمز عبور با موفقیت تغییر کرد.'

        return render_template('account.html', user=user, status_error=error, status_message=message)

    @app.route('/upgrade', methods=['POST'])
    def upgrade():
        uid = session.get('user_id')
        if not uid:
            return redirect(url_for('login'))
        user = User.query.get_or_404(uid)
        # In real app integrate payment; here we toggle premium for demo
        user.is_premium = True
        db.session.commit()
        return redirect(url_for('account'))

    @app.route("/search")
    def search():
        from flask import request
        query = request.args.get('q', '').strip()
        artist = Artist.query.first()
        
        if not artist:
            return render_template("setup_needed.html")
        
        results = []
        if query:
            tracks = Track.query.join(Album).filter(
                Album.artist_id == artist.id
            ).all()

            query_normalized = normalize_text(query)
            results = []

            scored_results = []
            for track in tracks:
                if not query_normalized:
                    continue

                title_score = search_match_score(query, track.title)
                album_score = search_match_score(query, track.album.title)
                best_score = max(title_score, album_score)
                if best_score >= 25:
                    scored_results.append((best_score, track))

            scored_results.sort(key=lambda item: (-item[0], item[1].title))
            results = [track for _, track in scored_results]
        
        return render_template("search_results.html", artist=artist, query=query, results=results)

    @app.route("/api/search")
    def api_search():
        query = request.args.get('q', '').strip()
        artist = Artist.query.first()
        
        if not artist or not query or len(query) < 2:
            return jsonify([])
        
        tracks = Track.query.join(Album).filter(
            Album.artist_id == artist.id
        ).all()

        query_normalized = normalize_text(query)
        results = []

        scored_results = []
        for track in tracks:
            title_score = search_match_score(query, track.title)
            album_score = search_match_score(query, track.album.title)
            best_score = max(title_score, album_score)
            if best_score >= 25:
                scored_results.append((best_score, {
                    'id': track.id,
                    'title': track.title,
                    'album': track.album.title,
                    'cover_url': track.cover_url,
                    'url': f"/track/{track.id}/{slugify_text(track.title)}"
                }))

        scored_results.sort(key=lambda item: (-item[0], item[1]['title']))
        return jsonify([item[1] for item in scored_results[:10]])

    @app.route("/genres")
    def genres_list():
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")

        def normalize_genres(genre_value):
            if not genre_value:
                return ["بدون سبک"]
            genres = [g.strip() for g in str(genre_value).split(",") if g.strip()]
            return genres or ["بدون سبک"]

        all_tracks = Track.query.join(Album).filter(Album.artist_id == artist.id).all()
        genre_map = {}
        for t in all_tracks:
            for g in normalize_genres(t.genre):
                genre_map.setdefault(g, []).append(t)

        # مرتب‌سازی ژانرها بر اساس تعداد ترک
        genres = sorted(genre_map.items(), key=lambda kv: len(kv[1]), reverse=True)
        return render_template("genres.html", artist=artist, genres=genres)

    @app.route("/genre/<genre_name>")
    def genre_detail(genre_name):
        artist = Artist.query.first()
        if not artist:
            return render_template("setup_needed.html")

        def normalize_genres(genre_value):
            if not genre_value:
                return ["بدون سبک"]
            genres = [g.strip() for g in str(genre_value).split(",") if g.strip()]
            return genres or ["بدون سبک"]

        all_tracks = Track.query.join(Album).filter(Album.artist_id == artist.id).all()
        tracks = [t for t in all_tracks if genre_name in normalize_genres(t.genre)]
        tracks = sorted(tracks, key=lambda t: t.total_views(), reverse=True)
        return render_template("genre_detail.html", artist=artist, genre_name=genre_name, tracks=tracks)

    @app.template_global()
    def release_label(track):
        return get_release_label(track)

    @app.template_filter("format_number")
    def format_number(value):
        if value is None:
            return "—"
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return value

    def to_persian_digits(value):
        if value is None:
            return ""
        translation = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        return str(value).translate(translation)

    def gregorian_to_jalali(gy, gm, gd):
        g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
        if gy > 1600:
            jy = 979
            gy -= 1600
        else:
            jy = 0
            gy -= 621
        if gm > 2:
            gy2 = gy + 1
        else:
            gy2 = gy
        days = 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1] - 80
        jy += 33 * (days // 12053)
        days %= 12053
        jy += 4 * (days // 1461)
        days %= 1461
        if days > 365:
            jy += (days - 1) // 365
            days = (days - 1) % 365
        if days < 186:
            jm = 1 + days // 31
            jd = 1 + days % 31
        else:
            days -= 186
            jm = 7 + days // 30
            jd = 1 + days % 30
        return jy, jm, jd

    @app.template_filter("format_date_short")
    def format_date_short(value):
        if not value:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime('%d %B %Y')
        return str(value)

    @app.template_filter("format_date_short_jalali")
    def format_date_short_jalali(value):
        if not value:
            return ""
        if hasattr(value, "strftime"):
            months = [
                "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
            ]
            jalali_year, jalali_month, jalali_day = gregorian_to_jalali(value.year, value.month, value.day)
            return f"{to_persian_digits(jalali_day)} {months[jalali_month - 1]} {to_persian_digits(jalali_year)}"
        return str(value)

    @app.template_filter("split")
    def split_filter(value, separator=","):
        if not value:
            return []
        return str(value).split(separator)

    @app.template_filter("trim")
    def trim_filter(value):
        if not value:
            return ""
        return str(value).strip()

def start_scheduler(app):
    """آپدیت خودکار ویوها هر روز ساعت ۳ بامداد"""

    scheduler = BackgroundScheduler(timezone="Asia/Tehran")
    scheduler.add_job(
        func=lambda: update_all_tracks(app),
        trigger="cron",
        hour=3,
        minute=0,
        id="daily_view_update",
        replace_existing=True,
    )
    scheduler.start()
    print("[scheduler] آپدیت روزانه ساعت ۳:۰۰ بامداد تنظیم شد.")
    return scheduler


app = create_app()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "update_views":
        update_all_tracks(app)
    else:
        start_scheduler(app)
        port = int(os.environ.get("PORT", 5000))
        app.run(debug=False, host="0.0.0.0", port=port)

# -*- coding: utf-8 -*-
"""
ارتباط با Spotify Web API (Client Credentials Flow) برای خوندن متادیتای
عمومی آرتیست — آلبوم‌ها، سینگل‌ها و ترک‌ها. این بخش اسکرپینگ نیست؛ از API
رسمی و رایگان اسپاتیفای استفاده می‌کند که برای داده‌های کاتالوگ (نه آمار
پخش لحظه‌ای) در دسترس است.

پیش‌نیاز: ساخت یک اپ رایگان در https://developer.spotify.com/dashboard
و تنظیم متغیرهای محیطی:
    export SPOTIFY_CLIENT_ID="..."
    export SPOTIFY_CLIENT_SECRET="..."
"""
import os
import re
import time
import base64
import requests

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

_token_cache = {"value": None, "expires_at": 0}


class SpotifyAPIError(Exception):
    pass


def _get_credentials():
    return os.environ.get("SPOTIFY_CLIENT_ID"), os.environ.get("SPOTIFY_CLIENT_SECRET")


def get_access_token():
    """دریافت توکن دسترسی؛ تا قبل از انقضا از حافظه موقت استفاده می‌شود."""
    now = time.time()
    if _token_cache["value"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["value"]

    client_id, client_secret = _get_credentials()
    if not client_id or not client_secret:
        raise SpotifyAPIError(
            "متغیرهای SPOTIFY_CLIENT_ID و SPOTIFY_CLIENT_SECRET تنظیم نشده‌اند. "
            "این مقادیر رایگان را از developer.spotify.com/dashboard بگیرید."
        )

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {auth_header}"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise SpotifyAPIError(f"دریافت توکن اسپاتیفای ناموفق بود: {e}")

    data = resp.json()
    _token_cache["value"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["value"]


def _auth_headers():
    return {"Authorization": f"Bearer {get_access_token()}"}


def extract_artist_id(url_or_id: str):
    """از روی لینک open.spotify.com/artist/xxxx یا خود آیدی، شناسه را استخراج می‌کند."""
    if not url_or_id:
        return None
    match = re.search(r"artist[/:]([a-zA-Z0-9]+)", url_or_id)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9]{15,30}", url_or_id.strip()):
        return url_or_id.strip()
    return None


def get_artist_info(artist_id: str) -> dict:
    try:
        resp = requests.get(f"{API_BASE}/artists/{artist_id}", headers=_auth_headers(), timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise SpotifyAPIError(f"دریافت اطلاعات آرتیست ناموفق بود: {e}")
    return resp.json()


def get_artist_albums(artist_id: str) -> list:
    """تمام آلبوم‌ها و سینگل‌های آرتیست را برمی‌گرداند (بدون تکرار هم‌نام)."""
    albums = []
    url = f"{API_BASE}/artists/{artist_id}/albums"
    params = {"include_groups": "album,single", "limit": 50, "market": "US"}

    while url:
        try:
            resp = requests.get(url, headers=_auth_headers(), params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise SpotifyAPIError(f"دریافت لیست آلبوم‌ها ناموفق بود: {e}")
        data = resp.json()
        albums.extend(data.get("items", []))
        url = data.get("next")
        params = None  # لینک 'next' خودش تمام پارامترها را داخل خود دارد

    # نسخه‌های دلوکس/منطقه‌ای هم‌نام را یکی در نظر می‌گیریم
    seen, unique_albums = set(), []
    for album in albums:
        key = album["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique_albums.append(album)
    return unique_albums


def get_album_tracks(album_id: str) -> list:
    tracks = []
    url = f"{API_BASE}/albums/{album_id}/tracks"
    params = {"limit": 50, "market": "US"}

    while url:
        try:
            resp = requests.get(url, headers=_auth_headers(), params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise SpotifyAPIError(f"دریافت ترک‌های آلبوم ناموفق بود: {e}")
        data = resp.json()
        tracks.extend(data.get("items", []))
        url = data.get("next")
        params = None
    return tracks


def format_duration(duration_ms: int) -> str:
    seconds = int(duration_ms / 1000)
    return f"{seconds // 60}:{seconds % 60:02d}"

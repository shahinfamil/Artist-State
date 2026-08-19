# -*- coding: utf-8 -*-
"""
پنل مدیریت سایت — افزودن/ویرایش/حذف آرتیست، آلبوم و آهنگ از طریق فرم.
آدرس ورود: /admin/login
"""
import json
import os
import re
import sys
import uuid
from datetime import datetime
from functools import wraps
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, Artist, ArtistWikipediaData, Album, Track, User, ViewStat, SiteMedia, Lyricist

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

LOCAL_SPOTIFY_SCRAPER_PATH = os.path.join(os.path.dirname(__file__), "myenv", "Lib", "site-packages")


def import_spotify_scraper():
    try:
        import spotify_scraper
        return spotify_scraper
    except ImportError:
        if os.path.isdir(LOCAL_SPOTIFY_SCRAPER_PATH) and LOCAL_SPOTIFY_SCRAPER_PATH not in sys.path:
            sys.path.insert(0, LOCAL_SPOTIFY_SCRAPER_PATH)
            try:
                import spotify_scraper
                return spotify_scraper
            except ImportError:
                pass
        raise

# لیست ژانرهای پیشنهادی برای نمایش به‌صورت دکمه سریع در فرم (کاربر هرچیزی هم می‌تواند تایپ کند)
SUGGESTED_GENRES = ["راک", "هیپ‌هاپ و رپ", "الکترونیک","متال"]

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "avif", "svg"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "ogg", "mov", "m4v"}
MEDIA_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")

# نام کاربری و پسورد پنل مدیریت از طریق متغیر محیطی قابل تنظیم است.
# برای تغییر پسورد، متغیر محیطی ADMIN_PASSWORD را قبل از اجرای سایت ست کنید:
#   export ADMIN_USERNAME="admin"
#   export ADMIN_PASSWORD="یک-پسورد-قوی"
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))

SPOTIFY_CLIENT_ID="475850c9658d4a95ad793a06484b1b80"
SPOTIFY_CLIENT_SECRET="e2954547913d42d895cc6a74af133a26"
RAPIDAPI_SPOTIFY_KEY = "6079d5b09dmsh11e7118c5c1323fp1fbcafjsn96c1d54d5bee"
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return view_func(*args, **kwargs)
    return wrapper


def save_uploaded_file(file_storage, allowed_extensions, subfolder, file_type_label):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed_extensions:
        flash(f"فرمت فایل {file_type_label} پشتیبانی نمی‌شود. فرمت‌های معتبر: {', '.join(sorted(allowed_extensions))}", "error")
        return None

    upload_dir = os.path.join(MEDIA_UPLOAD_DIR, subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(upload_dir, secure_filename(filename)))
    return url_for("static", filename=f"uploads/{subfolder}/{filename}")


def save_image_file(file_storage):
    return save_uploaded_file(file_storage, ALLOWED_IMAGE_EXTENSIONS, "images", "تصویر")


def get_social_refresh_config(platform):
    normalized_platform = (platform or "instagram").strip().lower()
    allowed_platforms = {
        "instagram": ("instagram_followers", "instagram"),
        "youtube": ("youtube_subscribers", "youtube"),
        "facebook": ("facebook_followers", "facebook"),
        "spotify": ("spotify_followers", "spotify"),
        "soundcloud": ("soundcloud_followers", "soundcloud"),
        "x": ("x_followers", "x"),
        "tiktok": ("tiktok_followers", "tiktok"),
    }
    return allowed_platforms.get(normalized_platform, (None, None))


def format_duration_ms(duration_ms):
    if not duration_ms:
        return ""
    total_seconds = int(duration_ms) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def get_env_value(*names):
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def summarize_view_stats(stats):
    total_views = 0
    platform_totals = {}
    track_totals = {}
    latest_by_pair = {}

    for stat in stats:
        platform = getattr(stat, "platform", "unknown") or "unknown"
        track = getattr(stat, "track", None)
        track_name = getattr(track, "title", None) or "بدون عنوان"
        pair_key = (track_name, platform)
        views = int(getattr(stat, "views", 0) or 0)

        current_fetched_at = getattr(stat, "fetched_at", None)
        if current_fetched_at is None:
            current_fetched_at = datetime.min

        existing = latest_by_pair.get(pair_key)
        if existing is None or current_fetched_at > existing["fetched_at"]:
            latest_by_pair[pair_key] = {
                "views": views,
                "platform": platform,
                "track_name": track_name,
                "fetched_at": current_fetched_at,
            }

    for pair_data in latest_by_pair.values():
        views = pair_data["views"]
        total_views += views
        platform = pair_data["platform"]
        track_name = pair_data["track_name"]

        platform_totals[platform] = platform_totals.get(platform, 0) + views
        track_totals[track_name] = track_totals.get(track_name, 0) + views

    return {
        "total_views": total_views,
        "platform_totals": platform_totals,
        "track_totals": track_totals,
    }


def parse_admin_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_release_date(form):
    if hasattr(form, "get"):
        release_date_value = (form.get("release_date") or "").strip()
        if release_date_value:
            return parse_admin_date(release_date_value)

        day = (form.get("release_day") or "").strip()
        month = (form.get("release_month") or "").strip()
        year = (form.get("release_year") or "").strip()
        if not (day and month and year):
            return None

        try:
            return datetime(int(year), int(month), int(day)).date()
        except ValueError:
            return None

    return None


def parse_album_release_date(form):
    return parse_release_date(form)


def get_spotify_access_token():
    client_id = get_env_value("2eb8b6c29bfc4d02ba3d0f1ae293a317", "spotify_client_id")
    client_secret = get_env_value("fcd46d3b17df4d788b744520486dcccf", "spotify_client_secret")
    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set and the server must be restarted after changing them")

    data = urllib_parse.urlencode({
        "grant_type": "client_credentials",
    }).encode("utf-8")
    req = urllib_request.Request(
        "https://accounts.spotify.com/api/token",
        data=data,
        headers={
            "Authorization": "Basic " + __import__("base64").b64encode(f"{client_id}:{client_secret}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib_request.urlopen(req, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("access_token")


def spotify_api_request(path, params=None, token=None):
    token = token or get_spotify_access_token()
    query = urllib_parse.urlencode(params or {})
    url = f"https://api.spotify.com/v1{path}"
    if query:
        url = f"{url}?{query}"
    req = urllib_request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib_request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def search_spotify_albums(query, limit=8):
    payload = spotify_api_request("/search", {"q": query, "type": "album", "limit": limit, "market": "IR"})
    return payload.get("albums", {}).get("items", [])


def get_spotify_album(album_id):
    return spotify_api_request(f"/albums/{album_id}", {"market": "IR"})


def get_youtube_video_url(query):
    api_key = get_env_value("AIzaSyC9GpfkEUWFWKRePbUBeEfaVCEmgQSp4Mo", "youtube_api_key")
    if not api_key:
        return None
    encoded_query = urllib_parse.quote(query)
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=1&q={encoded_query}&key={api_key}"
    req = urllib_request.Request(url)
    with urllib_request.urlopen(req, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    items = payload.get("items") or []
    if not items:
        return None
    video_id = items[0].get("id", {}).get("videoId")
    return f"https://www.youtube.com/watch?v={video_id}" if video_id else None


def get_soundcloud_track_url(query):
    client_id = get_env_value("E5H8PFjUqVaQIsiGCPhSA68vs1Y2", "soundcloud_client_id")
    if not client_id:
        return None
    encoded_query = urllib_parse.quote(query)
    url = f"https://api.soundcloud.com/tracks?client_id={client_id}&q={encoded_query}&limit=1"
    req = urllib_request.Request(url)
    with urllib_request.urlopen(req, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload:
        return None
    return payload[0].get("permalink_url") if payload else None


def get_track_external_links(track_name, artist_names, album_name):
    links = {"youtube_url": None, "soundcloud_url": None}
    primary_artist = artist_names[0] if artist_names else ""
    search_query = f"{primary_artist} {track_name}"
    if album_name:
        search_query = f"{search_query} {album_name}"

    try:
        links["youtube_url"] = get_youtube_video_url(search_query)
    except Exception:
        links["youtube_url"] = None

    try:
        links["soundcloud_url"] = get_soundcloud_track_url(search_query)
    except Exception:
        links["soundcloud_url"] = None

    return links


def is_safe_redirect_url(target: str) -> bool:
    if not target:
        return False
    parsed = urllib_parse.urlparse(target)
    if parsed.netloc and parsed.netloc != request.host:
        return False
    return parsed.scheme in ("http", "https", "") and (parsed.path.startswith("/") or parsed.path == "")


VALID_ADMIN_TABS = {"overview", "analytics", "users", "content", "tools"}


def get_redirect_tab() -> str | None:
    tab = (request.form.get("next_tab") or request.args.get("next_tab") or "").strip()
    return tab if tab in VALID_ADMIN_TABS else None


def append_url_anchor(url: str, anchor: str | None) -> str:
    if not anchor:
        return url
    parsed = urllib_parse.urlsplit(url)
    if parsed.fragment == anchor:
        return url
    return urllib_parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, anchor))


def redirect_back(default_endpoint="admin.dashboard", **values):
    explicit_next = request.form.get("next") or request.args.get("next")
    tab = get_redirect_tab()
    if explicit_next and is_safe_redirect_url(explicit_next):
        target = append_url_anchor(explicit_next, tab)
        return redirect(target)
    if tab:
        return redirect(url_for(get_dashboard_route_for_tab(tab), **values))
    if request.referrer and is_safe_redirect_url(request.referrer):
        return redirect(request.referrer)
    return redirect(url_for(default_endpoint, **values))


def get_dashboard_route_for_tab(tab: str | None) -> str:
    if tab == "analytics":
        return "admin.dashboard_analytics"
    if tab == "users":
        return "admin.dashboard_users"
    if tab == "content":
        return "admin.dashboard_content"
    return "admin.dashboard"


def redirect_to_content_section():
    return redirect(url_for("admin.dashboard_content"))


def get_admin_dashboard_base_context():
    artist = Artist.query.first()
    if artist:
        albums = (
            Album.query
            .order_by(Album.release_date.isnot(None).desc(), Album.release_date.desc(), Album.release_year.desc(), Album.id.desc())
            .all()
        )
    else:
        albums = []
    for album in albums:
        album.tracks = sorted(album.tracks, key=lambda track: (track.sort_order, track.title.lower(), track.id))
    users = User.query.order_by(User.created_at.desc()).all()
    tracks = Track.query.order_by(Track.title.asc()).all()
    return artist, albums, users, tracks


def group_albums_for_display(albums):
    singles = []
    eps = []
    full_albums = []

    for album in albums:
        release_type = getattr(album, "release_type", None)
        if release_type == "single":
            singles.append(album)
            continue
        if release_type == "ep":
            eps.append(album)
            continue
        if release_type == "album":
            full_albums.append(album)
            continue

        track_count = sum(1 for t in (album.tracks or []) if getattr(t, "is_active", True))
        if track_count == 1:
            singles.append(album)
        elif 2 <= track_count <= 4:
            eps.append(album)
        elif track_count >= 5:
            full_albums.append(album)

    return {
        "singles": singles,
        "eps": eps,
        "full_albums": full_albums,
    }


def build_analytics_context():
    platform_filter = (request.args.get("platform") or "").strip().lower()
    track_filter = request.args.get("track_id")
    date_from = parse_admin_date(request.args.get("date_from"))
    date_to = parse_admin_date(request.args.get("date_to"))

    analytics_query = ViewStat.query.join(Track)
    if platform_filter in {"spotify", "youtube", "soundcloud"}:
        analytics_query = analytics_query.filter(ViewStat.platform == platform_filter)
    if track_filter:
        analytics_query = analytics_query.filter(Track.id == int(track_filter))

    min_fetched_at = analytics_query.with_entities(db.func.min(ViewStat.fetched_at)).scalar()
    max_fetched_at = analytics_query.with_entities(db.func.max(ViewStat.fetched_at)).scalar()

    if min_fetched_at:
        min_date = min_fetched_at.date() if isinstance(min_fetched_at, datetime) else min_fetched_at
    else:
        min_date = None

    if max_fetched_at:
        max_date = max_fetched_at.date() if isinstance(max_fetched_at, datetime) else max_fetched_at
    else:
        max_date = None

    if date_from and min_date and date_from < min_date:
        date_from = min_date
    if date_to and max_date and date_to > max_date:
        date_to = max_date

    if date_from:
        analytics_query = analytics_query.filter(ViewStat.fetched_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        analytics_query = analytics_query.filter(ViewStat.fetched_at <= datetime.combine(date_to, datetime.max.time()))

    analytics_rows = analytics_query.order_by(ViewStat.fetched_at.desc()).all()
    analytics_summary = summarize_view_stats([
        type("AnalyticsStat", (), {"platform": row.platform, "views": row.views, "track": row.track})
        for row in analytics_rows
    ])

    grouped_rows = {}
    for row in analytics_rows:
        key = (row.track.title, row.platform)
        current_fetched_at = getattr(row, "fetched_at", None)
        if current_fetched_at is None:
            current_fetched_at = datetime.min

        existing = grouped_rows.get(key)
        if existing is None or current_fetched_at > existing["fetched_at"]:
            grouped_rows[key] = {
                "views": row.views or 0,
                "fetched_at": current_fetched_at,
            }

    analytics_table = [
        {
            "track_title": track_title,
            "platform": platform,
            "views": item_data["views"],
        }
        for (track_title, platform), item_data in sorted(grouped_rows.items(), key=lambda item: (-item[1]["views"], item[0][0], item[0][1]))
    ]

    tracks = Track.query.order_by(Track.title.asc()).all()
    selected_track_title = None
    if track_filter:
        selected_track = Track.query.get(int(track_filter))
        if selected_track:
            selected_track_title = selected_track.title

    analytics_context = {
        "analytics_summary": analytics_summary,
        "analytics_table": analytics_table,
        "analytics_rows": analytics_rows,
        "analytics_platform": platform_filter,
        "analytics_track_id": track_filter,
        "analytics_date_from": date_from.strftime("%Y-%m-%d") if date_from else "",
        "analytics_date_to": date_to.strftime("%Y-%m-%d") if date_to else "",
        "analytics_date_min": min_date.strftime("%Y-%m-%d") if min_date else "",
        "analytics_date_max": max_date.strftime("%Y-%m-%d") if max_date else "",
        "tracks": tracks,
        "selected_track_title": selected_track_title,
    }

    if request.args.get("partial") == "1":
        return analytics_context, render_template("admin/partials/analytics_panel.html", **analytics_context)

    return analytics_context, None


def build_dashboard_stats(tracks):
    lyricist_stats = []
    try:
        # یک ترک می‌تواند چند ترانه‌سرا داشته باشد؛ در این حالت هر نفر به‌صورت اشتراکی
        # برای همان ترک اعتبار می‌گیرد، اما متن ترانه و آهنگ‌ها به‌صورت یک‌دسته مشترک نگه داشته می‌شوند.
        lyricist_stats = [
            {"name": name, "count": int(count or 0)}
            for name, count in get_lyricist_track_counts()
        ]
    except Exception:
        lyricist_stats = []

    lyricist_stats = sorted(lyricist_stats, key=lambda item: (-item["count"], item["name"]))

    genre_map = {}
    platform_counts = {"spotify": 0, "youtube": 0, "soundcloud": 0}
    music_video_tracks = 0
    linked_tracks = 0

    for track in tracks:
        genres = [g.strip() for g in (track.genre or "").split(",") if g.strip()]
        if not genres:
            genres = ["بدون سبک"]
        for genre in genres:
            genre_map[genre] = genre_map.get(genre, 0) + 1

        if track.music_video_url:
            music_video_tracks += 1
        if track.spotify_url:
            platform_counts["spotify"] += 1
        if track.youtube_url or track.youtube_url_secondary:
            platform_counts["youtube"] += 1
        if track.soundcloud_url:
            platform_counts["soundcloud"] += 1
        if track.spotify_url or track.youtube_url or track.youtube_url_secondary or track.soundcloud_url:
            linked_tracks += 1

    total_tracks = len(tracks)
    genre_stats = []
    for genre, count in sorted(genre_map.items(), key=lambda item: item[1], reverse=True):
        percent = int(round((count / total_tracks) * 100)) if total_tracks else 0
        genre_stats.append({"genre": genre, "count": count, "percent": percent})

    year_map = {}
    for track in tracks:
        year = None
        if getattr(track, "release_date", None):
            try:
                year = track.release_date.year
            except Exception:
                year = None
        if year is None and getattr(track.album, "release_year", None):
            year = track.album.release_year
        if year is None:
            continue
        year_map[year] = year_map.get(year, 0) + 1

    year_stats = [
        {"year": year, "count": count}
        for year, count in sorted(year_map.items(), key=lambda item: (-item[1], -item[0]))
    ]

    platform_stats = [
        {"label": "اسپاتیفای", "count": platform_counts["spotify"], "percent": int(round((platform_counts["spotify"] / total_tracks) * 100)) if total_tracks else 0, "color": "spotify"},
        {"label": "یوتیوب", "count": platform_counts["youtube"], "percent": int(round((platform_counts["youtube"] / total_tracks) * 100)) if total_tracks else 0, "color": "youtube"},
        {"label": "ساندکلود", "count": platform_counts["soundcloud"], "percent": int(round((platform_counts["soundcloud"] / total_tracks) * 100)) if total_tracks else 0, "color": "soundcloud"},
    ]

    release_type_counts = {}
    for track in tracks:
        release_type = None
        if track.album and track.album.release_type:
            release_type = track.album.release_type
        elif track.album:
            album_tracks = len(track.album.tracks)
            if album_tracks == 1:
                release_type = "single"
            elif 2 <= album_tracks <= 4:
                release_type = "ep"
            elif album_tracks > 4:
                release_type = "album"
        release_type = release_type or "unknown"
        release_type_counts[release_type] = release_type_counts.get(release_type, 0) + 1

    release_type_labels = {
        "single": "سینگل",
        "ep": "اپ",
        "album": "آلبوم",
        "unknown": "نامشخص",
    }
    release_type_colors = {
        "single": "#f59e0b",
        "ep": "#0ea5e9",
        "album": "#7c3aed",
        "unknown": "#64748b",
    }
    release_type_stats = []
    for key, count in sorted(release_type_counts.items(), key=lambda item: item[1], reverse=True):
        percent = int(round((count / total_tracks) * 100)) if total_tracks else 0
        release_type_stats.append({
            "label": release_type_labels.get(key, key.title()),
            "count": count,
            "percent": percent,
            "color": release_type_colors.get(key, "#64748b"),
        })

    active_tracks = sum(1 for track in tracks if track.is_active)
    solo_tracks = sum(1 for track in tracks if (not track.featuring or not track.featuring.strip()) and not track.is_the_shah)
    the_shah_tracks = sum(1 for track in tracks if track.is_the_shah)
    the_shah_solo = sum(1 for track in tracks if track.is_the_shah and (not track.featuring or not track.featuring.strip()))
    the_shah_with_featured = sum(1 for track in tracks if track.is_the_shah and track.featuring and track.featuring.strip())
    featured_tracks = sum(1 for track in tracks if track.featuring and track.featuring.strip())
    collaboration_tracks = featured_tracks
    no_collaboration_tracks = solo_tracks + the_shah_solo
    no_collaboration_tracks_percent = int(round((no_collaboration_tracks / total_tracks) * 100)) if total_tracks else 0
    collaboration_percent = int(round((collaboration_tracks / total_tracks) * 100)) if total_tracks else 0
    the_shah_percent = int(round((the_shah_tracks / no_collaboration_tracks) * 100)) if no_collaboration_tracks else 0
    the_shah_chart_percent = int(round((the_shah_tracks / total_tracks) * 100)) if total_tracks else 0
    the_shah_chart_solo_percent = int(round((the_shah_solo / total_tracks) * 100)) if total_tracks else 0
    featured_artist_counts = {}
    for track in tracks:
        if not track.featuring or not track.featuring.strip():
            continue
        for artist_name in [name.strip() for name in track.featuring.split(",") if name.strip()]:
            featured_artist_counts[artist_name] = featured_artist_counts.get(artist_name, 0) + 1

    featured_artist_breakdown = []
    artist_palette = ["#8b5cf6", "#22c55e", "#f97316", "#06b6d4", "#f43f5e", "#eab308"]
    for index, (artist_name, count) in enumerate(
        sorted(featured_artist_counts.items(), key=lambda item: (-item[1], item[0]))
    ):
        featured_artist_breakdown.append({
            "name": artist_name,
            "count": count,
            "percent": int(round((count / featured_tracks) * 100)) if featured_tracks else 0,
            "color": artist_palette[index % len(artist_palette)],
        })

    cursor_percent = 0
    for item in featured_artist_breakdown:
        item["start"] = cursor_percent
        item["end"] = cursor_percent + item["percent"]
        cursor_percent = item["end"]

    featured_artist_gradient = ", ".join(
        f"{item['color']} {item['start']}% {item['end']}%"
        for item in featured_artist_breakdown
    )

    collaboration_breakdown = [
        {
            "name": "بدون همکاری",
            "count": no_collaboration_tracks,
            "percent": int(round((no_collaboration_tracks / total_tracks) * 100)) if total_tracks else 0,
            "color": "#ff5a5f",
        },
        {
            "name": "با همکاری",
            "count": collaboration_tracks,
            "percent": int(round((collaboration_tracks / total_tracks) * 100)) if total_tracks else 0,
            "color": "#8b5cf6",
        },
    ]

    circumference = 615.75
    collaboration_segments = []
    accumulated = 0
    for item in collaboration_breakdown:
        dash = (item["count"] / total_tracks) * circumference if total_tracks else 0
        collaboration_segments.append({
            "label": item["name"],
            "count": item["count"],
            "percent": item["percent"],
            "color": item["color"],
            "dash": dash,
            "offset": accumulated,
        })
        accumulated += dash

    linked_stats = {
        "count": linked_tracks,
        "percent": int(round((linked_tracks / total_tracks) * 100)) if total_tracks else 0,
    }

    return {
        "genre_stats": genre_stats,
        "year_stats": year_stats,
        "platform_stats": platform_stats,
        "release_type_stats": release_type_stats,
        "lyricist_stats": lyricist_stats,
        "music_video_stats": {
            "has_mv": music_video_tracks,
            "no_mv": total_tracks - music_video_tracks,
            "percent": int(round((music_video_tracks / total_tracks) * 100)) if total_tracks else 0,
        },
        "active_stats": {
            "active": active_tracks,
            "inactive": total_tracks - active_tracks,
            "percent": int(round((active_tracks / total_tracks) * 100)) if total_tracks else 0,
        },
        "featured_stats": {
            "featured": featured_tracks,
            "solo": solo_tracks,
            "the_shah": the_shah_solo,
            "the_shah_solo": the_shah_solo,
            "the_shah_with_featured": the_shah_with_featured,
            "the_shah_total": the_shah_tracks,
            "no_collaboration": no_collaboration_tracks,
            "no_collaboration_percent": no_collaboration_tracks_percent,
            "the_shah_percent": the_shah_percent,
            "the_shah_chart_percent": the_shah_chart_percent,
            "the_shah_chart_solo_percent": the_shah_chart_solo_percent,
            "collaboration_count": collaboration_tracks,
            "collaboration_percent": collaboration_percent,
            "percent": collaboration_percent,
        },
        "featured_artist_breakdown": featured_artist_breakdown,
        "featured_artist_gradient": featured_artist_gradient,
        "linked_stats": linked_stats,
        "collaboration_breakdown": collaboration_breakdown,
        "collaboration_segments": collaboration_segments,
        "linked_tracks": linked_tracks,
        "total_tracks": total_tracks,
    }


def import_spotify_album_to_site(album_id, artist_obj):
    album_data = get_spotify_album(album_id)
    if not album_data:
        raise ValueError("No album data returned")

    existing = Album.query.filter_by(artist_id=artist_obj.id, title=album_data.get("name", "").strip()).first()
    if existing:
        return None, "existing"

    album_artists = [artist.get("name", "") for artist in album_data.get("artists", []) if artist.get("name")]
    album = Album(
        title=album_data.get("name", "").strip(),
        cover_url=(album_data.get("images") or [{}])[0].get("url") if (album_data.get("images") or [{}]) else None,
        release_year=(album_data.get("release_date") or "")[0:4] if album_data.get("release_date") else None,
        artist_id=artist_obj.id,
    )
    db.session.add(album)
    db.session.flush()

    album_genres = album_data.get("genres") or []
    album_genre_text = ", ".join(album_genres) if album_genres else ""

    for track_data in album_data.get("tracks", {}).get("items", []):
        track_artists = [artist.get("name", "") for artist in track_data.get("artists", []) if artist.get("name")]
        track_title = track_data.get("name", "").strip()
        external_links = get_track_external_links(track_title, track_artists, album_data.get("name", ""))
        track = Track(
            title=track_title,
            cover_url=album.cover_url,
            duration=format_duration_ms(track_data.get("duration_ms")),
            album_id=album.id,
            spotify_url=track_data.get("external_urls", {}).get("spotify"),
            youtube_url=external_links.get("youtube_url") or "",
            soundcloud_url=external_links.get("soundcloud_url") or "",
            featuring=", ".join(track_artists[1:]) if len(track_artists) > 1 else "",
            genre=album_genre_text,
        )
        db.session.add(track)

    db.session.commit()
    return album, "imported"


# ---------------------------------------------------------------- ورود/خروج
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        flash("نام کاربری یا رمز عبور اشتباه است.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/tracks/reorder", methods=["POST"])
@login_required
def reorder_tracks():
    payload = request.get_json(silent=True) or {}
    track_id = payload.get("track_id")
    target_id = payload.get("target_id")
    if not track_id or not target_id:
        return jsonify({"success": False, "message": "اطلاعات ناقص است."}), 400

    track = Track.query.get(track_id)
    target = Track.query.get(target_id)
    if not track or not target:
        return jsonify({"success": False, "message": "آهنگ پیدا نشد."}), 404

    if track.album_id != target.album_id:
        return jsonify({"success": False, "message": "آهنگ‌ها باید در یک آلبوم باشند."}), 400

    ordered_tracks = Track.query.filter_by(album_id=track.album_id).order_by(Track.sort_order.asc(), Track.title.asc(), Track.id.asc()).all()
    if track not in ordered_tracks or target not in ordered_tracks:
        return jsonify({"success": False, "message": "ترتیب قابل اعمال نیست."}), 400

    ordered_tracks = [item for item in ordered_tracks if item.id != track.id]
    target_index = next((index for index, item in enumerate(ordered_tracks) if item.id == target.id), None)
    if target_index is None:
        ordered_tracks.append(track)
    else:
        ordered_tracks.insert(target_index, track)

    for index, item in enumerate(ordered_tracks):
        item.sort_order = index

    db.session.commit()
    return jsonify({"success": True})


@admin_bp.route('/track/<int:track_id>/toggle_active', methods=['POST'])
@login_required
def track_toggle_active(track_id):
    track = Track.query.get_or_404(track_id)
    payload = request.get_json(silent=True)
    if payload and 'is_active' in payload:
        track.is_active = bool(payload.get('is_active'))
    else:
        track.is_active = not bool(track.is_active)
    db.session.commit()
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'is_active': bool(track.is_active)})
    return redirect_back()


# ---------------------------------------------------------------- داشبورد
@admin_bp.route("/")
@login_required
def dashboard():
    artist, albums, users, tracks = get_admin_dashboard_base_context()
    dashboard_stats = build_dashboard_stats(tracks)
    grouped_albums = group_albums_for_display(albums)
    return render_template(
        "admin/dashboard.html",
        artist=artist,
        albums=albums,
        users=users,
        tracks=tracks,
        dashboard_stats=dashboard_stats,
        singles=grouped_albums["singles"],
        eps=grouped_albums["eps"],
        full_albums=grouped_albums["full_albums"],
    )


@admin_bp.route("/view-history/cleanup", methods=["POST"])
@login_required
def cleanup_all_view_history():
    today_start = datetime.combine(datetime.now().date(), datetime.min.time())
    deleted_count = ViewStat.query.filter(ViewStat.fetched_at < today_start).delete(synchronize_session=False)
    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "deleted_count": deleted_count})

    flash(f"تاریخچه قدیمی حذف شد: {deleted_count} رکورد", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/analytics")
@login_required
def dashboard_analytics():
    artist, albums, users, tracks = get_admin_dashboard_base_context()
    analytics_context, partial_template = build_analytics_context()

    if partial_template is not None:
        return partial_template

    context = {
        "artist": artist,
        "albums": albums,
        "users": users,
        "tracks": tracks,
    }
    context.update(analytics_context)

    return render_template("admin/dashboard_analytics.html", **context)


@admin_bp.route("/users")
@login_required
def dashboard_users():
    artist, albums, users, tracks = get_admin_dashboard_base_context()
    return render_template(
        "admin/dashboard_users.html",
        artist=artist,
        albums=albums,
        users=users,
        tracks=tracks,
    )


@admin_bp.route("/content")
@login_required
def dashboard_content():
    artist, albums, users, tracks = get_admin_dashboard_base_context()
    return render_template(
        "admin/dashboard_content.html",
        artist=artist,
        albums=albums,
        users=users,
        tracks=tracks,
    )


@admin_bp.route("/user/<int:user_id>/toggle-premium", methods=["POST"])
@login_required
def user_toggle_premium(user_id):
    user = User.query.get_or_404(user_id)
    user.is_premium = not user.is_premium
    db.session.commit()
    flash(f"حساب {user.email} {'پریمیوم شد' if user.is_premium else 'عادی شد'}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/user/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
def user_toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f"دسترسی ادمین برای {user.email} {'فعال شد' if user.is_admin else 'غیرفعال شد'}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/user/<int:user_id>/delete", methods=["POST"])
@login_required
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"کاربر {user.email} حذف شد.", "success")
    return redirect(url_for("admin.dashboard"))


# ---------------------------------------------------------------- آرتیست
@admin_bp.route("/wikipedia-info", methods=["GET", "POST"])
@login_required
def wikipedia_info_page():
    artist = Artist.query.first()
    if not artist:
        return redirect(url_for("admin.artist_form"))

    if request.method == "POST":
        wikipedia_record = artist.wikipedia_data
        if wikipedia_record is None:
            wikipedia_record = ArtistWikipediaData(artist=artist)
            db.session.add(wikipedia_record)
        wikipedia_record.title = request.form.get("wikipedia_title", "").strip()
        wikipedia_record.image_url = request.form.get("wikipedia_image_url", "").strip()
        wikipedia_record.timeline_section = request.form.get("wikipedia_timeline_section", "").strip()

        def parse_int_field(field_name):
            value = request.form.get(field_name, "").strip()
            try:
                return int(value) if value != "" else None
            except ValueError:
                return None

        wikipedia_record.instagram_followers = parse_int_field("instagram_followers")
        wikipedia_record.youtube_subscribers = parse_int_field("youtube_subscribers")
        wikipedia_record.facebook_followers = parse_int_field("facebook_followers")
        wikipedia_record.spotify_followers = parse_int_field("spotify_followers")
        wikipedia_record.soundcloud_followers = parse_int_field("soundcloud_followers")
        wikipedia_record.x_followers = parse_int_field("x_followers")

        infobox_keys = request.form.getlist("infobox_key[]")
        infobox_values = request.form.getlist("infobox_value[]")
        infobox_items = []
        for key, value in zip(infobox_keys, infobox_values):
            key = key.strip()
            value = value.strip()
            if key or value:
                infobox_items.append({"key": key, "value": value})

        wikipedia_record.infobox_json = json.dumps(infobox_items, ensure_ascii=False)
        db.session.add(wikipedia_record)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                success=True,
                message="اطلاعات ویکی‌پدیا ذخیره شد.",
                title=wikipedia_record.title,
                image_url=wikipedia_record.image_url,
                instagram_followers=wikipedia_record.instagram_followers,
                youtube_subscribers=wikipedia_record.youtube_subscribers,
                facebook_followers=wikipedia_record.facebook_followers,
                spotify_followers=wikipedia_record.spotify_followers,
                soundcloud_followers=wikipedia_record.soundcloud_followers,
                x_followers=wikipedia_record.x_followers,
                timeline_section=wikipedia_record.timeline_section,
                infobox=json.loads(wikipedia_record.infobox_json or "[]"),
            )
        flash("اطلاعات ویکی‌پدیا ذخیره شد.", "success")
        return redirect(url_for("admin.wikipedia_info_page"))

    wikipedia_record = artist.wikipedia_data or ArtistWikipediaData()
    infobox_items = []
    if wikipedia_record:
        if wikipedia_record.infobox_json:
            try:
                infobox_items = json.loads(wikipedia_record.infobox_json)
            except (TypeError, ValueError):
                infobox_items = []

    return render_template(
        "admin/wikipedia_info.html",
        artist=artist,
        wikipedia_record=wikipedia_record,
        infobox_items=infobox_items,
    )


@admin_bp.route("/wikipedia-info/upload-media", methods=["POST"])
@login_required
def upload_wikipedia_media():
    return _handle_media_upload()


@admin_bp.route("/upload-media", methods=["POST"])
@login_required
def upload_media():
    return _handle_media_upload()


def _handle_media_upload():
    media_file = request.files.get("upload") or request.files.get("file")
    media_type = request.form.get("media_type", "image").strip().lower()
    if not media_file or not media_file.filename:
        return jsonify(success=False, message="هیچ فایلی آپلود نشد."), 400

    allowed_extensions = ALLOWED_IMAGE_EXTENSIONS if media_type == "image" else ALLOWED_VIDEO_EXTENSIONS
    subfolder = "images" if media_type == "image" else "videos"
    url = save_uploaded_file(media_file, allowed_extensions, subfolder, media_type)
    if not url:
        return jsonify(success=False, message=f"آپلود {media_type} ناموفق بود."), 400

    media_record = SiteMedia(type=media_type, url=url, label=media_file.filename)
    db.session.add(media_record)
    db.session.commit()

    return jsonify(
        success=True,
        uploaded=1,
        url=url,
        media_id=media_record.id,
        message=f"{media_type.title()} با موفقیت آپلود شد.",
    )


@admin_bp.route("/wikipedia-info/refresh-social", methods=["POST"])
@login_required
def refresh_wikipedia_social_counts():
    artist = Artist.query.first()
    if not artist:
        return jsonify(success=False, message="آرتیستی برای به‌روزرسانی پیدا نشد."), 404

    from app import scrape_single_social_count

    wikipedia_record = artist.wikipedia_data
    if wikipedia_record is None:
        wikipedia_record = ArtistWikipediaData(artist=artist)
        db.session.add(wikipedia_record)
    now = datetime.now()

    payload = request.get_json(silent=True) or {}
    field_name, platform_key = get_social_refresh_config(payload.get("platform"))
    if not field_name or not platform_key:
            return jsonify(success=False, message="پلتفرم نامعتبر است.", extracted=[], failed=[], instagram_followers=wikipedia_record.instagram_followers, youtube_subscribers=wikipedia_record.youtube_subscribers, facebook_followers=wikipedia_record.facebook_followers, spotify_followers=wikipedia_record.spotify_followers, soundcloud_followers=wikipedia_record.soundcloud_followers, x_followers=wikipedia_record.x_followers, tiktok_followers=getattr(wikipedia_record, 'tiktok_followers', None), updated_at=None), 400
    count = None
    try:
        count = scrape_single_social_count(artist, platform_key)
    except Exception:
        count = None

    extracted = []
    failed = []
    updated = False

    if count is None:
        fallback_count = getattr(wikipedia_record, field_name, None)
        if fallback_count is not None:
            count = fallback_count
            updated = True
            extracted.append(field_name)
        else:
            failed.append(field_name)
    else:
        setattr(wikipedia_record, field_name, count)
        wikipedia_record.social_counts_updated_at = now
        db.session.add(wikipedia_record)
        db.session.commit()
        updated = True
        extracted.append(field_name)

    if updated:
        if count is None:
            count = getattr(wikipedia_record, field_name, None)
        setattr(wikipedia_record, field_name, count)
        wikipedia_record.social_counts_updated_at = now
        db.session.add(wikipedia_record)
        db.session.commit()
        return jsonify(
            success=True,
            message=f"بروزرسانی {platform_key} با مقدار فعلی انجام شد.",
            extracted=extracted,
            failed=failed,
            instagram_followers=wikipedia_record.instagram_followers,
            youtube_subscribers=wikipedia_record.youtube_subscribers,
            facebook_followers=wikipedia_record.facebook_followers,
            spotify_followers=wikipedia_record.spotify_followers,
            soundcloud_followers=wikipedia_record.soundcloud_followers,
            x_followers=wikipedia_record.x_followers,
            tiktok_followers=getattr(wikipedia_record, 'tiktok_followers', None),
            updated_at=wikipedia_record.social_counts_updated_at.isoformat() if wikipedia_record.social_counts_updated_at else None,
        )

    return jsonify(
        success=False,
        message=f"بروزرسانی {platform_key} انجام نشد.",
        extracted=extracted,
        failed=failed,
        instagram_followers=wikipedia_record.instagram_followers,
        youtube_subscribers=wikipedia_record.youtube_subscribers,
        facebook_followers=wikipedia_record.facebook_followers,
        spotify_followers=wikipedia_record.spotify_followers,
        soundcloud_followers=wikipedia_record.soundcloud_followers,
        x_followers=wikipedia_record.x_followers,
        tiktok_followers=getattr(wikipedia_record, 'tiktok_followers', None),
        updated_at=wikipedia_record.social_counts_updated_at.isoformat() if wikipedia_record.social_counts_updated_at else None,
    )


@admin_bp.route("/artist", methods=["GET", "POST"])
@login_required
def artist_form():
    artist = Artist.query.first()
    infobox_items = []
    if artist and artist.wikipedia_data and artist.wikipedia_data.infobox_json:
        try:
            infobox_items = json.loads(artist.wikipedia_data.infobox_json)
        except (TypeError, ValueError):
            infobox_items = []

    if request.method == "POST":
        if not artist:
            artist = Artist()
            db.session.add(artist)

        artist.name = request.form.get("name", "").strip()
        artist.bio = request.form.get("bio", "").strip()
        avatar_file_url = save_image_file(request.files.get("avatar_file"))
        artist.avatar_url = avatar_file_url or request.form.get("avatar_url", "").strip()
        artist.logo_url = request.form.get("logo_url", "").strip()
        cover_file_url = save_image_file(request.files.get("cover_file"))
        artist.cover_url = cover_file_url or request.form.get("cover_url", "").strip()
        artist.instagram = request.form.get("instagram", "").strip()
        artist.x = request.form.get("x", "").strip()
        artist.tiktok = request.form.get("tiktok", "").strip()
        artist.telegram = request.form.get("telegram", "").strip()
        artist.facebook = request.form.get("facebook", "").strip()
        artist.spotify_artist_url = request.form.get("spotify_artist_url", "").strip()
        artist.youtube_channel_url = request.form.get("youtube_channel_url", "").strip()
        artist.soundcloud_url = request.form.get("soundcloud_url", "").strip()

        action = request.form.get("action", "save")

        db.session.commit()
        flash("اطلاعات آرتیست ذخیره شد.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/artist_form.html", artist=artist)


# ---------------------------------------------------------------- آلبوم
@admin_bp.route("/spotify/import", methods=["GET", "POST"])
@login_required
def spotify_import():
    artist = Artist.query.first()
    has_api_creds = bool(os.environ.get("SPOTIFY_CLIENT_ID") and os.environ.get("SPOTIFY_CLIENT_SECRET"))
    if request.method == "POST":
        spotify_url = request.form.get("spotify_url", "").strip()
        method = request.form.get("method", "scrape")

        if not spotify_url:
            flash("لینک آرتیست، آلبوم یا ترک اسپاتیفای را وارد کن.", "error")
            return redirect(url_for("admin.spotify_import"))

        normalized_url = spotify_url.lower()
        album_id = None
        if "/track/" in normalized_url or normalized_url.startswith("spotify:track:"):
            msg, category = _import_spotify_track_link(spotify_url)
        elif "/album/" in normalized_url or normalized_url.startswith("spotify:album:"):
            msg, category, album_id = _import_spotify_album_link(spotify_url)
        elif "/artist/" in normalized_url or normalized_url.startswith("spotify:artist:"):
            if method == "api":
                msg, category = _import_via_api(spotify_url)
            else:
                msg, category = _import_via_scrape(spotify_url)
        else:
            if method == "api":
                msg, category = _import_via_api(spotify_url)
            else:
                msg, category = _import_via_scrape(spotify_url)

        flash(msg, category)
        if album_id is not None:
            return redirect(url_for("admin.album_edit", album_id=album_id, next_tab="content"))
        return redirect((url_for("admin.dashboard") or "/admin").rstrip("/") + "#content")

    return render_template("admin/spotify_import.html", artist=artist, has_api_creds=has_api_creds)


@admin_bp.route("/spotify/import/<album_id>", methods=["POST"])
@login_required
def spotify_import_album(album_id):
    artist = Artist.query.first()
    if not artist:
        flash("ابتدا اطلاعات آرتیست را وارد کنید.", "error")
        return redirect(url_for("admin.artist_form"))

    try:
        album, status = import_spotify_album_to_site(album_id, artist)
    except Exception as exc:
        flash(f"ورود آلبوم از اسپاتیفای انجام نشد: {exc}", "error")
        return redirect(url_for("admin.spotify_import"))

    if status == "existing":
        flash("این آلبوم از قبل در سایت موجود است.", "info")
    else:
        flash(f"آلبوم «{album.title}» با موفقیت وارد شد.", "success")

    return redirect(url_for("admin.album_edit", album_id=album.id, next_tab="content"))


@admin_bp.route("/spotify/import-all", methods=["POST"])
@login_required
def spotify_import_all():
    artist = Artist.query.first()
    if not artist:
        flash("ابتدا اطلاعات آرتیست را وارد کنید.", "error")
        return redirect(url_for("admin.artist_form"))

    query = request.form.get("query", "").strip()
    if not query:
        flash("برای ورود دسته‌جمعی، ابتدا جست‌وجو انجام دهید.", "error")
        return redirect(url_for("admin.spotify_import"))

    try:
        results = search_spotify_albums(f"{artist.name} {query}".strip())
    except Exception as exc:
        flash(f"اتصال به اسپاتیفای انجام نشد: {exc}", "error")
        return redirect(url_for("admin.spotify_import"))

    imported_count = 0
    skipped_count = 0
    for album in results:
        album_id = album.get("id")
        if not album_id:
            continue
        _, status = import_spotify_album_to_site(album_id, artist)
        if status == "imported":
            imported_count += 1
        else:
            skipped_count += 1

    flash(f"ورود دسته‌جمعی انجام شد: {imported_count} آلبوم وارد شد و {skipped_count} آلبوم رد شد.", "success")
    return redirect(url_for("admin.dashboard", _anchor="content"))


@admin_bp.route("/album/new", methods=["GET", "POST"])
@login_required
def album_new():
    artist = Artist.query.first()
    if not artist:
        flash("ابتدا اطلاعات آرتیست را وارد کنید.", "error")
        return redirect(url_for("admin.artist_form"))

    if request.method == "POST":
        release_date = parse_album_release_date(request.form)
        cover_file_url = save_image_file(request.files.get("cover_file"))
        album = Album(
            title=request.form.get("title", "").strip(),
            cover_url=cover_file_url or request.form.get("cover_url", "").strip(),
            artist_name=request.form.get("artist_name", "").strip(),
            release_date=release_date,
            release_year=release_date.year if release_date else None,
            artist_id=artist.id,
        )
        db.session.add(album)
        db.session.commit()
        album.update_release_type()
        db.session.commit()
        flash("آلبوم با موفقیت اضافه شد.", "success")
        return redirect_back("admin.dashboard")

    return render_template("admin/album_form.html", album=None)


@admin_bp.route("/album/<int:album_id>/edit", methods=["GET", "POST"])
@login_required
def album_edit(album_id):
    album = Album.query.get_or_404(album_id)
    if request.method == "POST":
        release_date = parse_album_release_date(request.form)
        cover_file_url = save_image_file(request.files.get("cover_file"))
        album.title = request.form.get("title", "").strip()
        album.cover_url = cover_file_url or request.form.get("cover_url", "").strip()
        album.artist_name = request.form.get("artist_name", "").strip()
        album.release_date = release_date
        album.release_year = release_date.year if release_date else None
        album.update_release_type()
        db.session.commit()
        flash("آلبوم ویرایش شد.", "success")
        return redirect_back("admin.dashboard") if (request.form.get("next") or request.args.get("next")) else redirect_to_content_section()

    return render_template("admin/album_form.html", album=album)


@admin_bp.route("/album/<int:album_id>/delete", methods=["POST"])
@login_required
def album_delete(album_id):
    album = Album.query.get_or_404(album_id)
    db.session.delete(album)
    db.session.commit()
    flash("آلبوم و تمام آهنگ‌های آن حذف شدند.", "success")
    return redirect_back("admin.dashboard") if (request.form.get("next") or request.args.get("next")) else redirect_to_content_section()


# ---------------------------------------------------------------- آهنگ
@admin_bp.route("/album/<int:album_id>/track/new", methods=["GET", "POST"])
@login_required
def track_new(album_id):
    album = Album.query.get_or_404(album_id)
    all_tracks = Track.query.order_by(Track.title.asc()).all()
    lyricist_options = [
        item[0] for item in db.session.query(Lyricist.name)
        .order_by(Lyricist.name.asc())
        .all()
    ]
    if request.method == "POST":
        cover_file_url = save_image_file(request.files.get("cover_file"))
        release_date = parse_release_date(request.form)
        if release_date is None:
            release_date = album.release_date

        selected_lyricists = request.form.getlist("lyricist")
        custom_lyricist_names = [name.strip() for name in request.form.get("new_lyricist", "").split(",") if name.strip()]
        lyricist_names = []
        for value in selected_lyricists:
            if value == "__new__":
                lyricist_names.extend(custom_lyricist_names)
            elif value == "__none__":
                continue
            elif value:
                lyricist_names.append(value.strip())
        lyricist_names = list(dict.fromkeys(name for name in lyricist_names if name))

        work_type = (request.form.get("work_type") or "original").strip().lower()
        if work_type not in {"original", "remix", "other"}:
            work_type = "original"

        remix_source_id_str = (request.form.get("remix_of_track_id") or "").strip()
        remix_source = None
        if remix_source_id_str:
            try:
                remix_source = Track.query.filter_by(id=int(remix_source_id_str)).first()
            except (TypeError, ValueError):
                remix_source = None

        if remix_source is None and work_type == "remix":
            typed_title = (request.form.get("remix_of_track_title") or "").strip()
            if typed_title:
                remix_source = Track.query.filter(db.func.lower(Track.title).like(f"%{typed_title.lower()}%")) .order_by(Track.title.asc()).first()

        remix_source_title = remix_source.title if remix_source else ""

        track = Track(
            title=request.form.get("title", "").strip(),
            featuring=request.form.get("featuring", "").strip(),
            lyricist=", ".join(lyricist_names) if lyricist_names else "",
            lyrics=request.form.get("lyrics", "").strip() if lyricist_names else "",
            work_type=work_type,
            remix_of=remix_source_title if work_type == "remix" else "",
            remix_of_track_id=remix_source.id if remix_source and work_type == "remix" else None,
            is_the_shah=bool(request.form.get("is_the_shah")),
            cover_url=cover_file_url or request.form.get("cover_url", "").strip() or album.cover_url,
            duration=request.form.get("duration", "").strip(),
            release_date=release_date,
            album_id=album.id,
            spotify_url=request.form.get("spotify_url", "").strip(),
            youtube_url=request.form.get("youtube_url", "").strip(),
            youtube_url_secondary=request.form.get("youtube_url_secondary", "").strip(),
            youtube_url_is_music_video=bool(request.form.get("youtube_url_is_music_video")),
            youtube_url_secondary_is_music_video=bool(request.form.get("youtube_url_secondary_is_music_video")),
            soundcloud_url=request.form.get("soundcloud_url", "").strip(),
            genre=request.form.get("genre", "").strip(),
        )
        db.session.add(track)
        db.session.flush()

        for lyricist_name in lyricist_names:
            lyricist = Lyricist.query.filter_by(name=lyricist_name).first()
            if lyricist is None:
                lyricist = Lyricist(name=lyricist_name)
                db.session.add(lyricist)
                db.session.flush()
            track.lyricists.append(lyricist)

        # If this track is a remix and a remix source was selected,
        # copy lyricist string, lyrics text, and relationships from the source track.
        if work_type == 'remix' and remix_source:
            try:
                track.lyricist = remix_source.lyricist or ''
                track.lyrics = remix_source.lyrics or ''
                track.lyricists = []
                for src_lyr in remix_source.lyricists:
                    track.lyricists.append(src_lyr)
            except Exception:
                pass

        db.session.commit()
        album.update_release_type()
        db.session.commit()
        flash("آهنگ با موفقیت اضافه شد.", "success")
        return redirect_back("admin.dashboard")

    return render_template("admin/track_form.html", track=None, album=album, all_tracks=all_tracks, suggested_genres=SUGGESTED_GENRES, lyricist_options=lyricist_options)


@admin_bp.route("/track/<int:track_id>/edit", methods=["GET", "POST"])
@login_required
def track_edit(track_id):
    track = Track.query.get_or_404(track_id)
    all_tracks = Track.query.order_by(Track.title.asc()).all()
    lyricist_options = [
        item[0] for item in db.session.query(Lyricist.name)
        .order_by(Lyricist.name.asc())
        .all()
    ]
    if request.method == "POST":
        cover_file_url = save_image_file(request.files.get("cover_file"))

        release_date = parse_release_date(request.form)
        if release_date is None:
            release_date = track.album.release_date

        selected_lyricists = request.form.getlist("lyricist")
        custom_lyricist_names = [name.strip() for name in request.form.get("new_lyricist", "").split(",") if name.strip()]
        lyricist_names = []
        for value in selected_lyricists:
            if value == "__new__":
                lyricist_names.extend(custom_lyricist_names)
            elif value == "__none__":
                continue
            elif value:
                lyricist_names.append(value.strip())
        lyricist_names = list(dict.fromkeys(name for name in lyricist_names if name))

        work_type = (request.form.get("work_type") or "original").strip().lower()
        if work_type not in {"original", "remix", "other"}:
            work_type = "original"

        remix_source_id_str = (request.form.get("remix_of_track_id") or "").strip()
        remix_source = None
        if remix_source_id_str:
            try:
                remix_source = Track.query.filter_by(id=int(remix_source_id_str)).first()
            except (TypeError, ValueError):
                remix_source = None

        if remix_source is None and work_type == "remix":
            typed_title = (request.form.get("remix_of_track_title") or "").strip()
            if typed_title:
                remix_source = Track.query.filter(db.func.lower(Track.title).like(f"%{typed_title.lower()}%")) .order_by(Track.title.asc()).first()

        track.title = request.form.get("title", "").strip()
        track.featuring = request.form.get("featuring", "").strip()
        track.lyricist = ", ".join(lyricist_names) if lyricist_names else ""
        track.lyrics = request.form.get("lyrics", "").strip() if lyricist_names else ""
        track.work_type = work_type
        track.remix_of = remix_source.title if remix_source and work_type == "remix" else ""
        track.remix_of_track_id = remix_source.id if remix_source and work_type == "remix" else None
        track.is_the_shah = bool(request.form.get("is_the_shah"))
        track.cover_url = cover_file_url or request.form.get("cover_url", "").strip()
        track.duration = request.form.get("duration", "").strip()
        track.release_date = release_date
        track.spotify_url = request.form.get("spotify_url", "").strip()
        track.youtube_url_secondary = request.form.get("youtube_url_secondary", "").strip()
        track.youtube_url = request.form.get("youtube_url", "").strip()
        track.youtube_url_is_music_video = bool(request.form.get("youtube_url_is_music_video"))
        track.youtube_url_secondary_is_music_video = bool(request.form.get("youtube_url_secondary_is_music_video"))
        track.soundcloud_url = request.form.get("soundcloud_url", "").strip()
        track.genre = request.form.get("genre", "").strip()

        track.lyricists = []
        for lyricist_name in lyricist_names:
            lyricist = Lyricist.query.filter_by(name=lyricist_name).first()
            if lyricist is None:
                lyricist = Lyricist(name=lyricist_name)
                db.session.add(lyricist)
                db.session.flush()
            track.lyricists.append(lyricist)

        # If this track is a remix and a remix source was selected,
        # copy lyricist string, lyrics text, and relationships from the source track.
        if work_type == 'remix' and remix_source:
            try:
                track.lyricist = remix_source.lyricist or ''
                track.lyrics = remix_source.lyrics or ''
                track.lyricists = []
                for src_lyr in remix_source.lyricists:
                    track.lyricists.append(src_lyr)
            except Exception:
                pass

        db.session.commit()
        track.album.update_release_type()
        db.session.commit()
        flash("آهنگ ویرایش شد.", "success")
        return redirect_back("admin.dashboard") if (request.form.get("next") or request.args.get("next")) else redirect_to_content_section()

    for existing_name in track.lyricist_names:
        if existing_name not in lyricist_options:
            lyricist_options.append(existing_name)

    return render_template("admin/track_form.html", track=track, album=track.album, all_tracks=all_tracks, suggested_genres=SUGGESTED_GENRES, lyricist_options=lyricist_options)


@admin_bp.route("/track/<int:track_id>/delete", methods=["POST"])
@login_required
def track_delete(track_id):
    track = Track.query.get_or_404(track_id)
    album = track.album
    db.session.delete(track)
    db.session.commit()
    if album:
        album.update_release_type()
        db.session.commit()
    flash("آهنگ حذف شد.", "success")
    return redirect_back("admin.dashboard") if (request.form.get("next") or request.args.get("next")) else redirect_to_content_section()


@admin_bp.route("/track/<int:track_id>/update-views/<platform>", methods=["POST"])
@login_required
def update_track_views(track_id, platform):
    track = Track.query.get_or_404(track_id)
    platform = (platform or "").strip().lower()
    if platform not in {"spotify", "youtube", "soundcloud"}:
        message = "پلتفرم نامعتبر است."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return jsonify({"success": False, "message": message}), 400
        flash(message, "error")
        return redirect(url_for("admin.dashboard"))

    from app import update_track_views as update_single_track_views

    success = update_single_track_views(track, platform)
    latest_stats = track.latest_stats()
    message = f"آمار {platform} برای آهنگ «{track.title}» به‌روزرسانی شد."
    error_message = f"به‌روزرسانی آمار {platform} برای آهنگ «{track.title}» انجام نشد."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
        if success:
            return jsonify({"success": True, "message": message, "platform": platform, "track_id": track.id, "latest_stats": latest_stats})
        return jsonify({"success": False, "message": error_message, "platform": platform, "track_id": track.id, "latest_stats": latest_stats}), 400

    if success:
        flash(message, "success")
    else:
        flash(error_message, "error")
    return redirect(url_for("admin.dashboard", _anchor="content"))


# ---------------------------------------------------------------- آپدیت دستی ویوها
@admin_bp.route("/update-views", methods=["POST"])
@login_required
def trigger_update():
    from flask import current_app
    from app import update_all_tracks
    update_all_tracks(current_app._get_current_object())
    flash("آپدیت آمار انجام شد.", "success")
    return redirect(url_for("admin.dashboard", _anchor="content"))

# ---------------------------------------------------------------- وارد کردن خودکار از اسپاتیفای
def _get_or_create_artist(spotify_url, name="", avatar_url=""):
    artist = None
    spotify_url = (spotify_url or "").strip()
    normalized_name = (name or "").strip()

    if spotify_url:
        artist = Artist.query.filter(Artist.spotify_artist_url == spotify_url).first()

    if not artist and normalized_name:
        artist = Artist.query.filter(Artist.name == normalized_name).first()

    if not artist:
        artist = Artist(
            name=normalized_name or "Unknown Artist",
            avatar_url=avatar_url or "",
            spotify_artist_url=spotify_url,
        )
        db.session.add(artist)
    else:
        if not artist.name and normalized_name:
            artist.name = normalized_name
        if spotify_url and not artist.spotify_artist_url:
            artist.spotify_artist_url = spotify_url
        if avatar_url and not artist.avatar_url:
            artist.avatar_url = avatar_url

    db.session.commit()
    return artist


def _import_spotify_track_link(spotify_url):
    try:
        from spotify_scraper import SpotifyClient, urls
    except ImportError as exc:
        return f"پکیج spotify_scraper نصب نشده یا بارگذاری نمی‌شود: {exc}", "error"

    try:
        with SpotifyClient() as client:
            sp_track = client.get_track(spotify_url)
    except Exception as exc:
        return f"دریافت اطلاعات ترک از اسپاتیفای انجام نشد: {exc}", "error"

    if not sp_track:
        return "اطلاعات ترک از اسپاتیفای دریافت نشد.", "error"

    artist_name = sp_track.artists[0].name if sp_track.artists else "Artist"
    artist_url = urls.entity_url("artist", sp_track.artists[0].id) if sp_track.artists and sp_track.artists[0].id else spotify_url
    artist = _get_or_create_artist(artist_url, artist_name, avatar_url=(sp_track.images[0].url if sp_track.images else ""))

    album_title = sp_track.album.name if getattr(sp_track, "album", None) and getattr(sp_track.album, "name", None) else "Single"
    album_cover = ""
    if getattr(sp_track, "images", None):
        album_cover = sp_track.images[0].url
    elif getattr(sp_track, "album", None) and getattr(sp_track.album, "images", None):
        album_cover = sp_track.album.images[0].url if sp_track.album.images else ""

    album = Album.query.filter_by(artist_id=artist.id, title=album_title).first()
    if not album:
        release_date = getattr(sp_track, "release_date", None)
        album = Album(
            title=album_title,
            cover_url=album_cover,
            release_date=release_date,
            release_year=release_date.year if release_date else None,
            artist_name=artist_name,
            artist_id=artist.id,
        )
        db.session.add(album)
        db.session.commit()
    elif not album.artist_name:
        album.artist_name = artist_name
        db.session.commit()

    existing_track = Track.query.filter_by(album_id=album.id, title=sp_track.name.strip()).first()
    if existing_track:
        if not existing_track.artist_name:
            existing_track.artist_name = artist_name
            db.session.commit()
        return f"این ترک «{sp_track.name}» قبلا در آلبوم «{album.title}» ثبت شده است.", "info"

    track = Track(
        title=sp_track.name.strip(),
        featuring=", ".join([artist.name for artist in sp_track.artists[1:] if getattr(artist, "name", None)]),
        cover_url=album_cover or album.cover_url,
        duration=format_duration_ms(getattr(sp_track, "duration_ms", None)),
        artist_name=artist_name,
        album_id=album.id,
        spotify_url=getattr(sp_track, "url", spotify_url),
    )
    db.session.add(track)
    db.session.commit()

    return f"ترک «{track.title}» از آلبوم «{album.title}» وارد شد.", "success"


def _import_spotify_album_link(spotify_url):
    try:
        from spotify_scraper import SpotifyClient, urls
    except ImportError as exc:
        return f"پکیج spotify_scraper نصب نشده یا بارگذاری نمی‌شود: {exc}", "error", None

    try:
        with SpotifyClient() as client:
            sp_album = client.get_album(spotify_url)
    except Exception as exc:
        return f"دریافت اطلاعات آلبوم از اسپاتیفای انجام نشد: {exc}", "error", None

    if not sp_album:
        return "اطلاعات آلبوم از اسپاتیفای دریافت نشد.", "error", None

    artist_name = sp_album.artists[0].name if sp_album.artists else "Artist"
    artist_url = urls.entity_url("artist", sp_album.artists[0].id) if sp_album.artists and sp_album.artists[0].id else spotify_url
    artist = _get_or_create_artist(artist_url, artist_name, avatar_url=(sp_album.images[0].url if getattr(sp_album, "images", None) else ""))

    album_title = sp_album.name.strip() if getattr(sp_album, "name", None) else "Unknown Album"
    album_cover = sp_album.images[0].url if getattr(sp_album, "images", None) else ""
    release_date = getattr(sp_album, "release_date", None)
    release_year = release_date.year if release_date else None

    album = Album.query.filter_by(artist_id=artist.id, title=album_title).first()
    if not album:
        album = Album(
            title=album_title,
            cover_url=album_cover,
            release_date=release_date,
            release_year=release_year,
            artist_name=artist_name,
            artist_id=artist.id,
        )
        db.session.add(album)
        db.session.commit()
    elif not album.artist_name:
        album.artist_name = artist_name
        db.session.commit()

    existing_track_titles = {t.title.strip().lower() for t in album.tracks}
    added_tracks = 0
    for sp_track in getattr(sp_album, "tracks", ()) or ():
        track_title = getattr(sp_track, "name", "").strip()
        if not track_title:
            continue
        if track_title.lower() in existing_track_titles:
            continue

        track_cover = album_cover
        if getattr(sp_track, "images", None):
            track_cover = sp_track.images[0].url

        track = Track(
            title=track_title,
            featuring=", ".join([artist.name for artist in getattr(sp_track, "artists", [])[1:] if getattr(artist, "name", None)]),
            cover_url=track_cover or album.cover_url,
            duration=format_duration_ms(getattr(sp_track, "duration_ms", None)),
            album_id=album.id,
            spotify_url=getattr(sp_track, "url", ""),
        )
        db.session.add(track)
        existing_track_titles.add(track_title.lower())
        added_tracks += 1

    db.session.commit()
    if added_tracks == 0:
        return f"آلبوم «{album.title}» قبلا وارد شده یا هیچ ترک جدیدی نداشت.", "info", album.id

    return f"آلبوم «{album.title}» با {added_tracks} ترک جدید وارد شد.", "success", album.id


def _import_via_scrape(spotify_url):
    """روش جایگزین API: مستقیم از صفحه عمومی اسپاتیفای با Selenium می‌خواند.
    نیازی به Client ID/Secret یا ساخت اپ در پنل دولوپر ندارد."""
    from scraper.spotify_discography_scraper import get_artist_info, get_artist_albums, get_album_tracks

    info = get_artist_info(spotify_url)
    artist = _get_or_create_artist(spotify_url, info.get("name", ""), info.get("avatar_url", ""))

    sp_albums = get_artist_albums(spotify_url)
    if not sp_albums:
        return (
            "هیچ آلبومی پیدا نشد. ممکن است لینک اشتباه باشد یا ساختار صفحه‌ی "
            "اسپاتیفای تغییر کرده باشد (در این صورت باید سلکتورهای "
            "scraper/spotify_discography_scraper.py به‌روزرسانی شوند).",
            "error",
        )

    existing_album_titles = {a.title.strip().lower(): a for a in artist.albums}
    added_albums = added_tracks = skipped_tracks = 0

    for sp_album in sp_albums:
        title = sp_album["title"]
        key = title.strip().lower()

        if key in existing_album_titles:
            album = existing_album_titles[key]
        else:
            album = Album(title=title, cover_url=sp_album.get("cover_url", ""), artist_id=artist.id)
            db.session.add(album)
            db.session.commit()
            existing_album_titles[key] = album
            added_albums += 1

        album_data = get_album_tracks(sp_album["album_url"])
        if album_data.get("release_year") and not album.release_year:
            album.release_year = album_data["release_year"]
        if album_data.get("cover_url") and not album.cover_url:
            album.cover_url = album_data["cover_url"]

        existing_track_titles = {t.title.strip().lower() for t in album.tracks}
        for sp_track in album_data.get("tracks", []):
            t_key = sp_track["title"].strip().lower()
            if t_key in existing_track_titles:
                skipped_tracks += 1
                continue
            track = Track(
                title=sp_track["title"],
                cover_url=album.cover_url,
                duration=sp_track.get("duration", ""),
                album_id=album.id,
                spotify_url=sp_track.get("track_url", ""),
            )
            db.session.add(track)
            existing_track_titles.add(t_key)
            added_tracks += 1

        db.session.commit()

    msg = (
        f"وارد کردن (روش اسکرپینگ مستقیم) تمام شد: {added_albums} آلبوم جدید "
        f"و {added_tracks} آهنگ جدید اضافه شد"
    )
    if skipped_tracks:
        msg += f" ({skipped_tracks} آهنگ تکراری نادیده گرفته شد)"
    msg += ". حالا برای هر آهنگ لینک یوتیوب موزیک و ساندکلود را از فرم ویرایش وارد کن."
    return msg, "success"


def _import_via_api(spotify_url):
    """روش رسمی با Spotify Web API — نیاز به SPOTIFY_CLIENT_ID/SECRET دارد."""
    from scraper.spotify_api import (
        SpotifyAPIError, extract_artist_id, get_artist_info,
        get_artist_albums, get_album_tracks, format_duration,
    )

    artist_id = extract_artist_id(spotify_url)
    if not artist_id:
        return "لینک آرتیست اسپاتیفای معتبر نیست.", "error"

    try:
        info = get_artist_info(artist_id)
        spotify_albums = get_artist_albums(artist_id)
    except SpotifyAPIError as e:
        return str(e), "error"

    artist = _get_or_create_artist(
        spotify_url, info.get("name", ""),
        (info["images"][0]["url"] if info.get("images") else ""),
    )
    default_genre = (info.get("genres") or [None])[0]

    existing_album_titles = {a.title.strip().lower(): a for a in artist.albums}
    added_albums = added_tracks = skipped_tracks = 0

    for sp_album in spotify_albums:
        title = sp_album["name"]
        key = title.strip().lower()
        cover_url = sp_album["images"][0]["url"] if sp_album.get("images") else ""
        release_year = int(sp_album["release_date"][:4]) if sp_album.get("release_date") else None

        if key in existing_album_titles:
            album = existing_album_titles[key]
        else:
            album = Album(title=title, cover_url=cover_url, release_year=release_year, artist_id=artist.id)
            db.session.add(album)
            db.session.commit()
            existing_album_titles[key] = album
            added_albums += 1

        try:
            sp_tracks = get_album_tracks(sp_album["id"])
        except SpotifyAPIError:
            continue

        existing_track_titles = {t.title.strip().lower() for t in album.tracks}
        for sp_track in sp_tracks:
            t_key = sp_track["name"].strip().lower()
            if t_key in existing_track_titles:
                skipped_tracks += 1
                continue
            track = Track(
                title=sp_track["name"],
                cover_url=cover_url,
                duration=format_duration(sp_track["duration_ms"]),
                album_id=album.id,
                spotify_url=(sp_track.get("external_urls") or {}).get("spotify", ""),
                genre=default_genre or "",
            )
            db.session.add(track)
            existing_track_titles.add(t_key)
            added_tracks += 1

        db.session.commit()

    msg = f"وارد کردن (روش API رسمی) تمام شد: {added_albums} آلبوم جدید و {added_tracks} آهنگ جدید اضافه شد"
    if skipped_tracks:
        msg += f" ({skipped_tracks} آهنگ تکراری نادیده گرفته شد)"
    msg += ". حالا برای هر آهنگ لینک یوتیوب موزیک و ساندکلود را از فرم ویرایش وارد کن."
    return msg, "success"


@admin_bp.route("/import/spotify", methods=["GET", "POST"])
@login_required
def import_spotify():
    artist = Artist.query.first()
    has_api_creds = bool(os.environ.get("SPOTIFY_CLIENT_ID") and os.environ.get("SPOTIFY_CLIENT_SECRET"))

    if request.method == "POST":
        spotify_url = request.form.get("spotify_url", "").strip()
        method = request.form.get("method", "scrape")

        if not spotify_url:
            flash("لینک آرتیست اسپاتیفای را وارد کن.", "error")
            return redirect(url_for("admin.import_spotify"))

        if method == "api":
            msg, category = _import_via_api(spotify_url)
        else:
            msg, category = _import_via_scrape(spotify_url)

        flash(msg, category)
        if category == "success":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("admin.import_spotify"))

    return render_template("admin/import_spotify.html", artist=artist, has_api_creds=has_api_creds)
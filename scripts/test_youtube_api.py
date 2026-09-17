import os
import requests

key = os.environ.get("YOUTUBE_API_KEY", "").strip()
if not key:
    try:
        with open(os.path.join(os.path.dirname(__file__), "..", "instance", "youtube_api_key.txt"), "r", encoding="utf-8") as fh:
            key = fh.read().strip()
    except Exception as e:
        print("Failed reading key file:", e)
        key = ""

if not key:
    print("No YouTube API key available.")
    raise SystemExit(1)

vid = "dQw4w9WgXcQ"  # known public video
url = "https://www.googleapis.com/youtube/v3/videos"
params = {"part": "statistics", "id": vid, "key": key}

try:
    r = requests.get(url, params=params, timeout=15)
    print("HTTP", r.status_code)
    try:
        j = r.json()
    except Exception:
        print("Response not JSON:\n", r.text[:1000])
        raise
    print("Response keys:", list(j.keys()))
    items = j.get("items") or []
    if not items:
        print("No items in API response. Full response:\n", j)
        raise SystemExit(1)
    stats = items[0].get("statistics", {})
    print("viewCount:", stats.get("viewCount"))
except Exception as e:
    print("Error calling YouTube API:", e)
    raise

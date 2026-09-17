import os
import sys
from pathlib import Path

# ensure project root in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# load key from instance file if not in env
if not os.environ.get("YOUTUBE_API_KEY"):
    try:
        key_file = ROOT / "instance" / "youtube_api_key.txt"
        if key_file.exists():
            os.environ["YOUTUBE_API_KEY"] = key_file.read_text(encoding="utf-8").strip()
    except Exception:
        pass

from app import create_app
from models import Track
from scraper.youtube_scraper import get_youtube_views

app = create_app()
with app.app_context():
    track = (
        Track.query.filter(Track.youtube_url.isnot(None)).filter_by(is_active=True).order_by(Track.id.asc()).first()
    )
    if not track:
        print("No active track with a YouTube URL found.")
        raise SystemExit(1)

    url = track.youtube_url
    print(f"Track: {track.title}")
    print(f"YouTube URL: {url}")
    views = get_youtube_views(url)
    print(f"Views: {views}")

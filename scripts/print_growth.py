from app import create_app, calculate_daily_growth_stats
from models import Track

app = create_app()
with app.app_context():
    all_tracks = Track.query.join(Track.album).filter(Track.is_active==True).all()
    ids = [t.id for t in all_tracks]
    stats, prev = calculate_daily_growth_stats(ids)
    for t in all_tracks:
        cur = sum((stats.get(t.id, {}) or {}).get(p, 0) for p in ("spotify","youtube","soundcloud"))
        prev_total = sum((prev.get(t.id, {}) or {}).get(p, 0) for p in ("spotify","youtube","soundcloud"))
        print(f"{t.id}\t{t.title}\tcur={cur}\tprev={prev_total}\tdelta={cur-prev_total}")

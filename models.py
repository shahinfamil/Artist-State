import re
import unicodedata
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(500))
    cover_url = db.Column(db.String(500))
    instagram = db.Column(db.String(300))
    x = db.Column(db.String(300))
    tiktok = db.Column(db.String(300))
    telegram = db.Column(db.String(300))
    facebook = db.Column(db.String(500))
    spotify_artist_url = db.Column(db.String(500))
    youtube_channel_url = db.Column(db.String(500))
    soundcloud_url = db.Column(db.String(500))

    albums = db.relationship("Album", backref="artist", lazy=True, cascade="all, delete-orphan")
    wikipedia_data = db.relationship(
        "ArtistWikipediaData",
        back_populates="artist",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def wikipedia_title(self):
        return self.wikipedia_data.title if self.wikipedia_data else None

    @property
    def wikipedia_image_url(self):
        return self.wikipedia_data.image_url if self.wikipedia_data else None

    @property
    def wikipedia_infobox_json(self):
        return self.wikipedia_data.infobox_json if self.wikipedia_data else None

    @property
    def wikipedia_timeline_section(self):
        return self.wikipedia_data.timeline_section if self.wikipedia_data else None


class ArtistWikipediaData(db.Model):
    __tablename__ = "artist_wikipedia_data"

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey("artist.id"), nullable=False, unique=True)
    title = db.Column(db.String(300))
    image_url = db.Column(db.String(500))
    timeline_section = db.Column(db.Text)
    instagram_followers = db.Column(db.BigInteger)
    youtube_subscribers = db.Column(db.BigInteger)
    facebook_followers = db.Column(db.BigInteger)
    spotify_followers = db.Column(db.BigInteger)
    soundcloud_followers = db.Column(db.BigInteger)
    x_followers = db.Column(db.BigInteger)
    tiktok_followers = db.Column(db.BigInteger)
    social_counts_updated_at = db.Column(db.DateTime)
    infobox_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    artist = db.relationship("Artist", back_populates="wikipedia_data", uselist=False)


class SiteMedia(db.Model):
    __tablename__ = 'site_media'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    label = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    cover_url = db.Column(db.String(500))
    release_type = db.Column(db.String(20), nullable=True)
    release_year = db.Column(db.Integer)
    release_date = db.Column(db.Date)  # تاریخ دقیق انتشار (سال-ماه-روز)
    artist_name = db.Column(db.String(200))
    artist_id = db.Column(db.Integer, db.ForeignKey("artist.id"), nullable=False)

    tracks = db.relationship("Track", backref="album", lazy=True, cascade="all, delete-orphan")

    def compute_release_type(self):
        track_count = sum(1 for t in (self.tracks or []) if getattr(t, 'is_active', True))
        if track_count == 1:
            return 'single'
        if 2 <= track_count <= 4:
            return 'ep'
        if track_count > 4:
            return 'album'
        return None

    def update_release_type(self):
        new_type = self.compute_release_type()
        if new_type != self.release_type:
            self.release_type = new_type
            return True
        return False


track_lyricist = db.Table(
    "track_lyricist",
    db.Column("track_id", db.Integer, db.ForeignKey("track.id"), primary_key=True),
    db.Column("lyricist_id", db.Integer, db.ForeignKey("lyricist.id"), primary_key=True),
)


class Lyricist(db.Model):
    __tablename__ = "lyricist"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    @property
    def track_count(self):
        return self.tracks.count() if hasattr(self.tracks, "count") else len(self.tracks)

    def __repr__(self):
        return f"<Lyricist {self.name}>"


def get_lyricist_track_counts():
    return (
        db.session.query(Lyricist.name, db.func.count(track_lyricist.c.track_id).label("track_count"))
        .outerjoin(track_lyricist, track_lyricist.c.lyricist_id == Lyricist.id)
        .group_by(Lyricist.id, Lyricist.name)
        .order_by(Lyricist.name.asc())
        .all()
    )


class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    featuring = db.Column(db.String(150))
    cover_url = db.Column(db.String(500))
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    duration = db.Column(db.String(20))  # مثلا "3:45"
    release_date = db.Column(db.Date)  # تاریخ دقیق انتشار آهنگ
    artist_name = db.Column(db.String(200))
    lyricist = db.Column(db.String(200))  # legacy single-name support
    lyrics = db.Column(db.Text)
    work_type = db.Column(db.String(30), default="original", nullable=False)
    remix_of = db.Column(db.String(200))
    remix_of_track_id = db.Column(db.Integer, db.ForeignKey("track.id"), nullable=True)
    is_the_shah = db.Column(db.Boolean, default=False, nullable=False)
    album_id = db.Column(db.Integer, db.ForeignKey("album.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    lyricists = db.relationship(
        "Lyricist",
        secondary=track_lyricist,
        backref=db.backref("tracks", lazy="dynamic"),
        lazy="subquery",
    )
    remix_source = db.relationship(
        "Track",
        foreign_keys=[remix_of_track_id],
        remote_side="Track.id",
        post_update=True,
    )

    @property
    def display_artist_name(self):
        if self.is_the_shah:
            return "The Shah"

        album_artist_name = getattr(self.album, "artist_name", None)
        if album_artist_name and album_artist_name.strip():
            return album_artist_name.strip()

        track_artist_name = (self.artist_name or "").strip()
        if track_artist_name:
            return track_artist_name

        return "شاهین نجفی"

    @staticmethod
    def _normalize_name(value):
        if value is None:
            return ""
        text = unicodedata.normalize("NFKC", str(value)).strip()
        text = text.replace("ـ", "")
        text = re.sub(r"[\-_/|]+", " ", text)
        text = text.replace("،", ",").replace(";", ",")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\b(?:feat|ft|featuring|with)\b.*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*,\s*", ",", text)
        text = text.strip(" ,;")
        return text.lower()

    @property
    def collaborator_names(self):
        names = []
        seen = set()
        own_names = {
            "the shah",
            "theshah",
            "dshah",
            "دشاه",
            "د شاه",
            "د-شاه",
            "شاه",
            "shah",
            "شاهین نجفی",
            "شاهين نجفی",
            "shahin najafi",
            "شاهین",
            "shahin",
        }

        raw_names = []
        if self.featuring and self.featuring.strip():
            raw_names.extend(
                part.strip()
                for part in re.split(r"[,;|\n]+", self.featuring)
                if part.strip()
            )

        if not raw_names and self.artist_name and self.artist_name.strip():
            raw_names = [self.artist_name.strip()]

        for raw in raw_names:
            clean_name = " ".join(raw.split())
            if not clean_name:
                continue

            normalized = self._normalize_name(clean_name)
            if not normalized:
                continue

            if normalized in own_names:
                continue

            if normalized == self._normalize_name(self.display_artist_name):
                continue

            if normalized in {self._normalize_name(name) for name in own_names}: 
                continue

            display = re.sub(r"\s+", " ", clean_name).strip()
            if display not in seen:
                seen.add(display)
                names.append(display)

        return names

    # لینک هرکدوم به صفحه واقعی اون پلتفرم برای اسکرپ کردن
    spotify_url = db.Column(db.String(500))
    youtube_url = db.Column(db.String(500))
    youtube_url_secondary = db.Column(db.String(500))
    youtube_url_is_music_video = db.Column(db.Boolean, default=False, nullable=False)
    youtube_url_secondary_is_music_video = db.Column(db.Boolean, default=False, nullable=False)
    soundcloud_url = db.Column(db.String(500))


    # ژانر (مثلا "رپ"، "راک"، "پاپ") - برای دسته‌بندی
    genre = db.Column(db.String(60))

    stats = db.relationship("ViewStat", backref="track", lazy=True, cascade="all, delete-orphan")

    def latest_stats(self):
        """آخرین مقدار ثبت‌شده برای هر پلتفرم"""
        result = {}
        for platform in ["spotify", "youtube", "soundcloud"]:
            stat = (
                ViewStat.query.filter_by(track_id=self.id, platform=platform)
                .order_by(ViewStat.fetched_at.desc())
                .first()
            )
            result[platform] = stat.views if stat else None
        return result

    @property
    def music_video_url(self):
        if self.youtube_url_is_music_video:
            return self.youtube_url
        if self.youtube_url_secondary_is_music_video:
            return self.youtube_url_secondary
        return None

    @property
    def is_remix(self):
        return (self.work_type or "original").strip().lower() == "remix"

    @property
    def remix_display_name(self):
        if self.remix_source and self.remix_source.title:
            return self.remix_source.title
        if self.remix_of:
            return self.remix_of
        return None

    @property
    def work_type_label(self):
        kind = (self.work_type or "original").strip().lower()
        labels = {
            "original": "کار اصلی",
            "remix": "ریمیکس",
            "other": "کار دیگر",
        }
        return labels.get(kind, "کار اصلی")

    @property
    def lyricist_names(self):
        names = [lyricist.name for lyricist in sorted(self.lyricists, key=lambda item: item.name.lower())]
        legacy_names = [part.strip() for part in (self.lyricist or "").split(",") if part.strip()]
        if legacy_names:
            names.extend(legacy_names)
        return list(dict.fromkeys(name for name in names if name))

    @property
    def lyricist_display(self):
        return ", ".join(self.lyricist_names)

    def total_views(self):
        latest = self.latest_stats()
        return sum(v for v in latest.values() if v)


class ViewStat(db.Model):
    """تاریخچه روزانه ویوها - برای هر روز یک رکورد جدید ذخیره می‌شود"""
    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey("track.id"), nullable=False)
    platform = db.Column(db.String(20), nullable=False)  # spotify, youtube, soundcloud
    views = db.Column(db.BigInteger, default=0)
    fetched_at = db.Column(db.DateTime, default=datetime.now)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

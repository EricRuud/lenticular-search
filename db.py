"""SQLite database for Spinitron playlist/spin history."""

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

# Use Render's persistent disk if available, else ~/.cache/kalx/
if os.environ.get("RENDER"):
    DB_PATH = Path("/opt/render/project/.cache/kalx/kalx.db")
else:
    DB_PATH = Path.home() / ".cache" / "kalx" / "kalx.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS playlists (
    playlist_id   INTEGER PRIMARY KEY,
    station       TEXT NOT NULL DEFAULT 'KALX',
    show_name     TEXT NOT NULL,
    dj_name       TEXT NOT NULL,
    date_str      TEXT NOT NULL,
    show_date     TEXT NOT NULL,
    fetched_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS spins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id   INTEGER NOT NULL REFERENCES playlists(playlist_id),
    spin_time     TEXT NOT NULL,
    artist        TEXT NOT NULL,
    song          TEXT NOT NULL,
    album         TEXT NOT NULL DEFAULT '',
    label         TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_spins_artist ON spins(artist COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_spins_playlist ON spins(playlist_id);
CREATE INDEX IF NOT EXISTS idx_playlists_date ON playlists(show_date);
CREATE INDEX IF NOT EXISTS idx_playlists_station ON playlists(station);

CREATE TABLE IF NOT EXISTS artist_tags (
    artist        TEXT NOT NULL COLLATE NOCASE,
    tag           TEXT NOT NULL COLLATE NOCASE,
    score         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (artist, tag)
);

CREATE INDEX IF NOT EXISTS idx_artist_tags_tag ON artist_tags(tag COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_artist_tags_artist ON artist_tags(artist COLLATE NOCASE);
"""

MIGRATIONS = [
    # Add station column if missing (for existing DBs)
    """
    ALTER TABLE playlists ADD COLUMN station TEXT NOT NULL DEFAULT 'KALX';
    """,
]


def _seed_db_if_needed():
    """Copy bundled DB into data dir on first run."""
    if DB_PATH.exists():
        return
    bundled = Path(__file__).parent / "kalx.db"
    if bundled.exists():
        import shutil
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundled, DB_PATH)
        print(f"[db] Seeded database from bundled kalx.db ({bundled.stat().st_size // 1024 // 1024}MB)", flush=True)


def get_connection():
    """Get a database connection, creating tables if needed."""
    _seed_db_if_needed()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _run_migrations(conn)
    conn.executescript(SCHEMA)
    return conn


def _run_migrations(conn):
    """Run any needed schema migrations."""
    # Check if playlists table exists yet
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    if "playlists" not in tables:
        return  # Fresh DB, SCHEMA will create everything

    # Add station column if missing
    cols = [r[1] for r in conn.execute("PRAGMA table_info(playlists)").fetchall()]
    if "station" not in cols:
        conn.execute("ALTER TABLE playlists ADD COLUMN station TEXT NOT NULL DEFAULT 'KALX'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_playlists_station ON playlists(station)")
        conn.commit()


def store_playlist(conn, playlist):
    """Store a parsed playlist dict into the database."""
    if playlist is None or playlist.get("playlist_id") is None:
        return

    show_date = playlist["date"].isoformat() if playlist.get("date") else ""
    station = playlist.get("station", "KALX")

    conn.execute(
        "INSERT OR REPLACE INTO playlists (playlist_id, station, show_name, dj_name, date_str, show_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (playlist["playlist_id"], station, playlist["show_name"], playlist["dj_name"],
         playlist["date_str"], show_date),
    )
    conn.execute("DELETE FROM spins WHERE playlist_id = ?", (playlist["playlist_id"],))

    for spin in playlist.get("spins", []):
        conn.execute(
            "INSERT INTO spins (playlist_id, spin_time, artist, song, album, label) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (playlist["playlist_id"], spin["time"], spin["artist"],
             spin["song"], spin["album"], spin["label"]),
        )
    conn.commit()


def _escape_like(s):
    """Escape SQL LIKE wildcards."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_db(conn, query, start_date, end_date, stations=None):
    """Search spins by artist substring match. Returns grouped results."""
    pattern = f"%{_escape_like(query)}%"

    if stations:
        placeholders = ",".join("?" for _ in stations)
        sql = f"""
            SELECT p.playlist_id, p.show_name, p.dj_name, p.date_str, p.show_date,
                   s.spin_time, s.artist, s.song, s.album, s.label, p.station
            FROM spins s
            JOIN playlists p ON s.playlist_id = p.playlist_id
            WHERE s.artist LIKE ? ESCAPE '\\'
              AND p.show_date BETWEEN ? AND ?
              AND p.station IN ({placeholders})
            ORDER BY p.show_date, s.spin_time
        """
        params = [pattern, start_date.isoformat(), end_date.isoformat()] + list(stations)
    else:
        sql = """
            SELECT p.playlist_id, p.show_name, p.dj_name, p.date_str, p.show_date,
                   s.spin_time, s.artist, s.song, s.album, s.label, p.station
            FROM spins s
            JOIN playlists p ON s.playlist_id = p.playlist_id
            WHERE s.artist LIKE ? ESCAPE '\\'
              AND p.show_date BETWEEN ? AND ?
            ORDER BY p.show_date, s.spin_time
        """
        params = [pattern, start_date.isoformat(), end_date.isoformat()]

    rows = conn.execute(sql, params).fetchall()

    grouped = {}
    for row in rows:
        pid = row[0]
        if pid not in grouped:
            show_date = date.fromisoformat(row[4]) if row[4] else None
            grouped[pid] = {
                "playlist_id": pid,
                "show_name": row[1],
                "dj_name": row[2],
                "date_str": row[3],
                "date": show_date,
                "station": row[10],
                "spins": [],
            }
        grouped[pid]["spins"].append({
            "time": row[5],
            "artist": row[6],
            "song": row[7],
            "album": row[8],
            "label": row[9],
        })

    return list(grouped.values())


def get_playlist_from_db(conn, playlist_id):
    """Get a single playlist with its spins from the database."""
    row = conn.execute(
        "SELECT playlist_id, show_name, dj_name, date_str, show_date, station "
        "FROM playlists WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchone()
    if not row:
        return None

    show_date = date.fromisoformat(row[4]) if row[4] else None
    spins = conn.execute(
        "SELECT spin_time, artist, song, album, label FROM spins "
        "WHERE playlist_id = ? ORDER BY rowid",
        (playlist_id,),
    ).fetchall()

    return {
        "playlist_id": row[0],
        "show_name": row[1],
        "dj_name": row[2],
        "date_str": row[3],
        "date": show_date,
        "station": row[5],
        "spins": [
            {"time": s[0], "artist": s[1], "song": s[2], "album": s[3], "label": s[4]}
            for s in spins
        ],
    }


def get_stored_playlist_ids(conn, start_date, end_date, station=None):
    """Get set of playlist IDs already stored for a date range."""
    if station:
        rows = conn.execute(
            "SELECT playlist_id FROM playlists WHERE show_date BETWEEN ? AND ? AND station = ?",
            (start_date.isoformat(), end_date.isoformat(), station),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT playlist_id FROM playlists WHERE show_date BETWEEN ? AND ?",
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return {r[0] for r in rows}


def get_top_artists(conn, start_date, end_date, stations=None, tags=None, tag=None, limit=50):
    """Get most-played artists in a date range, optionally filtered by genre tags."""
    conditions = ["p.show_date BETWEEN ? AND ?", "s.artist != ''"]
    where_params = [start_date.isoformat(), end_date.isoformat()]
    joins = ""
    join_params = []

    if stations:
        placeholders = ",".join("?" for _ in stations)
        conditions.append(f"p.station IN ({placeholders})")
        where_params += list(stations)

    # Support both single tag and multiple tags
    all_tags = list(tags or [])
    if tag and tag not in all_tags:
        all_tags.append(tag)
    if all_tags:
        placeholders = ",".join("?" for _ in all_tags)
        joins = f"JOIN artist_tags at ON s.artist = at.artist COLLATE NOCASE AND at.tag IN ({placeholders}) COLLATE NOCASE"
        join_params = list(all_tags)

    params = join_params + where_params + [limit]
    where = " AND ".join(conditions)

    sql = f"""
        SELECT s.artist, COUNT(*) as play_count,
               COUNT(DISTINCT p.playlist_id) as show_count,
               COUNT(DISTINCT p.station) as station_count,
               GROUP_CONCAT(DISTINCT p.station) as station_list
        FROM spins s
        JOIN playlists p ON s.playlist_id = p.playlist_id
        {joins}
        WHERE {where}
        GROUP BY s.artist COLLATE NOCASE
        ORDER BY play_count DESC
        LIMIT ?
    """

    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "artist": r[0],
            "plays": r[1],
            "shows": r[2],
            "stations": r[4].split(",") if r[4] else [],
        }
        for r in rows
    ]


def store_artist_tags(conn, artist, tags):
    """Store genre tags for an artist."""
    for tag_name, score in tags:
        conn.execute(
            "INSERT OR REPLACE INTO artist_tags (artist, tag, score) VALUES (?, ?, ?)",
            (artist, tag_name, score),
        )
    conn.commit()


def get_untagged_artists(conn, limit=200):
    """Get artists that appear in spins but have no tags yet."""
    rows = conn.execute("""
        SELECT s.artist, COUNT(*) as play_count
        FROM spins s
        LEFT JOIN artist_tags at ON s.artist = at.artist COLLATE NOCASE
        WHERE at.artist IS NULL AND s.artist != ''
        GROUP BY s.artist COLLATE NOCASE
        ORDER BY play_count DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [(r[0], r[1]) for r in rows]


def get_all_tags(conn):
    """Get all unique tags sorted by how many artists have them."""
    rows = conn.execute("""
        SELECT tag, COUNT(DISTINCT artist) as artist_count
        FROM artist_tags
        GROUP BY tag COLLATE NOCASE
        HAVING artist_count >= 3
        ORDER BY artist_count DESC
    """).fetchall()
    return [{"tag": r[0], "count": r[1]} for r in rows]


def get_db_stats(conn):
    """Get basic stats about the database."""
    playlists = conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
    spins = conn.execute("SELECT COUNT(*) FROM spins").fetchone()[0]
    min_date = conn.execute("SELECT MIN(show_date) FROM playlists").fetchone()[0]
    max_date = conn.execute("SELECT MAX(show_date) FROM playlists").fetchone()[0]
    stations = [r[0] for r in conn.execute(
        "SELECT DISTINCT station FROM playlists ORDER BY station"
    ).fetchall()]
    return {
        "playlists": playlists,
        "spins": spins,
        "min_date": min_date,
        "max_date": max_date,
        "stations": stations,
    }

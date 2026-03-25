"""SQLite database for Spinitron playlist/spin history."""

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

# Use Render's persistent disk if mounted, else local data dir, else ~/.cache/kalx/
_render_disk = Path("/opt/render/project/.cache/kalx")
_local_data = Path(__file__).parent / "data"

if os.environ.get("RENDER") and _render_disk.parent.exists():
    DB_PATH = _render_disk / "kalx.db"
elif os.environ.get("RENDER"):
    DB_PATH = _local_data / "kalx.db"
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

CREATE TABLE IF NOT EXISTS artist_locations (
    artist        TEXT PRIMARY KEY COLLATE NOCASE,
    area          TEXT NOT NULL DEFAULT '',
    begin_area    TEXT NOT NULL DEFAULT '',
    is_local      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS album_years (
    artist        TEXT NOT NULL COLLATE NOCASE,
    album         TEXT NOT NULL COLLATE NOCASE,
    release_year  INTEGER,
    release_date  TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (artist, album)
);

CREATE INDEX IF NOT EXISTS idx_album_years_year ON album_years(release_year);
"""

MIGRATIONS = [
    # Add station column if missing (for existing DBs)
    """
    ALTER TABLE playlists ADD COLUMN station TEXT NOT NULL DEFAULT 'KALX';
    """,
]


SEED_VERSION = 3  # bump this to force re-seed on next deploy


def _seed_db_if_needed():
    """Decompress bundled DB into data dir on first run."""
    print(f"[db] DB_PATH={DB_PATH}, exists={DB_PATH.exists()}", flush=True)
    version_file = DB_PATH.parent / "seed_version"
    if DB_PATH.exists():
        current_version = 0
        if version_file.exists():
            try:
                current_version = int(version_file.read_text().strip())
            except Exception:
                pass
        if current_version >= SEED_VERSION:
            return
        print(f"[db] Seed version {current_version} < {SEED_VERSION} — replacing with bundled data", flush=True)
        DB_PATH.unlink()
    bundled_gz = Path(__file__).parent / "kalx.db.gz"
    print(f"[db] bundled_gz={bundled_gz}, exists={bundled_gz.exists()}", flush=True)
    if bundled_gz.exists():
        import gzip
        import shutil
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"[db] Decompressing bundled database to {DB_PATH}...", flush=True)
        with gzip.open(bundled_gz, "rb") as f_in, open(DB_PATH, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        version_file.write_text(str(SEED_VERSION))
        print(f"[db] Seeded database ({DB_PATH.stat().st_size // 1024 // 1024}MB), version {SEED_VERSION}", flush=True)
    else:
        print(f"[db] No bundled database found, starting fresh", flush=True)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(str(SEED_VERSION))


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


def search_db(conn, query, start_date, end_date, stations=None, local_only=False, year_min=None, year_max=None):
    """Search spins by artist substring match. Returns grouped results."""
    pattern = f"%{_escape_like(query)}%"
    conditions = ["s.artist LIKE ? ESCAPE '\\'", "p.show_date BETWEEN ? AND ?"]
    params = [pattern, start_date.isoformat(), end_date.isoformat()]

    if stations:
        placeholders = ",".join("?" for _ in stations)
        conditions.append(f"p.station IN ({placeholders})")
        params += list(stations)

    local_join = "LEFT JOIN" if not local_only else "JOIN"
    if local_only:
        conditions.append("al.is_local = 1")

    year_join = "LEFT JOIN"
    if year_min is not None or year_max is not None:
        year_join = "JOIN"
        if year_min is not None:
            conditions.append("ay.release_year >= ?")
            params.append(year_min)
        if year_max is not None:
            conditions.append("ay.release_year <= ?")
            params.append(year_max)

    where = " AND ".join(conditions)
    sql = f"""
        SELECT p.playlist_id, p.show_name, p.dj_name, p.date_str, p.show_date,
               s.spin_time, s.artist, s.song, s.album, s.label, p.station,
               COALESCE(al.is_local, 0), ay.release_year
        FROM spins s
        JOIN playlists p ON s.playlist_id = p.playlist_id
        {local_join} artist_locations al ON s.artist = al.artist COLLATE NOCASE
        {year_join} album_years ay ON s.artist = ay.artist COLLATE NOCASE AND s.album = ay.album COLLATE NOCASE
        WHERE {where}
        ORDER BY p.show_date, s.spin_time
    """

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
            "local": bool(row[11]),
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


def get_top_artists(conn, start_date, end_date, stations=None, tags=None, tag=None, local_only=False, year_min=None, year_max=None, limit=50):
    """Get most-played artists in a date range, optionally filtered by genre tags."""
    conditions = ["p.show_date BETWEEN ? AND ?", "s.artist != ''"]
    where_params = [start_date.isoformat(), end_date.isoformat()]
    joins = ""
    join_params = []
    year_join = ""

    if local_only:
        conditions.append("al.is_local = 1")

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

    if year_min is not None or year_max is not None:
        year_join = "JOIN album_years ay ON s.artist = ay.artist COLLATE NOCASE AND s.album = ay.album COLLATE NOCASE"
        if year_min is not None:
            conditions.append("ay.release_year >= ?")
            where_params.append(year_min)
        if year_max is not None:
            conditions.append("ay.release_year <= ?")
            where_params.append(year_max)

    params = join_params + where_params + [limit]
    where = " AND ".join(conditions)

    sql = f"""
        SELECT s.artist, COUNT(*) as play_count,
               COUNT(DISTINCT p.playlist_id) as show_count,
               COUNT(DISTINCT p.station) as station_count,
               GROUP_CONCAT(DISTINCT p.station) as station_list,
               COALESCE(al.is_local, 0) as is_local
        FROM spins s
        JOIN playlists p ON s.playlist_id = p.playlist_id
        LEFT JOIN artist_locations al ON s.artist = al.artist COLLATE NOCASE
        {year_join}
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
            "local": bool(r[5]),
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


BAY_AREA_LOCATIONS = {
    # Core cities
    "san francisco", "oakland", "berkeley", "richmond", "san jose",
    "palo alto", "mountain view", "sunnyvale", "santa clara", "fremont",
    "hayward", "concord", "walnut creek", "san mateo", "redwood city",
    "daly city", "santa cruz", "sacramento", "davis", "albany",
    "el cerrito", "emeryville", "san rafael", "vallejo", "petaluma",
    "santa rosa", "novato", "mill valley", "sausalito", "san leandro",
    "pleasanton", "livermore", "cupertino", "menlo park", "half moon bay",
    "pacifica", "south san francisco", "burlingame", "foster city",
    "san bruno", "stockton", "modesto", "antioch", "pittsburg",
    "el sobrante", "pinole", "hercules", "martinez", "benicia",
    "napa", "sonoma", "gilroy", "morgan hill", "los gatos", "campbell",
    "milpitas", "newark", "union city", "san pablo", "orinda",
    "lafayette", "moraga", "danville", "dublin", "san ramon",
    "woodside", "portola valley", "atherton", "los altos", "los altos hills",
    "belmont", "san carlos", "millbrae", "corte madera", "larkspur",
    "tiburon", "fairfax", "san anselmo", "ross", "kentfield",
    "sebastopol", "cotati", "rohnert park", "windsor",
    "alameda", "piedmont", "kensington",
    # Regional names
    "bay area", "san francisco bay area", "east bay", "south bay",
    "north bay", "peninsula", "silicon valley",
    "sf", "the bay",
}


def store_artist_location(conn, artist, area, begin_area):
    """Store artist location and determine if they're local."""
    check = (area.lower().strip(), begin_area.lower().strip())
    is_local = any(loc in BAY_AREA_LOCATIONS for loc in check if loc)
    conn.execute(
        "INSERT OR REPLACE INTO artist_locations (artist, area, begin_area, is_local) "
        "VALUES (?, ?, ?, ?)",
        (artist, area, begin_area, int(is_local)),
    )
    conn.commit()


def get_unlocated_artists(conn, limit=500):
    """Get artists that have no location data yet."""
    rows = conn.execute("""
        SELECT s.artist, COUNT(*) as play_count
        FROM spins s
        LEFT JOIN artist_locations al ON s.artist = al.artist COLLATE NOCASE
        WHERE al.artist IS NULL AND s.artist != ''
        GROUP BY s.artist COLLATE NOCASE
        ORDER BY play_count DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [(r[0], r[1]) for r in rows]


def store_album_year(conn, artist, album, release_year, release_date=""):
    """Store release year for an album."""
    conn.execute(
        "INSERT OR REPLACE INTO album_years (artist, album, release_year, release_date) "
        "VALUES (?, ?, ?, ?)",
        (artist, album, release_year, release_date),
    )
    conn.commit()


def get_undated_albums(conn, limit=500):
    """Get (artist, album) pairs that have no release year yet, sorted by play count."""
    rows = conn.execute("""
        SELECT s.artist, s.album, COUNT(*) as play_count
        FROM spins s
        LEFT JOIN album_years ay ON s.artist = ay.artist COLLATE NOCASE AND s.album = ay.album COLLATE NOCASE
        WHERE ay.artist IS NULL AND s.artist != '' AND s.album != ''
        GROUP BY s.artist COLLATE NOCASE, s.album COLLATE NOCASE
        ORDER BY play_count DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


def get_release_year_ranges(conn):
    """Get available release year decades for the filter UI."""
    rows = conn.execute("""
        SELECT DISTINCT (release_year / 10) * 10 as decade
        FROM album_years
        WHERE release_year IS NOT NULL AND release_year > 0
        ORDER BY decade DESC
    """).fetchall()
    return [r[0] for r in rows]


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

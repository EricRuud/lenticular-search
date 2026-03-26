"""Show bill recommendation engine.

Given a seed artist, find local bands that would work well on a show bill,
using co-occurrence, genre overlap, recency, and bookability signals.
"""

from db import get_connection

# Genre tags that define the indie/psych/art-pop neighborhood
SEED_TAGS = [
    'indie rock', 'indie pop', 'rock', 'singer-songwriter', 'alternative rock',
    'art pop', 'folk', 'freak folk', 'dream pop', 'psychedelic rock',
    'garage rock', 'lo-fi', 'shoegaze', 'surf rock', 'jangle pop',
    'post-punk', 'new wave', 'experimental rock', 'noise pop',
    'indie', 'psychedelic', 'experimental', 'krautrock', 'art rock',
]


def get_seed_artists_from_playlists(conn, artist):
    """Find artists that share playlists with the given artist."""
    rows = conn.execute("""
        SELECT s2.artist, COUNT(DISTINCT s2.playlist_id) as shared
        FROM spins s1
        JOIN spins s2 ON s1.playlist_id = s2.playlist_id AND s1.artist != s2.artist
        WHERE s1.artist LIKE ? COLLATE NOCASE
        GROUP BY s2.artist COLLATE NOCASE
        ORDER BY shared DESC
        LIMIT 20
    """, (f"%{artist}%",)).fetchall()
    return [r[0] for r in rows]


def recommend_show_bill(conn, artist, min_plays=3, max_plays=300,
                        recent_days=90, limit=30):
    """Generate show bill recommendations for an artist.

    Returns list of dicts with: artist, city, cooccurrence, genre_match,
    total_plays, newest_release, score, last_play
    """
    # Get seed artists from shared playlists
    seeds = get_seed_artists_from_playlists(conn, artist)
    if not seeds:
        # Fall back to just genre-based if no playlist data
        seeds = [artist]

    seed_ph = ",".join(["?"] * len(seeds))
    tag_ph = ",".join(["?"] * len(SEED_TAGS))

    rows = conn.execute(f"""
        WITH cooccurrence AS (
            SELECT s2.artist, COUNT(DISTINCT s2.playlist_id) as shared
            FROM spins s1
            JOIN spins s2 ON s1.playlist_id = s2.playlist_id AND s1.artist != s2.artist
            WHERE s1.artist IN ({seed_ph})
            GROUP BY s2.artist COLLATE NOCASE
        ),
        tag_overlap AS (
            SELECT at.artist, COUNT(*) as tag_matches
            FROM artist_tags at
            WHERE at.tag IN ({tag_ph})
            GROUP BY at.artist COLLATE NOCASE
        ),
        all_plays AS (
            SELECT s.artist, COUNT(*) as total_plays, MAX(p.show_date) as last_play
            FROM spins s JOIN playlists p ON s.playlist_id = p.playlist_id
            GROUP BY s.artist COLLATE NOCASE
        ),
        recent_release AS (
            SELECT artist, MAX(release_year) as newest
            FROM album_years WHERE release_year > 0
            GROUP BY artist COLLATE NOCASE
        )
        SELECT a.artist,
               COALESCE(c.shared, 0) as cooccurrence,
               COALESCE(t.tag_matches, 0) as genre_match,
               a.total_plays,
               a.last_play,
               al.begin_area,
               COALESCE(rr.newest, 0) as newest_release,
               (COALESCE(c.shared, 0) * 3
                + COALESCE(t.tag_matches, 0) * 8
                + CASE WHEN COALESCE(rr.newest, 0) >= 2024 THEN 20
                       WHEN COALESCE(rr.newest, 0) >= 2020 THEN 10 ELSE 0 END
                - CASE WHEN a.total_plays > 200 THEN 30
                       WHEN a.total_plays > 100 THEN 15 ELSE 0 END
               ) as score
        FROM all_plays a
        JOIN artist_locations al ON a.artist = al.artist COLLATE NOCASE
        LEFT JOIN cooccurrence c ON a.artist = c.artist COLLATE NOCASE
        LEFT JOIN tag_overlap t ON a.artist = t.artist COLLATE NOCASE
        LEFT JOIN recent_release rr ON a.artist = rr.artist COLLATE NOCASE
        WHERE al.is_local = 1
          AND a.total_plays BETWEEN ? AND ?
          AND a.artist NOT LIKE ? COLLATE NOCASE
          AND a.artist NOT IN ({seed_ph})
        ORDER BY score DESC
        LIMIT ?
    """, seeds + SEED_TAGS + [min_plays, max_plays, f"%{artist}%"] + seeds + [limit]).fetchall()

    return [
        {
            "artist": r[0],
            "cooccurrence": r[1],
            "genre_match": r[2],
            "total_plays": r[3],
            "last_play": r[4],
            "city": r[5] or "",
            "newest_release": r[6] if r[6] > 0 else None,
            "score": r[7],
        }
        for r in rows
    ]

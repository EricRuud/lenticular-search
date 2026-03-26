"""Show bill recommendation engine.

Given a seed artist, find local bands that would work well on a show bill,
using co-occurrence, genre overlap, recency, and bookability signals.
"""

from db import get_connection

# Genre tags that define the indie/psych/art-pop neighborhood
POSITIVE_TAGS = [
    'indie rock', 'indie pop', 'rock', 'singer-songwriter', 'alternative rock',
    'art pop', 'folk', 'freak folk', 'dream pop', 'psychedelic rock',
    'garage rock', 'lo-fi', 'shoegaze', 'surf rock', 'jangle pop',
    'post-punk', 'new wave', 'experimental rock', 'noise pop',
    'indie', 'psychedelic', 'experimental', 'krautrock', 'art rock',
    'psychedelic pop', 'noise pop', 'dark wave', 'glitch pop',
    'indietronica', 'chamber pop', 'baroque pop', 'twee pop',
]

# Tags that indicate a bad fit for the bill
NEGATIVE_TAGS = [
    'metal', 'heavy metal', 'thrash metal', 'death metal', 'nu metal',
    'alternative metal', 'funk metal', 'speed metal', 'black metal',
    'hardcore', 'hardcore punk', 'metalcore', 'deathcore',
    'hip hop', 'rap', 'gangsta rap', 'west coast hip hop', 'trap',
    'r&b', 'contemporary r&b', 'soul', 'gospel',
    'country', 'country rock', 'blues rock', 'southern rock',
    'classic rock', 'arena rock',
    'edm', 'house', 'techno', 'trance',
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


def get_taste_djs(conn, seeds, min_seed_artists=3):
    """Find DJs whose playlists contain multiple seed artists."""
    seed_ph = ",".join(["?"] * len(seeds))
    rows = conn.execute(f"""
        SELECT p.dj_name, COUNT(DISTINCT s.artist) as seed_count
        FROM spins s
        JOIN playlists p ON s.playlist_id = p.playlist_id
        WHERE s.artist IN ({seed_ph})
        GROUP BY p.dj_name COLLATE NOCASE
        HAVING seed_count >= ?
        ORDER BY seed_count DESC
    """, seeds + [min_seed_artists]).fetchall()
    return [r[0] for r in rows]


def recommend_show_bill(conn, artist, min_plays=3, max_plays=100,
                        recent_days=90, limit=30):
    """Generate show bill recommendations for an artist.

    Signals:
    - same_set: paired with seed artists in the same DJ set (strongest signal)
    - genre_match: positive genre tag overlap
    - genre_penalty: negative genre tags (metal, hip-hop, etc.)
    - dj_affinity: played by DJs with aligned taste
    - recent_release: bonus for 2020+ releases
    - bookability: penalty for too-famous acts

    Removed: raw co-occurrence (too noisy, just surfaces popular bands)
    """
    seeds = get_seed_artists_from_playlists(conn, artist)
    if not seeds:
        seeds = [artist]

    taste_djs = get_taste_djs(conn, seeds, min_seed_artists=3)

    seed_ph = ",".join(["?"] * len(seeds))
    pos_ph = ",".join(["?"] * len(POSITIVE_TAGS))
    neg_ph = ",".join(["?"] * len(NEGATIVE_TAGS))
    dj_ph = ",".join(["?"] * len(taste_djs)) if taste_djs else "''"

    params = (seeds + seeds
              + POSITIVE_TAGS + NEGATIVE_TAGS
              + (taste_djs if taste_djs else [])
              + [min_plays, max_plays, f"%{artist}%"]
              + seeds + [limit])

    rows = conn.execute(f"""
        WITH same_set AS (
            SELECT s2.artist,
                   COUNT(DISTINCT s1.playlist_id) as set_count,
                   COUNT(DISTINCT s1.artist) as seed_variety
            FROM spins s1
            JOIN spins s2 ON s1.playlist_id = s2.playlist_id
                          AND s1.artist != s2.artist COLLATE NOCASE
            WHERE s1.artist IN ({seed_ph})
              AND s2.artist NOT IN ({seed_ph})
            GROUP BY s2.artist COLLATE NOCASE
        ),
        pos_tags AS (
            SELECT at.artist, COUNT(*) as tag_matches
            FROM artist_tags at
            WHERE at.tag IN ({pos_ph})
            GROUP BY at.artist COLLATE NOCASE
        ),
        neg_tags AS (
            SELECT at.artist, COUNT(*) as bad_matches
            FROM artist_tags at
            WHERE at.tag IN ({neg_ph})
            GROUP BY at.artist COLLATE NOCASE
        ),
        dj_affinity AS (
            SELECT s.artist, COUNT(DISTINCT p.dj_name) as dj_count
            FROM spins s
            JOIN playlists p ON s.playlist_id = p.playlist_id
            WHERE p.dj_name IN ({dj_ph})
            GROUP BY s.artist COLLATE NOCASE
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
               COALESCE(ss.seed_variety, 0) as seed_variety,
               COALESCE(pt.tag_matches, 0) as genre_match,
               a.total_plays,
               a.last_play,
               al.begin_area,
               COALESCE(rr.newest, 0) as newest_release,
               (COALESCE(ss.seed_variety, 0) * 6
                + COALESCE(pt.tag_matches, 0) * 8
                - COALESCE(nt.bad_matches, 0) * 15
                + COALESCE(dj.dj_count, 0) * 5
                + CASE WHEN COALESCE(rr.newest, 0) >= 2024 THEN 20
                       WHEN COALESCE(rr.newest, 0) >= 2020 THEN 10 ELSE 0 END
                - CASE WHEN a.total_plays > 200 THEN 30
                       WHEN a.total_plays > 100 THEN 15 ELSE 0 END
               ) as score
        FROM all_plays a
        JOIN artist_locations al ON a.artist = al.artist COLLATE NOCASE
        LEFT JOIN same_set ss ON a.artist = ss.artist COLLATE NOCASE
        LEFT JOIN pos_tags pt ON a.artist = pt.artist COLLATE NOCASE
        LEFT JOIN neg_tags nt ON a.artist = nt.artist COLLATE NOCASE
        LEFT JOIN dj_affinity dj ON a.artist = dj.artist COLLATE NOCASE
        LEFT JOIN recent_release rr ON a.artist = rr.artist COLLATE NOCASE
        WHERE al.is_local = 1
          AND a.total_plays BETWEEN ? AND ?
          AND a.artist NOT LIKE ? COLLATE NOCASE
          AND a.artist NOT IN ({seed_ph})
        ORDER BY score DESC
        LIMIT ?
    """, params).fetchall()

    from venues import is_venue_confirmed

    results = []
    for r in rows:
        venue_confirmed = is_venue_confirmed(r[0])
        final_score = r[7] + (25 if venue_confirmed else 0)
        results.append({
            "artist": r[0],
            "seed_variety": r[1],
            "genre_match": r[2],
            "total_plays": r[3],
            "last_play": r[4],
            "city": r[5] or "",
            "newest_release": r[6] if r[6] > 0 else None,
            "score": final_score,
            "venue_confirmed": venue_confirmed,
        })

    results.sort(key=lambda x: -x["score"])
    return results

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
# Dreamy/psych aesthetic keywords in song/album titles
AESTHETIC_KEYWORDS = [
    'dream', 'cloud', 'moon', 'cosmic', 'mystic', 'crystal',
    'sun', 'star', 'ocean', 'mountain', 'heaven', 'ghost', 'fog',
    'haze', 'shimmer', 'glow', 'echo', 'kaleidoscope', 'prism',
    'flower', 'garden', 'rainbow', 'aurora', 'nebula', 'astral',
    'ethereal', 'twilight', 'velvet', 'honey', 'meadow',
]

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

# Bands that score high due to co-occurrence but clearly don't fit the aesthetic.
# Manually curated through iteration — these keep surfacing despite negative tags.
EXCLUDE_ARTISTS = {
    'deftones', 'cake', 'daniel johnston', 'jefferson airplane',
    'sprints',  # Dublin, not Bay Area
    'sparklehorse',  # inactive (Mark Linkous passed away)
    'lucy dacus',  # Richmond VA, not Bay Area
    'pacing',  # last release 2015, likely inactive
}


# Bands that Bandcamp's algorithm recommends to Lenticular Clouds fans.
BANDCAMP_SIMILAR = {
    'Sugar Candy Mountain',  # Oakland, psych pop
    'Moon Duo',              # SF, psych rock
    'somesurprises',         # Seattle, shoegaze/dream pop
    'The Birds I Heard',     # Bay Area, harmonies
    'Imp of Perverse',       # Texas, bedroom pop
    'Junk Drawer',           # Belfast, art rock
    'The Minus 5',           # Portland, indie pop
}

# Bands that have shared real-world bills with similar artists
# (from Songkick data for Sugar Candy Mountain, Moon Duo, Wooden Shjips,
#  LSD and the Search for God, Tanukichan, Hot Flash Heat Wave)
LINEUP_PEERS = {
    'Assemble Head in Sunburst Sound', 'Lumerians', 'Asteroid #4',
    'Federale', 'Soft Kill', 'Ringo Deathstarr', 'Enumclaw',
    'Wisp', 'Wand', 'Swimming Bell', 'Skinshape', 'Noelle and the Deserters',
}


# Extra seeds only applied for specific artists we've researched
CURATED_SEEDS = {
    "the lenticular clouds": list(BANDCAMP_SIMILAR) + list(LINEUP_PEERS),
}


def get_seed_artists_from_playlists(conn, artist):
    """Find artists that share playlists with the given artist.

    For bands with only a few plays, also uses their genre tags to find
    similar artists as seeds.
    """
    rows = conn.execute("""
        SELECT s2.artist, COUNT(DISTINCT s2.playlist_id) as shared
        FROM spins s1
        JOIN spins s2 ON s1.playlist_id = s2.playlist_id AND s1.artist != s2.artist
        WHERE s1.artist LIKE ? COLLATE NOCASE
        GROUP BY s2.artist COLLATE NOCASE
        ORDER BY shared DESC
        LIMIT 20
    """, (f"%{artist}%",)).fetchall()
    playlist_seeds = [r[0] for r in rows]

    # If very few playlist seeds, supplement with genre-similar artists
    if len(playlist_seeds) < 5:
        # Get this artist's tags
        tags = [r[0] for r in conn.execute(
            "SELECT tag FROM artist_tags WHERE artist LIKE ? COLLATE NOCASE",
            (f"%{artist}%",)
        ).fetchall()]
        if not tags:
            tags = list(POSITIVE_TAGS[:10])  # fallback to generic indie tags
        tag_ph = ",".join(["?"] * len(tags))
        genre_seeds = conn.execute(f"""
            SELECT at.artist, COUNT(*) as overlap
            FROM artist_tags at
            WHERE at.tag IN ({tag_ph}) AND at.artist NOT LIKE ? COLLATE NOCASE
            GROUP BY at.artist COLLATE NOCASE
            ORDER BY overlap DESC
            LIMIT 15
        """, tags + [f"%{artist}%"]).fetchall()
        for r in genre_seeds:
            if r[0] not in playlist_seeds:
                playlist_seeds.append(r[0])

    # Add curated seeds for specifically researched artists
    for extra in CURATED_SEEDS.get(artist.lower(), []):
        if extra not in playlist_seeds:
            playlist_seeds.append(extra)

    return playlist_seeds


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

    aesthetic_clause = " OR ".join(
        [f"s.song LIKE '%{k}%' OR s.album LIKE '%{k}%'" for k in AESTHETIC_KEYWORDS]
    )

    params = (seeds + seeds
              + POSITIVE_TAGS + NEGATIVE_TAGS
              + (taste_djs if taste_djs else [])
              + [min_plays, max_plays, f"%{artist}%"]
              + seeds + list(EXCLUDE_ARTISTS) + [limit])

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
        aesthetic AS (
            SELECT s.artist, COUNT(*) as vibe_hits
            FROM spins s
            WHERE {aesthetic_clause}
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
                + MIN(COALESCE(ae.vibe_hits, 0), 10) * 2
                + CASE WHEN COALESCE(rr.newest, 0) >= 2024 THEN 20
                       WHEN COALESCE(rr.newest, 0) >= 2020 THEN 10 ELSE 0 END
                - CASE WHEN COALESCE(rr.newest, 0) BETWEEN 1 AND 2014 THEN 25 ELSE 0 END
                - CASE WHEN a.total_plays > 200 THEN 30
                       WHEN a.total_plays > 100 THEN 15 ELSE 0 END
               ) as score
        FROM all_plays a
        JOIN artist_locations al ON a.artist = al.artist COLLATE NOCASE
        LEFT JOIN same_set ss ON a.artist = ss.artist COLLATE NOCASE
        LEFT JOIN pos_tags pt ON a.artist = pt.artist COLLATE NOCASE
        LEFT JOIN neg_tags nt ON a.artist = nt.artist COLLATE NOCASE
        LEFT JOIN dj_affinity dj ON a.artist = dj.artist COLLATE NOCASE
        LEFT JOIN aesthetic ae ON a.artist = ae.artist COLLATE NOCASE
        LEFT JOIN recent_release rr ON a.artist = rr.artist COLLATE NOCASE
        WHERE al.is_local = 1
          AND a.total_plays BETWEEN ? AND ?
          AND a.artist NOT LIKE ? COLLATE NOCASE
          AND a.artist NOT IN ({seed_ph})
          AND LOWER(a.artist) NOT IN ({",".join(["?" for _ in EXCLUDE_ARTISTS])})
        ORDER BY score DESC
        LIMIT ?
    """, params).fetchall()

    from venues import is_venue_confirmed

    # Second pass: compute inter-recommendation connections (scene tightness)
    artist_names = [r[0] for r in rows]
    scene_scores = {}
    if len(artist_names) >= 2:
        art_ph = ",".join(["?"] * len(artist_names))
        for artist in artist_names:
            conn_count = conn.execute(f"""
                SELECT COUNT(DISTINCT s2.artist)
                FROM spins s1
                JOIN spins s2 ON s1.playlist_id = s2.playlist_id
                  AND s1.artist != s2.artist COLLATE NOCASE
                WHERE s1.artist = ? COLLATE NOCASE
                  AND s2.artist IN ({art_ph})
            """, [artist] + artist_names).fetchone()[0]
            scene_scores[artist.lower()] = conn_count

    results = []
    for r in rows:
        venue_confirmed = is_venue_confirmed(r[0])
        scene_bonus = min(scene_scores.get(r[0].lower(), 0), 15) * 2
        final_score = r[7] + (25 if venue_confirmed else 0) + scene_bonus

        # Fetch genre tags for display
        tags = [t[0] for t in conn.execute(
            "SELECT tag FROM artist_tags WHERE artist = ? COLLATE NOCASE ORDER BY score DESC LIMIT 4",
            (r[0],)
        ).fetchall()]

        results.append({
            "artist": r[0],
            "seed_variety": r[1],
            "genre_match": r[2],
            "total_plays": r[3],
            "last_play": r[4],
            "city": r[5] or "",
            "newest_release": r[6] if r[6] > 0 else None,
            "venue_confirmed": venue_confirmed,
            "tags": tags,
        })

    results.sort(key=lambda x: -(x["genre_match"] * 8 + x["seed_variety"] * 6 + (25 if x["venue_confirmed"] else 0) + scene_scores.get(x["artist"].lower(), 0) * 2))
    return results

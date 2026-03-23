#!/usr/bin/env python3
"""Background backfill — iterates day-by-day (today backwards), station-by-station.

Starts the web server immediately; data appears as it's ingested.
"""

import sys
import time
import traceback
from datetime import datetime, timedelta

from db import get_connection, get_db_stats, store_playlist, get_stored_playlist_ids
from kalx import (
    DEFAULT_STATIONS, SPINITRON_STATIONS,
    get_playlist_ids_for_range, fetch_playlist,
)

BACKFILL_DAYS = 30
TAG_LIMIT = 200


def backfill():
    conn = get_connection()
    stats = get_db_stats(conn)
    print(f"[backfill] DB: {stats['playlists']} playlists, {stats['spins']} spins", flush=True)

    today = datetime.now().date()

    for days_ago in range(BACKFILL_DAYS):
        target_date = today - timedelta(days=days_ago)

        for station in DEFAULT_STATIONS:
            try:
                # Get playlist IDs for this single day + station
                if station in SPINITRON_STATIONS:
                    entries = get_playlist_ids_for_range(target_date, target_date, station)
                    fetch_fn = lambda pid, st=station: fetch_playlist(pid, st)
                elif station == "BFF.fm":
                    import bff
                    entries = bff.get_playlist_ids_for_range(target_date, target_date)
                    fetch_fn = bff.fetch_playlist
                else:
                    continue

                # Skip already-stored playlists
                existing = get_stored_playlist_ids(conn, target_date, target_date, station)
                to_fetch = [e for e in entries if e["id"] not in existing]

                if not to_fetch:
                    continue

                print(f"[backfill] {target_date} {station}: {len(to_fetch)} new playlists", flush=True)

                for entry in to_fetch:
                    try:
                        playlist = fetch_fn(entry["id"])
                        if playlist:
                            store_playlist(conn, playlist)
                    except Exception:
                        pass  # skip individual failures

            except Exception as exc:
                print(f"[backfill] {target_date} {station}: error - {exc}", flush=True)
                time.sleep(2)

        if days_ago % 5 == 0 and days_ago > 0:
            stats = get_db_stats(conn)
            print(f"[backfill] Progress: {stats['playlists']} playlists, {stats['spins']} spins", flush=True)

    # Tag artists after data is loaded
    print("[backfill] Tagging artists...", flush=True)
    try:
        from db import get_untagged_artists, store_artist_tags
        import requests

        untagged = get_untagged_artists(conn, limit=TAG_LIMIT)
        tagged = 0
        for artist, _ in untagged:
            try:
                time.sleep(1.1)
                resp = requests.get(
                    "https://musicbrainz.org/ws/2/artist/",
                    params={"query": f'artist:"{artist}"', "fmt": "json", "limit": "1"},
                    headers={"User-Agent": "RadioPlaylistSearch/1.0 (genre-tagging)"},
                    timeout=10,
                )
                if resp.ok:
                    data = resp.json()
                    if data.get("artists"):
                        tags = [(t["name"].lower(), t.get("count", 0))
                                for t in data["artists"][0].get("tags", [])]
                        if tags:
                            store_artist_tags(conn, artist, tags)
                            tagged += 1
            except Exception:
                pass
        print(f"[backfill] Tagged {tagged} artists", flush=True)
    except Exception as exc:
        print(f"[backfill] Tagging error: {exc}", flush=True)

    stats = get_db_stats(conn)
    conn.close()
    print(f"[backfill] Done. {stats['playlists']} playlists, {stats['spins']} spins", flush=True)


if __name__ == "__main__":
    print("[backfill] Starting background data backfill...", flush=True)
    try:
        backfill()
    except Exception:
        traceback.print_exc()

#!/usr/bin/env python3
"""Background backfill — iterates day-by-day (today backwards), station-by-station.

Starts the web server immediately; data appears as it's ingested.
Writes status to a JSON file so the web UI can display progress.
"""

import json
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from db import (
    DB_PATH, get_connection, get_db_stats, store_playlist,
    get_stored_playlist_ids, get_untagged_artists, store_artist_tags,
)
from kalx import (
    DEFAULT_STATIONS, SPINITRON_STATIONS,
    get_playlist_ids_for_range, fetch_playlist,
)

BACKFILL_DAYS = 30
TAG_LIMIT = 200
STATUS_FILE = DB_PATH.parent / "backfill_status.json"


def write_status(status):
    """Write current backfill status to a JSON file."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status))


def backfill():
    conn = get_connection()
    stats = get_db_stats(conn)
    print(f"[backfill] DB: {stats['playlists']} playlists, {stats['spins']} spins", flush=True)

    today = datetime.now().date()
    total_fetched = 0
    total_errors = 0
    start_time = time.time()

    write_status({
        "running": True,
        "phase": "playlists",
        "days_done": 0,
        "days_total": BACKFILL_DAYS,
        "current_date": str(today),
        "current_station": "",
        "playlists_fetched": 0,
        "errors": 0,
        "started_at": datetime.now().isoformat(),
    })

    for days_ago in range(BACKFILL_DAYS):
        target_date = today - timedelta(days=days_ago)

        for station in DEFAULT_STATIONS:
            try:
                if station in SPINITRON_STATIONS:
                    entries = get_playlist_ids_for_range(target_date, target_date, station)
                    fetch_fn = lambda pid, st=station: fetch_playlist(pid, st)
                elif station == "BFF.fm":
                    import bff
                    entries = bff.get_playlist_ids_for_range(target_date, target_date)
                    fetch_fn = bff.fetch_playlist
                else:
                    continue

                existing = get_stored_playlist_ids(conn, target_date, target_date, station)
                to_fetch = [e for e in entries if e["id"] not in existing]

                if not to_fetch:
                    continue

                print(f"[backfill] {target_date} {station}: {len(to_fetch)} new playlists", flush=True)

                for j, entry in enumerate(to_fetch):
                    write_status({
                        "running": True,
                        "phase": "playlists",
                        "days_done": days_ago,
                        "days_total": BACKFILL_DAYS,
                        "current_date": str(target_date),
                        "current_station": station,
                        "station_progress": f"{j+1}/{len(to_fetch)}",
                        "playlists_fetched": total_fetched,
                        "errors": total_errors,
                        "started_at": datetime.fromtimestamp(start_time).isoformat(),
                        "elapsed_seconds": int(time.time() - start_time),
                    })
                    try:
                        playlist = fetch_fn(entry["id"])
                        if playlist:
                            store_playlist(conn, playlist)
                            total_fetched += 1
                    except Exception:
                        total_errors += 1

            except Exception as exc:
                total_errors += 1
                print(f"[backfill] {target_date} {station}: error - {exc}", flush=True)
                time.sleep(2)

        if days_ago % 5 == 0:
            stats = get_db_stats(conn)
            print(f"[backfill] Day {days_ago}/{BACKFILL_DAYS}: {stats['playlists']} playlists, {stats['spins']} spins", flush=True)

    # Tag artists
    print("[backfill] Tagging artists...", flush=True)
    write_status({
        "running": True,
        "phase": "tagging",
        "playlists_fetched": total_fetched,
        "errors": total_errors,
        "started_at": datetime.fromtimestamp(start_time).isoformat(),
        "elapsed_seconds": int(time.time() - start_time),
    })

    try:
        import requests
        untagged = get_untagged_artists(conn, limit=TAG_LIMIT)
        tagged = 0
        for i, (artist, _) in enumerate(untagged):
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
            if (i + 1) % 25 == 0:
                write_status({
                    "running": True,
                    "phase": "tagging",
                    "artists_tagged": tagged,
                    "artists_total": len(untagged),
                    "playlists_fetched": total_fetched,
                    "started_at": datetime.fromtimestamp(start_time).isoformat(),
                    "elapsed_seconds": int(time.time() - start_time),
                })
        print(f"[backfill] Tagged {tagged} artists", flush=True)
    except Exception as exc:
        print(f"[backfill] Tagging error: {exc}", flush=True)

    stats = get_db_stats(conn)
    conn.close()
    elapsed = int(time.time() - start_time)
    write_status({
        "running": False,
        "phase": "done",
        "playlists_fetched": total_fetched,
        "errors": total_errors,
        "elapsed_seconds": elapsed,
        "finished_at": datetime.now().isoformat(),
    })
    print(f"[backfill] Done in {elapsed}s. {stats['playlists']} playlists, {stats['spins']} spins", flush=True)


def refresh_today():
    """Quick refresh — fetch just today and yesterday for all stations."""
    conn = get_connection()
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    for target_date in [today, yesterday]:
        for station in DEFAULT_STATIONS:
            try:
                if station in SPINITRON_STATIONS:
                    entries = get_playlist_ids_for_range(target_date, target_date, station)
                    fetch_fn = lambda pid, st=station: fetch_playlist(pid, st)
                elif station == "BFF.fm":
                    import bff
                    entries = bff.get_playlist_ids_for_range(target_date, target_date)
                    fetch_fn = bff.fetch_playlist
                else:
                    continue

                existing = get_stored_playlist_ids(conn, target_date, target_date, station)
                to_fetch = [e for e in entries if e["id"] not in existing]
                for entry in to_fetch:
                    try:
                        playlist = fetch_fn(entry["id"])
                        if playlist:
                            store_playlist(conn, playlist)
                    except Exception:
                        pass
            except Exception:
                pass

    conn.close()


UPDATE_INTERVAL = 30 * 60  # 30 minutes


if __name__ == "__main__":
    print("[backfill] Starting background data backfill...", flush=True)
    try:
        backfill()
    except Exception:
        traceback.print_exc()
        write_status({"running": False, "phase": "error", "error": traceback.format_exc()})

    # Keep running — refresh new data every 30 minutes
    print(f"[backfill] Entering refresh loop (every {UPDATE_INTERVAL // 60} min)...", flush=True)
    while True:
        time.sleep(UPDATE_INTERVAL)
        try:
            print("[backfill] Refreshing today's data...", flush=True)
            refresh_today()
            stats = get_db_stats(get_connection())
            print(f"[backfill] Refresh done. {stats['playlists']} playlists, {stats['spins']} spins", flush=True)
            write_status({
                "running": False,
                "phase": "idle",
                "last_refresh": datetime.now().isoformat(),
                "next_refresh": (datetime.now() + timedelta(seconds=UPDATE_INTERVAL)).isoformat(),
            })
        except Exception as exc:
            print(f"[backfill] Refresh error: {exc}", flush=True)

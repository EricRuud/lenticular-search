#!/usr/bin/env python3
"""Spinitron playlist scraper for college/community radio stations.

Search play history for specific artists across a date range.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SPINITRON_BASE = "https://widgets.spinitron.com"
STATIONS = {
    "KALX": "KALX 90.7 FM Berkeley",
    "KDVS": "KDVS 90.3 FM Davis",
    "KPFA": "KPFA 94.1 FM Berkeley",
    "KSJS": "KSJS 90.5 FM San Jose",
    "KPOO": "KPOO 89.5 FM San Francisco",
    "BFF.fm": "BFF.fm San Francisco",
}
# Stations that use Spinitron (vs custom API)
SPINITRON_STATIONS = {"KALX", "KDVS", "KPFA", "KSJS", "KPOO"}
DEFAULT_STATIONS = ["KALX", "KDVS", "BFF.fm", "KPFA", "KSJS", "KPOO"]
HEADERS = {"User-Agent": "Spinitron-Playlist-Search/1.0"}
CACHE_DIR = Path.home() / ".cache" / "kalx"
REQUEST_DELAY = 0.3  # seconds between requests (global rate limit)
_fetch_lock = threading.Lock()
_last_fetch_time = 0.0


def fetch(url):
    """Fetch a URL with rate limiting and caching."""
    global _last_fetch_time
    cache_key = re.sub(r"[^\w]", "_", url)
    cache_path = CACHE_DIR / f"{cache_key}.html"

    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 3600:  # cache for 1 hour
            return cache_path.read_text()

    # Global rate limit across all threads
    with _fetch_lock:
        elapsed = time.time() - _last_fetch_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        _last_fetch_time = time.time()

    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(resp.text)
    return resp.text


def parse_playlist(html, playlist_id=None, station=None):
    """Parse a playlist page and return metadata + spins."""
    soup = BeautifulSoup(html, "html.parser")

    # Show title
    h3 = soup.find("h3", class_="show-title")
    show_name = h3.get_text(strip=True) if h3 else "Unknown Show"

    # DJ name (match any station prefix in the dj link)
    dj_link = soup.find("a", href=re.compile(r"/\w+/dj/\d+"))
    dj_name = dj_link.get_text(strip=True) if dj_link else "Unknown DJ"

    # Date/time
    timeslot = soup.find("p", class_="timeslot")
    date_str = ""
    show_date = None
    if timeslot:
        date_str = timeslot.get_text(strip=True)
        # Parse the date: "Mar 22, 2026 8:00 AM – 10:00 AM"
        match = re.search(r"(\w+ \d+, \d{4})", date_str)
        if match:
            show_date = datetime.strptime(match.group(1), "%b %d, %Y").date()

    # Spins
    spins = []
    spins_div = soup.find(id="public-spins-0")
    if spins_div:
        for row in spins_div.find_all("tr", class_="spin-item"):
            spin = parse_spin_row(row)
            if spin:
                spins.append(spin)

    return {
        "playlist_id": playlist_id,
        "show_name": show_name,
        "dj_name": dj_name,
        "date_str": date_str,
        "date": show_date,
        "spins": spins,
    }


def parse_spin_row(row):
    """Parse a single spin table row."""
    # The data-spin attribute has structured JSON
    data_spin = row.get("data-spin")
    if data_spin:
        try:
            d = json.loads(data_spin)
            artist = d.get("a", "")
            song = d.get("s", "")
            album = d.get("r", "")
        except json.JSONDecodeError:
            artist = song = album = ""
    else:
        artist = song = album = ""

    # Fall back to HTML parsing if data-spin is missing
    if not artist:
        artist_span = row.find("span", class_="artist")
        artist = artist_span.get_text(strip=True) if artist_span else ""
    if not song:
        song_span = row.find("span", class_="song")
        song = song_span.get_text(strip=True) if song_span else ""
    if not album:
        release_span = row.find("span", class_="release")
        album = release_span.get_text(strip=True) if release_span else ""

    # Label
    label_span = row.find("span", class_="label")
    label = label_span.get_text(strip=True) if label_span else ""

    # Time
    time_cell = row.find("td", class_="spin-time")
    spin_time = time_cell.get_text(strip=True) if time_cell else ""

    return {
        "time": spin_time,
        "artist": artist,
        "song": song,
        "album": album,
        "label": label,
    }


def get_playlist_ids_for_range(start_date, end_date, station="KALX"):
    """Get playlist IDs in a date range using the calendar feed API.

    Chunks into 28-day windows since the API rejects ranges > ~30 days.
    """
    url = f"{SPINITRON_BASE}/{station}/calendar-feed"
    playlist_ids = []
    seen_ids = set()

    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(chunk_start + timedelta(days=27), end_date)
        params = {
            "timeslot": "15",
            "start": chunk_start.isoformat(),
            "end": (chunk_end + timedelta(days=1)).isoformat(),
        }
        time.sleep(REQUEST_DELAY)
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        for entry in resp.json():
            if entry["id"] not in seen_ids:
                seen_ids.add(entry["id"])
                playlist_ids.append({
                    "id": entry["id"],
                    "title": entry.get("title", ""),
                    "dj": entry.get("text", ""),
                    "start": entry.get("start", ""),
                    "station": station,
                })

        chunk_start = chunk_end + timedelta(days=1)

    return playlist_ids


def fetch_playlist(playlist_id, station="KALX"):
    """Fetch and parse a single playlist by ID."""
    url = f"{SPINITRON_BASE}/{station}/pl/{playlist_id}/"
    html = fetch(url)
    if not html:
        return None
    result = parse_playlist(html, playlist_id, station)
    result["station"] = station
    return result


def _check_playlist(entry, query, start_date, end_date):
    """Fetch one playlist and check for matching spins. Returns (result, playlist_id)."""
    query_lower = query.lower()
    playlist = fetch_playlist(entry["id"], entry.get("station", "KALX"))
    if playlist is None:
        return None

    if playlist["date"] and (playlist["date"] < start_date or playlist["date"] > end_date):
        return None

    matching_spins = [s for s in playlist["spins"] if query_lower in s["artist"].lower()]
    if not matching_spins:
        return None

    return {
        "playlist_id": playlist["playlist_id"],
        "show_name": playlist["show_name"],
        "dj_name": playlist["dj_name"],
        "date_str": playlist["date_str"],
        "date": playlist["date"],
        "spins": matching_spins,
    }


def search_playlists(query, start_date, end_date, on_progress=None, on_result=None):
    """Search playlists in the date range for an artist.

    on_progress(checked, total) - called after each playlist is checked.
    on_result(result) - called when a match is found.
    """
    print(f"Fetching playlist schedule for {start_date} to {end_date}...",
          file=sys.stderr)

    entries = get_playlist_ids_for_range(start_date, end_date)
    total = len(entries)
    print(f"Found {total} playlists to check.", file=sys.stderr)

    results = []
    checked = 0

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_check_playlist, entry, query, start_date, end_date): entry
            for entry in entries
        }
        for future in as_completed(futures):
            checked += 1
            result = future.result()
            if result:
                results.append(result)
                if on_result:
                    on_result(result)
            if on_progress:
                on_progress(checked, total)
            elif checked % 10 == 0:
                print(f"  Checked {checked}/{total} playlists...", file=sys.stderr)

    print(f"Done. Checked {total} playlists.", file=sys.stderr)
    return results


def print_results(results, query):
    """Print search results as a formatted table."""
    if not results:
        print(f'\nNo plays found for "{query}".')
        return

    total_spins = sum(len(r["spins"]) for r in results)
    print(f'\nFound {total_spins} play(s) of "{query}" '
          f"across {len(results)} show(s):\n")

    # Header
    print(f"{'Station':<7} {'Date':<14} {'Time':<10} {'DJ':<20} {'Show':<25} {'Song':<30} {'Album'}")
    print("-" * 130)

    for result in sorted(results, key=lambda r: (r["date"], r.get("station", ""))):
        for spin in result["spins"]:
            date_short = result["date"].strftime("%a %m/%d") if result["date"] else "?"
            station = result.get("station", "KALX")
            print(
                f"{station:<7} "
                f"{date_short:<14} "
                f"{spin['time']:<10} "
                f"{result['dj_name']:<20.20} "
                f"{result['show_name']:<25.25} "
                f"{spin['song']:<30.30} "
                f"{spin['album']}"
            )


def _parse_date_range(args):
    """Parse date range from CLI args."""
    if args.days:
        start_date = (datetime.now() - timedelta(days=args.days)).date()
        end_date = datetime.now().date()
    elif args.after:
        start_date = datetime.strptime(args.after, "%Y-%m-%d").date()
        end_date = (
            datetime.strptime(args.before, "%Y-%m-%d").date()
            if args.before
            else datetime.now().date()
        )
    else:
        # Default: last 7 days
        start_date = (datetime.now() - timedelta(days=7)).date()
        end_date = datetime.now().date()
    return start_date, end_date


def cmd_search(args):
    """Handle the 'search' command."""
    from db import get_connection, search_db

    start_date, end_date = _parse_date_range(args)
    stations = args.station if args.station else None
    conn = get_connection()
    results = search_db(conn, args.artist, start_date, end_date, stations=stations)
    conn.close()
    print_results(results, args.artist)


def cmd_recent(args):
    """Handle the 'recent' command."""
    html = fetch(BASE_URL + "/")
    if not html:
        print("Error: Could not fetch KALX main page.", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(html, "html.parser")
    recent = soup.find("div", class_="recent-playlists")
    if not recent:
        print("Could not find recent playlists section.")
        return

    print("Recent KALX playlists:\n")
    print(f"{'Time':<12} {'Show':<30} {'DJ':<20} {'ID'}")
    print("-" * 75)

    for row in recent.find_all("tr"):
        time_cell = row.find("td", class_="show-time")
        show_time = time_cell.get_text(strip=True) if time_cell else ""

        pl_link = row.find("a", href=re.compile(r"/KALX/pl/\d+"))
        if not pl_link:
            continue
        show_name = pl_link.get_text(strip=True)
        match = re.search(r"/KALX/pl/(\d+)", pl_link["href"])
        pl_id = match.group(1) if match else ""

        dj_link = row.find("a", href=re.compile(r"/KALX/dj/"))
        dj_name = dj_link.get_text(strip=True) if dj_link else ""

        print(f"{show_time:<12} {show_name:<30.30} {dj_name:<20.20} {pl_id}")


def cmd_build_db(args):
    """Handle the 'build-db' command."""
    from db import get_connection, store_playlist, get_stored_playlist_ids, get_db_stats

    start_date, end_date = _parse_date_range(args)
    stations = args.station if args.station else DEFAULT_STATIONS

    conn = get_connection()

    for station in stations:
        print(f"\n[{station}] Fetching playlist schedule...")

        if station in SPINITRON_STATIONS:
            entries = get_playlist_ids_for_range(start_date, end_date, station)
            fetch_fn = lambda pid, st=station: fetch_playlist(pid, st)
        elif station == "BFF.fm":
            import bff
            entries = bff.get_playlist_ids_for_range(start_date, end_date)
            fetch_fn = bff.fetch_playlist
        else:
            print(f"[{station}] Unknown station type, skipping.")
            continue

        existing = get_stored_playlist_ids(conn, start_date, end_date, station)
        to_fetch = [e for e in entries if e["id"] not in existing]
        print(f"[{station}] Found {len(entries)} playlists, {len(existing)} already in DB, "
              f"fetching {len(to_fetch)}...")

        if not to_fetch:
            print(f"[{station}] Up to date.")
            continue

        fetched = 0
        errors = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fetch_fn, e["id"]): e for e in to_fetch}
            for future in as_completed(futures):
                fetched += 1
                try:
                    playlist = future.result()
                    if playlist:
                        store_playlist(conn, playlist)
                except Exception:
                    errors += 1
                if fetched % 25 == 0 or fetched == len(to_fetch):
                    print(f"  [{station}] {fetched}/{len(to_fetch)} fetched ({errors} errors)")

    stats = get_db_stats(conn)
    conn.close()
    print(f"\nDone. DB: {stats['playlists']} playlists, {stats['spins']} spins "
          f"({stats['min_date']} to {stats['max_date']})")


def cmd_tag_artists(args):
    """Fetch genre tags from MusicBrainz for untagged artists."""
    from db import get_connection, get_untagged_artists, store_artist_tags

    conn = get_connection()
    untagged = get_untagged_artists(conn, limit=args.limit)
    print(f"Found {len(untagged)} untagged artists (by play count).")

    tagged = 0
    errors = 0
    for i, (artist, play_count) in enumerate(untagged):
        try:
            time.sleep(1.1)  # MusicBrainz rate limit: 1 req/sec
            resp = requests.get(
                "https://musicbrainz.org/ws/2/artist/",
                params={"query": f'artist:"{artist}"', "fmt": "json", "limit": "1"},
                headers={"User-Agent": "RadioPlaylistSearch/1.0 (genre-tagging)"},
                timeout=10,
            )
            if resp.ok:
                data = resp.json()
                if data.get("artists"):
                    mb_artist = data["artists"][0]
                    tags = [
                        (t["name"].lower(), t.get("count", 0))
                        for t in mb_artist.get("tags", [])
                    ]
                    if tags:
                        store_artist_tags(conn, artist, tags)
                        tagged += 1
        except Exception:
            errors += 1

        if (i + 1) % 25 == 0 or (i + 1) == len(untagged):
            print(f"  {i + 1}/{len(untagged)} checked, {tagged} tagged, {errors} errors")

    conn.close()
    print(f"Done. Tagged {tagged} artists.")


def cmd_playlist(args):
    """Handle the 'playlist' command."""
    from db import get_connection, get_playlist_from_db

    conn = get_connection()
    playlist = get_playlist_from_db(conn, args.playlist_id)
    conn.close()

    if not playlist:
        playlist = fetch_playlist(args.playlist_id)

    if not playlist:
        print(f"Playlist {args.playlist_id} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"\n{playlist['show_name']}")
    print(f"DJ: {playlist['dj_name']}")
    print(f"{playlist['date_str']}")
    print()

    if not playlist["spins"]:
        print("No spins logged for this playlist.")
        return

    print(f"{'Time':<10} {'Artist':<25} {'Song':<30} {'Album':<30} {'Label'}")
    print("-" * 110)

    for spin in playlist["spins"]:
        print(
            f"{spin['time']:<10} "
            f"{spin['artist']:<25.25} "
            f"{spin['song']:<30.30} "
            f"{spin['album']:<30.30} "
            f"{spin['label']}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Search KALX 90.7FM play history on Spinitron"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    station_names = ", ".join(STATIONS.keys())

    # search
    sp_search = subparsers.add_parser("search", help="Search for an artist")
    sp_search.add_argument("artist", help="Artist name to search for")
    sp_search.add_argument("--after", help="Start date (YYYY-MM-DD)")
    sp_search.add_argument("--before", help="End date (YYYY-MM-DD)")
    sp_search.add_argument("--days", type=int, help="Search last N days")
    sp_search.add_argument("--station", nargs="*", choices=STATIONS.keys(),
                           help=f"Stations to search (default: all in DB). Options: {station_names}")
    sp_search.set_defaults(func=cmd_search)

    # build-db
    sp_build = subparsers.add_parser("build-db", help="Build/update the local database")
    sp_build.add_argument("--after", help="Start date (YYYY-MM-DD)")
    sp_build.add_argument("--before", help="End date (YYYY-MM-DD)")
    sp_build.add_argument("--days", type=int, default=180, help="Fetch last N days (default: 180)")
    sp_build.add_argument("--station", nargs="*", choices=STATIONS.keys(),
                          help=f"Stations to fetch (default: {', '.join(DEFAULT_STATIONS)}). Options: {station_names}")
    sp_build.set_defaults(func=cmd_build_db)

    # tag-artists
    sp_tag = subparsers.add_parser("tag-artists", help="Fetch genre tags from MusicBrainz")
    sp_tag.add_argument("--limit", type=int, default=500, help="Max artists to tag (default: 500)")
    sp_tag.set_defaults(func=cmd_tag_artists)

    # recent
    sp_recent = subparsers.add_parser("recent", help="List recent playlists")
    sp_recent.set_defaults(func=cmd_recent)

    # playlist
    sp_playlist = subparsers.add_parser("playlist", help="Show spins for a playlist")
    sp_playlist.add_argument("playlist_id", type=int, help="Playlist ID")
    sp_playlist.set_defaults(func=cmd_playlist)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

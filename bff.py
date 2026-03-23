"""BFF.fm API adapter.

Produces the same data structures as the Spinitron scraper so both
can feed into the shared database.
"""

import time
from datetime import datetime, timedelta, date

import requests

BASE_URL = "https://bff.fm/api"
HEADERS = {"User-Agent": "Spinitron-Playlist-Search/1.0"}
STATION = "BFF.fm"


def get_playlist_ids_for_range(start_date, end_date):
    """Get all BFF.fm broadcast IDs in a date range.

    The API returns 20 results per request in reverse-chronological order.
    We paginate with offset until we pass the start date.
    """
    entries = []
    offset = 0

    while True:
        time.sleep(0.3)
        resp = requests.get(
            f"{BASE_URL}/broadcasts",
            params={"offset": str(offset)},
            headers=HEADERS,
            timeout=30,
        )
        if not resp.ok:
            break
        data = resp.json()
        if not data:
            break

        past_range = False
        for b in data:
            broadcast_date = None
            if b.get("start"):
                try:
                    broadcast_date = datetime.strptime(b["start"], "%Y-%m-%d %H:%M:%S").date()
                except ValueError:
                    pass

            if broadcast_date and broadcast_date < start_date:
                past_range = True
                break

            if broadcast_date and broadcast_date > end_date:
                continue  # future broadcast, skip

            entries.append({
                "id": int(b["id"]),
                "title": b.get("title", ""),
                "dj": b.get("User", {}).get("display_name", "") if b.get("User") else "",
                "start": b.get("start", ""),
                "station": STATION,
            })

        if past_range:
            break

        offset += len(data)

    return entries


def fetch_playlist(broadcast_id, station=None):
    """Fetch a single BFF.fm broadcast with its tracks."""
    time.sleep(0.3)
    resp = requests.get(
        f"{BASE_URL}/broadcasts/{broadcast_id}",
        headers=HEADERS,
        timeout=30,
    )
    if not resp.ok:
        return None

    b = resp.json()
    if not b:
        return None

    # Parse date
    show_date = None
    date_str = b.get("start", "")
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            show_date = dt.date()
            date_str = dt.strftime("%b %d, %Y %I:%M %p")
        except ValueError:
            pass

    show_title = b.get("Show", {}).get("title", b.get("title", "Unknown Show")) if b.get("Show") else b.get("title", "Unknown Show")
    dj_name = b.get("User", {}).get("display_name", "Unknown DJ") if b.get("User") else "Unknown DJ"

    spins = []
    for t in b.get("tracks", []):
        spin_time = ""
        if t.get("played"):
            try:
                spin_time = datetime.strptime(t["played"], "%Y-%m-%d %H:%M:%S").strftime("%-I:%M %p")
            except ValueError:
                spin_time = t["played"]

        spins.append({
            "time": spin_time,
            "artist": t.get("artist", ""),
            "song": t.get("title", ""),
            "album": t.get("album", ""),
            "label": t.get("label", ""),
        })

    return {
        "playlist_id": int(b["id"]),
        "station": STATION,
        "show_name": show_title,
        "dj_name": dj_name,
        "date_str": date_str,
        "date": show_date,
        "spins": spins,
    }

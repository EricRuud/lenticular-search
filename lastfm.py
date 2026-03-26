"""Last.fm scraper for similar artists and listener counts."""

import time
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (ShowBill/1.0)"}


def get_similar_artists(artist, limit=10):
    """Get similar artists from Last.fm."""
    try:
        slug = artist.replace(" ", "+")
        resp = requests.get(
            f"https://www.last.fm/music/{slug}/+similar",
            headers=HEADERS, timeout=10,
        )
        if not resp.ok:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        names = [h.get_text(strip=True) for h in
                 soup.find_all("h3", class_="similar-artists-item-name")]
        return names[:limit]
    except Exception:
        return []


def get_listener_count(artist):
    """Get Last.fm listener count (audience size proxy)."""
    try:
        slug = artist.replace(" ", "+")
        resp = requests.get(
            f"https://www.last.fm/music/{slug}",
            headers=HEADERS, timeout=10,
        )
        if not resp.ok:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # First abbr with intabbr class is the listener count
        stat = soup.find("abbr", class_="intabbr")
        if stat:
            raw = stat.get("title", stat.get_text(strip=True))
            # Parse "714,579" or "714579" to int
            return int(raw.replace(",", "").strip())
        return None
    except Exception:
        return None

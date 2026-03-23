# KALX Spinitron Playlist Scraper

## Project Goal

Build a CLI tool to search KALX 90.7FM Berkeley's play history on Spinitron for specific artist names across a date range. The primary use case is answering questions like "which DJ played [band name] this week?"

## Architecture

Single Python script (`kalx.py`) using `requests` + `BeautifulSoup`. No API key needed — we scrape the public Spinitron widget pages.

## How Spinitron Serves KALX Data

All data is server-rendered HTML (no JS needed). The key pages:

### Main page: `https://widgets.spinitron.com/KALX/`
- Shows the currently on-air playlist with its spins
- Lists ~5 recent playlists under "Recent" with links
- Lists upcoming shows under "Coming up"

### Individual playlist page: `https://widgets.spinitron.com/KALX/pl/{PLAYLIST_ID}/{SLUG}`
- Contains a table of all spins (songs) for that show
- Each row has: timestamp, "Artist - Song" text, and "Artist Song Album Label" detail text
- The playlist header shows: show name, date/time range, DJ name (linked)
- DJ link format: `https://widgets.spinitron.com/KALX/dj/{DJ_ID}/{DJ-Slug}`

### Calendar page: `https://widgets.spinitron.com/KALX/calendar`
- Shows the weekly schedule grid
- Has not been confirmed to support date query params — may need to discover playlist IDs by other means

### DJ page: `https://widgets.spinitron.com/KALX/dj/{DJ_ID}/{DJ-Slug}`
- Lists all shows by a specific DJ with dates

## Scraping Strategy

1. **Discover playlists for a date range.** Use the calendar feed JSON API at `widgets.spinitron.com/KALX/calendar-feed?timeslot=15&start=YYYY-MM-DD&end=YYYY-MM-DD`. This returns a JSON array of all playlists in the range with their IDs, titles, DJ names, and start times. Note: playlist IDs are NOT sequential for KALX — they're shared across all Spinitron stations with gaps of ~400-800 between KALX entries, so ID iteration is not viable.

2. **For each playlist, extract spins.** Parse the HTML table rows. Each spin row contains:
   - A time link (e.g. "7:52 AM")
   - A combined "Artist - Song" cell
   - A detail cell with: Artist, Song, Album, Label (sometimes marked "New")

3. **Match against search term.** Case-insensitive substring match on the artist field. Report the DJ name, show name, date/time, and the specific spin(s) that matched.

## HTML Structure (observed from real pages)

The playlist page at `widgets.spinitron.com/KALX/pl/{id}/{slug}` contains:

- Show title in `<h3 class="show-title">` inside a link like `/KALX/show/{show_id}/{Show-Name}`
- Date/time in `<p class="timeslot">` like `Mar 22, 2026 8:00 AM – 10:00 AM`
- DJ name in a link like `/KALX/dj/{dj_id}/{DJ-Name}`
- Spin data in `<div id="public-spins-0" class="spins public-spins">` containing a `<table>`
- Each spin is a `<tr class="spin-item">` with a `data-spin` JSON attribute: `{"i":"ISRC","a":"Artist","s":"Song","r":"Album"}`
- Cells: `<td class="spin-time">`, `<td class="spin-art">`, `<td class="spin-text">`
- Inside spin-text: `<span class="artist">`, `<span class="song">`, `<span class="release">`, `<span class="label">`

## CLI Interface

```
# Search this week's playlists for an artist
python kalx.py search "The Lenticular Clouds"

# Search with a specific date range
python kalx.py search "The Lenticular Clouds" --after 2026-03-16 --before 2026-03-23

# Search last N days
python kalx.py search "The Lenticular Clouds" --days 7

# List recent playlists
python kalx.py recent

# Show spins for a specific playlist
python kalx.py playlist 22157411
```

## Implementation Notes

- **Rate limiting**: Add a 1-2 second delay between requests to be respectful. Spinitron rate-limits aggressive crawling.
- **User-Agent**: Set a descriptive User-Agent header like `KALX-Playlist-Search/1.0`.
- **Playlist discovery**: Use the calendar-feed API to get all playlist IDs in a date range. This is fast (single JSON request) and avoids the ID gap problem.
- **Error handling**: Some playlists may have no spins or fail to load. Handle gracefully and continue.
- **Caching**: Consider caching fetched playlists to `~/.cache/kalx/` as JSON to avoid re-fetching on repeated searches.
- **Output**: Print results as a simple table: Date, Time, DJ, Show, Artist, Song, Album.

## Dependencies

```
pip install requests beautifulsoup4
```

No other dependencies needed. Target Python 3.10+.

## Important Gotchas

- The `programming.kalx.berkeley.edu` subdomain and `widgets.spinitron.com` serve the same data with different layouts. Use `widgets.spinitron.com/KALX/` as it has a simpler layout.
- Spinitron pages use standard HTML tables, not JavaScript-rendered content, so `requests` works fine (no Selenium/Playwright needed).
- Some playlists may have very few or zero spins logged (e.g., automated overnight blocks or talk shows).
- The "New" marker appears inline in the detail cell for recently released music — handle it when parsing album/label fields.

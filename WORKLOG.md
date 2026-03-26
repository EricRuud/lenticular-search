# Show Bill Discovery Worklog

**Goal:** Find local Bay Area bands that would work well on a show bill with The Lenticular Clouds at Bottom of the Hill.

**Approach:** Iterate on the app one step at a time, trying each idea, evaluating what it reveals, and building on what works.

---

## Iteration 1: Baseline — What does the app know about The Lenticular Clouds?

**Result:** One play found: KDVS, Oct 16 2025, DJ Conifer's "Evergreen Radio" — "Get Yourself a Girl" from Mystic Mountain New Age Music Festival. Only 1 play across 6 months / 6 stations. Not much direct data to work with.

**Evaluation:** Can't rely on direct play data. Need to use the context of that one playlist as a taste seed.

## Iteration 2: Playlist context + DJ taste

**Result:** The Evergreen Radio playlist had Shannon & The Clams, Jessica Pratt, Japanese Breakfast, glass beach, Cornelius, Fiona Apple, Sidney Gish, Velvet Underground — eclectic indie/art pop/dream pop mix. DJ Conifer also plays local acts like Jay Som, Sweet Trip, Duster, Tuxedomoon.

**Evaluation:** The playlist-mates paint a taste profile: indie rock/pop with psych-adjacent and art-pop tendencies. Good seed for co-occurrence analysis.

## Iteration 3: Co-occurrence — local bands sharing playlists with taste seeds

**Result:** Top co-occurring local bands: Deerhoof (20), The Coup (20), Pavement (18), Grateful Dead (17), SPELLLING (17), Flipper (16), Primus (16), Tanukichan (14). Many are legacy acts or too big.

**Evaluation:** Co-occurrence alone surfaces famous bands. Need to filter for currently active, bookable acts at Bottom of the Hill scale.

## Iteration 4: Filter for active bands (played recently)

**Result:** Added recency filter (last 90 days). Better results: SPELLLING, April Magazine, Al Harper, Everyone Is Dirty, Scowl, Aluminum, Dick Stusso, Jay Som, Sweet Trip, Topographies, Whirr. Mix of bookable indie bands.

**Evaluation:** Getting warmer but still noisy. Missing genre signal — Scowl (hardcore) and Mac Dre (rap) share playlists but wouldn't fit on a bill.

## Iteration 5: Genre profiling

**Result:** Lenticular Clouds has no MusicBrainz tags (too small). Seed artists cluster around: indie rock, indie pop, rock, singer-songwriter, alternative rock, art pop, folk, freak folk.

**Evaluation:** Genre overlap can help filter out non-fitting bands. Need to combine it with co-occurrence.

## Iteration 6: Combined scoring (co-occurrence × 3 + genre × 5 + plays)

**Result:** Top scored: Grateful Dead (287), Pavement (139), SPELLLING (139), The Coup (139), Deerhoof (130), Primus (120). Still dominated by big/legacy acts.

**Evaluation:** The scoring works but needs a "size" filter. Grateful Dead shouldn't be on a Bottom of the Hill bill. Need to penalize bands that are too big (too many plays = probably too famous) or separate "bookable indie" from "legacy legend."

## Iteration 7: Bookability heuristic

**Result:** Added play count penalties (>200 plays = -30, >100 = -15) and recent release bonuses (2024+ = +20, 2020+ = +10). Top results: Pavement (79), Deerhoof (77), Everyone Is Dirty (66), Tanukichan (66), Hot Flash Heat Wave (65), SPELLLING (64). Much more bookable scale.

**Evaluation:** Better! Everyone Is Dirty, Tanukichan, Hot Flash Heat Wave, Fake Fruit, pardoner, Jay Som, Sweet Trip, Topographies are all reasonable Bottom of the Hill acts. But still some too-big acts (Pavement, Deftones). The genre weighting also needs tuning — Deftones shouldn't score that high for a psych-pop bill.

## Iteration 8: Built "Show Bill" tab into the web UI

**Result:** Created recommend.py module with the scoring engine. Added "Show Bill" tab to web UI with artist input field (defaults to The Lenticular Clouds). Shows ranked recommendations with signals (shared playlists, genre matches, total plays) and platform links.

**Evaluation:** The feature works end-to-end. Now I can iterate on the algorithm through the UI. Key issues to address:
- Need more genre tags to differentiate psych-pop from metal/hardcore
- "Everyone Is Dirty", "Tanukichan", "Hot Flash Heat Wave" feel right
- "Deftones", "Faith No More" feel wrong — too heavy
- Missing city data for some bands (need more MusicBrainz lookups)

## Next iterations to try:
- Weight down bands with "metal", "hardcore", "hip hop" tags
- Boost bands whose DJs also played Lenticular Clouds
- Add a "venue fit" signal: has this band played Bottom of the Hill before?
- Try expanding seed artists beyond just the one playlist

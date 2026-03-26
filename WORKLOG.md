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

## Iteration 9: Negative genre tag penalties

**Result:** Added NEGATIVE_TAGS list (metal, hip hop, country, etc) with -10 per match. Deftones, Faith No More, Mac Dre, Testament all dropped off. Top list now: Everyone Is Dirty, Deerhoof, Hot Flash Heat Wave, Tanukichan, Fake Fruit, Topographies, LSD and the Search for God, Osees.

**Evaluation:** Much better vibe match. The negative tags effectively filter out wrong-genre bands.

## Iterations 10-11: DJ affinity analysis

**Result:** Found DJs whose taste aligns: DJ Conifer (KDVS), DJ Honeypot (KDVS), DJ Otter Mason (BFF.fm), dj siick (KSJS), Space Abuela (BFF.fm). Their playlists revealed new candidates: pardoner, The Fresh & Onlys, Pacing, No Vacation, Haley Heynderickx, Duster, Tuxedomoon.

**Evaluation:** DJ affinity surfaces bands that pure co-occurrence misses. These are bands whose aesthetic is validated by human tastemakers who also like the Lenticular Clouds sound.

## Iterations 12-13: DJ affinity scoring + penalty tuning

**Result:** Added dj_count * 5 to score (how many aligned DJs play this band). Increased negative tag penalty to -15. Current top list:
1. Everyone Is Dirty (post-punk/art rock)
2. Jay Som (indie rock/dream pop, Walnut Creek)
3. Whirr (shoegaze, SF)
4. Xiu Xiu (experimental, San Jose)
5. LSD and the Search for God (shoegaze, SF)
6. Tanukichan (shoegaze/noise pop)
7. Fake Fruit (post-punk, Oakland)
8. SPELLLING (experimental, Sacramento)
9. Hot Flash Heat Wave (dream pop/garage, SF)
10. Sweet Trip (dream pop/shoegaze, SF)
11. Haley Heynderickx (folk/singer-songwriter, Stockton)
12. Madeline Kenney (indie)
13. Duster (slowcore/shoegaze, San Jose)
14. Topographies (post-punk/shoegaze, SF)
15. Tuxedomoon (post-punk/art rock, SF)

**Evaluation:** This is a STRONG list for a Bottom of the Hill bill. The algorithm is surfacing exactly the kind of dreamy, psych-adjacent indie bands that would fit. Still some legacy acts high (Pavement, Jefferson Airplane, Deerhoof) that are too big. Need to keep refining the "bookability" signal.

## Current best candidates for the bill:
- **Everyone Is Dirty** — post-punk/psychedelic pop, Oakland, active
- **Fake Fruit** — post-punk/indie rock, Oakland, 2024 release
- **Tanukichan** — shoegaze/dream pop, active
- **Hot Flash Heat Wave** — dream pop/garage rock, SF
- **Topographies** — post-punk/shoegaze/dark wave, SF
- **LSD and the Search for God** — shoegaze, SF
- **Sweet Trip** — dream pop/glitch pop, SF
- **Duster** — slowcore/shoegaze, San Jose
- **Haley Heynderickx** — folk/singer-songwriter
- **pardoner** — punk/rock, active, 99 plays

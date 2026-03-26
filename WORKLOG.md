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

## Iterations 15-17: Venue scale + Bottom of the Hill data

**Added:** Scraped Bottom of the Hill's 2026 calendar. Bands confirmed to play BOTH get +25 bonus and a "BOTH" badge. LSD and the Search for God jumps to #1 (they're literally playing BOTH on Apr 5).

**Removed:** Raw score column from UI, total_plays from Why signals. Lowered max_plays to 100 (BOTH scale).

## Iteration 18: Two-hop taste chain

**Result:** Went 2 degrees out from Lenticular Clouds' playlist. Found Red House Painters and The Brian Jonestown Massacre — both strongly in the right aesthetic neighborhood (slowcore and psych rock).

**Evaluation:** The two-hop chain finds aesthetic allies that direct methods miss. Good for widening the net.

## Iteration 19: Label connections

**Result:** Mapped record labels across seed artists. Carpark Records connects Tanukichan, Fake Fruit, and Madeline Kenney. Polyvinyl connects Jay Som and Deerhoof.

**Evaluation:** Label signal is noisy (many empty labels) but the Carpark connection is genuinely useful — shared label implies shared audience and booking circuit.

## Iteration 20: Show bill generator

**Added:** The UI now generates 3 "Suggested Bills" below the recommendation table:
- **Venue-Tested** — bands that already play Bottom of the Hill
- **Genre Night** — strongest genre overlap
- **DJ Picks** — most frequently paired by local DJs

**Removed:** N/A (this was pure add)

**Three proposed bills:**
1. Dream Pop Night: Lenticular Clouds + LSD and the Search for God + Sweet Trip
2. Art Punk Night: Lenticular Clouds + Xiu Xiu + Everyone Is Dirty
3. Indie Pop Night: Lenticular Clouds + Haley Heynderickx + Hemlocke Springs

## Iteration 21: Artist track preview

**Added:** Click any recommended band to see their most-played tracks on Bay Area radio with platform links.

**Removed:** Redundant "BAY AREA" badge on Show Bill tab (all recs are local).

## Iteration 22: Bandcamp verification + single link

**Added:** Verified all top 14 recommendations have Bandcamp pages. Replaced full platform link bar with single "bandcamp" link.

**Removed:** 4-platform link bar on Show Bill tab (cluttered, Bandcamp most relevant for indie).

## Iteration 23: Era penalty for legacy acts

**Added:** -25 score for bands whose newest known release is pre-2015. Jefferson Airplane and similar legacy acts drop appropriately.

**Removed:** Legacy acts from competitive rankings via era penalty.

## Iteration 24: Aesthetic keyword scoring

**Added:** Song/album title keyword matching for psych/dreamy aesthetics (dream, moon, cosmic, crystal, etc.). New discoveries: Wooden Shjips, venturing, Sparklehorse, Moon Duo, Wild Moth.

**Current top 10 after 24 iterations:**
1. LSD and the Search for God [plays BOTH] — shoegaze, SF
2. Xiu Xiu — experimental, San Jose
3. Haley Heynderickx — folk/singer-songwriter, Stockton
4. Sweet Trip — dream pop/glitch, SF
5. Whirr — shoegaze, SF
6. Ty Segall — psych/garage, Palo Alto
7. Tanukichan — shoegaze/noise pop
8. venturing — Newark (rising band)
9. Everyone Is Dirty — post-punk/art rock
10. Hot Flash Heat Wave — dream pop/garage, SF
11. Wooden Shjips — psych rock, SF
12. Duster — slowcore/shoegaze, San Jose
13. Hemlocke Springs — Concord
14. Fake Fruit — post-punk, Oakland

## Iterations 25-26: Bandcamp recommendation engine + exclusion list

**Added:** Scraped Bandcamp's "if you like" section. Found Sugar Candy Mountain (Oakland psych pop), Moon Duo (SF psych), The Birds I Heard (Bay Area). Added as seeds. Manual exclusion list for persistent misfits (Deftones, Cake, SPRINTS).

## Iterations 27-28: Real show lineups + lineup peer seeds

**Added:** Songkick data for Sugar Candy Mountain, Moon Duo, Wooden Shjips shows. Bands that opened for them (Assemble Head in Sunburst Sound, Lumerians, Skinshape, Enumclaw, Wisp) added as LINEUP_PEERS.

## Iteration 29: Bandcamp release date verification

**Result:** Hot Flash Heat Wave released Mar 2026 (very active). pure hex Mar 2025. Welcome Strawberry Jul 2025. Pacing last release 2015 (removed as likely inactive).

## Iteration 30: Scene graph / community tightness

**Added:** Scene tightness bonus — bands that connect to many other recs get boosted. Identified core cluster: Tanukichan ↔ Fake Fruit ↔ Topographies ↔ Wooden Shjips ↔ Whirr ↔ Duster ↔ pure hex ↔ Everyone Is Dirty ↔ Welcome Strawberry. pure hex connects to 17/20 recs.

## Iteration 31: Bandcamp fan collection overlap

**Explored:** Scraped 5 Lenticular Clouds supporters' Bandcamp collections. Found their taste leans more experimental/electronic/new-age (M. Sage, Emily A. Sprague, Moon Letters) vs the radio-sourced indie rock recs. Both valid — radio recs better for a Bottom of the Hill rock show.

---

# FINAL RECOMMENDATIONS (after 31 iterations)

**Tier 1 — Strongest fit (play BOTH, core scene, right genre):**
1. LSD and the Search for God — SF shoegaze, plays Bottom of the Hill Apr 5
2. Tanukichan — shoegaze/dream pop, 9 seed pairings, core scene
3. Whirr — SF shoegaze, core scene cluster
4. Hot Flash Heat Wave — SF dream pop/garage, released new album Mar 2026

**Tier 2 — Excellent fit (strong signals, active):**
5. pure hex — SF, connects to 17 other recs, released Mar 2025
6. Fake Fruit — Oakland post-punk, released 2024
7. Everyone Is Dirty — post-punk/art rock, released 2023
8. Welcome Strawberry — Oakland, released Jul 2025
9. Wooden Shjips — SF psych rock, Ripley Johnson project
10. Sweet Trip — SF dream pop/glitch pop

**Tier 3 — Good fit (worth exploring):**
11. Topographies — SF post-punk/shoegaze/dark wave
12. Chime School — indie pop, released 2024
13. The Telephone Numbers — SF, released 2025
14. Gumby's Junk — Oakland, released 2025
15. Duster — San Jose slowcore/shoegaze
16. Ty Segall — Palo Alto psych/garage (may be too big)
17. Xiu Xiu — San Jose experimental (may be too experimental)
18. The Spiral Electric — psych, released 2019
19. Ryli — released 2025
20. Whitney's Playland — released 2023

**Signal sources used:**
- Bay Area radio co-occurrence (6 stations, 6 months)
- MusicBrainz genre tags (positive + negative)
- Bandcamp "if you like" recommendations
- Real show lineup data (Songkick)
- Bottom of the Hill 2026 calendar
- Aesthetic keyword matching (song/album titles)
- DJ taste affinity
- Scene graph / community tightness
- Bandcamp release date verification
- Bandcamp fan collection overlap

## Iteration 14: Replace co-occurrence with same-set pairing

**Added:** `same_set` signal — counts how many different seed artists a band gets paired with in the same DJ set (playlist). Weighted by `seed_variety` (diversity of pairings) rather than raw count. Weight: seed_variety * 6.

**Removed:** Raw `cooccurrence` — just counted shared playlists, which surfaced popular bands appearing everywhere regardless of aesthetic fit.

**Result:** New discoveries: Hemlocke Springs (Concord), The Telephone Numbers (SF), Gumby's Junk (Oakland), Chime School, Ty Segall. These weren't visible before. Deftones still persists (seed_variety=8 because freeform DJs pair everything together).

**Evaluation:** Same-set pairing is a tighter signal than co-occurrence. The `seed_variety` metric (how many *different* seed artists you're paired with) captures genuine aesthetic affinity. New candidates feel right. Need to increase negative tag weight again for Deftones, or add a "too eclectic DJ" discount.

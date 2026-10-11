# Changelog

What changed on the [SCP Constellation Map](https://nyxxxx.github.io/scp-constellation-map/), newest first.
The map's data are also refreshed every day from the newest crawl of the wiki; those daily refreshes are not listed here.

## 11 October 2026

**Filters**
- New **Length** filter in the left column: a slider on word counts (0 to 30,000+), with quick choices Under 1k, 1k to 3k, 3k+ and 10k+.
- The left column is now in two parts: **Filter the pages** (Show, Object class, Rating, Length) first, then **Display**
  (Colour dots by, Background clouds, Layers).

**Timeline**
- The timeline now replays how the map grew: before today, the map shows a layout computed for the end of each year from the pages
  written by then, and the dots glide from one year to the next.
- Pressing Play opens on SCP-173 alone, then the 238 pages of 2008 appear one by one in the order they were created, while the view
  pulls back; the years then follow at about three seconds each. The camera follows the growing map, and region clouds and names fade
  back in when the animation reaches today.

**Tale series**
- The Tale series menu now lists 254 of the 268 series on the wiki's Series Archive (it listed 42).
- A selected series shows each page's place in the reading order as a number above its dot.

**Look**
- New colours: object classes follow the wiki's own Anomaly Classification Bar (Safe green, Euclid yellow, Keter red); no more pink in
  the dark theme; region names in white (dark theme) or black (light theme), so they no longer share a colour with the dots.
- In the Object class list, the esoteric classes come right after Keter; in Layers, Outer ring comes last.

**Keeping the map alive**
- The map is now published at nyxxxx.github.io/scp-constellation-map and refreshed every morning from the newest crawl of the wiki.
  Pages already on the map keep their place and region; new pages appear next to the pages they resemble most.
- The project is open source: code under the MIT licence, content under CC BY-SA 3.0 like the wiki.

**Texts and documentation**
- "Sources and limits" on the map is shorter; the full methodology (tag weighting, similarity, regions, layout, names, refresh,
  timeline) is in [METHODS.md](METHODS.md).
- The guide now says that regions are groups of pages that share many tags.

**Safety**
- The map only ever turns ordinary web addresses into links.

## 9 and 10 October 2026

- First version of the map: 18,083 SCP entries, tales and GoI formats placed by the tags they share, 58 regions with names, menus for
  canons, groups of interest, contests, tale series (preview) and lists, search, timeline, light and dark themes.
- 589 pages missing from the dataset (Lost SCP Series, SCP-001 proposals, joke entries) read from the wiki directly.

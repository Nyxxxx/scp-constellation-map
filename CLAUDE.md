# SCP Constellation Map — notes for continuing the work

An interactive map of the English SCP Wiki: every SCP entry, tale and GoI format is a dot, placed by the tags the pages share.
The map was first built in a cloud session (9 and 10 October 2026); this file carries its decisions and backlog forward.
`README.md` lists the files and the commands. Read both before changing anything.
Personal notes about the owner and private links live in `CLAUDE.local.md`, which is kept out of the repository. Read it too when present.

## Where things stand

- Built from `site/scp-constellation-map.html` (version 16 at the hand-over).
- 18,083 pages, 58 regions, 58 canons, 54 GoIs, 49 contests, 42 tale series (preview), a timeline, highlight menus, search, light and dark themes.
- Everything was tested in a headless browser only. **It has never been checked on a real phone or with a real mouse.**

## Setup (Windows)

Tested on Windows 10 x64 with Python 3.12.10 and Git 2.55. Node is optional.

1. Check what is already there: `python --version`, `git --version`, `node --version` (Node is optional; it only checks the page for syntax errors).
2. Install what is missing, for example with `winget install Python.Python.3.12` and `winget install Git.Git`, or from python.org and git-scm.com.
   A shell opened before the install does not see the new programs; open a new one (or reload `PATH`).
3. `python -m pip install -r requirements.txt`, then `python -m playwright install chromium`.
4. Download the dataset snapshot into this folder. **Do not `git clone` it**: with its history the repository is about 16.6 GB and the clone
   stalls for a long time. Fetch the single snapshot the map was built from (about 1.2 GB):
   ```
   git init scp-api
   git -C scp-api remote add origin https://github.com/scp-data/scp-api
   git -C scp-api fetch --depth 1 origin b69934c67940e8512a345fae2615e3e6e14efeaf
   git -C scp-api checkout FETCH_HEAD
   ```
5. `python make.py page`, then `python make.py test`. Both should pass before any change.
   On Windows the rebuilt pages use Windows line endings (CRLF), so they differ from a cloud build by line endings only.
   In `fuzz.py` output, "act errors" are the random clicker missing a button that is not on screen; only "page errors" are faults.
6. History: `git init` here (the `.gitignore` already excludes `scp-api/`, `raw_wiki/`, `out/*.png`, `__pycache__/`), `git config core.autocrlf false`,
   and a first commit. Commit after each validated change.
7. On Windows always start the scripts through `make.py` or with `python -X utf8`: they open files without naming the encoding.

Do **not** run `python make.py all` casually. It recomputes the layout; on another machine or with other library versions the dots can
land in slightly different places, and region names are tied to each region's three most typical tags. `out/data4.json` is the reference layout.

## How changes are decided

- For any choice of look (colours, type, layout), show two to four options side by side on the real map and wait for a pick. Apply nothing aesthetic unasked.
- When asked to explain a suggestion first, explain it and wait; build only what was validated.

## Rules for texts on the page

- Impersonal: no "I", no "we", no address to one reader. Written for an outside audience.
- Precise and methodological: say what was done, with counts, and what is missing.
- Any text produced by an AI (region names and descriptions, summaries of contests absent from the archive) is labelled as AI-generated on the page.
- Contest, GoI, canon and tale-series descriptions are copied word for word from the wiki's own pages (Contest Archive, Groups of Interest, Canon Hub, each hub's preview).
- No "Production" line and no mention of an "AI page reader": the owner had both removed.
- The page keeps its attribution line (SCP Wiki, CC BY-SA 3.0, unofficial).

## Behaviour decided so far (do not change without asking)

- A highlight closes only with the × of its chip (Escape also works). Clicking an empty spot only lets go of a selected page.
- Outer ring hidden at launch; dots coloured by object class at launch; region names in violet; subtitle "Every SCP entry, tale and GoI format, mapped by the tags they share."
- Region, canon and GoI names win clicks over dots when zoomed out; their size follows their page count.
- Cloud outlines are traced once as vector lines; nothing re-renders while zooming (the owner found the re-render "very annoying").
- Selecting a dot dims the rest and lights the cloud of its region; clicking the selected dot again lets it go.
- The right column has back and forward buttons at its far left; contest, GoI and canon information lives in the right column, not in the menus.
- Unofficial contests are not listed; their tags are housekeeping tags.
- Highlight counts stay as they are (total of the set, not "N of M shown").
- On narrow screens a long region name is set on two lines and kept inside the map; the search box empties itself after a pick; a small colour key shows on the map while the left column is closed.
- A tale series belongs to the canons and GoIs its hub page is tagged with; the menu groups series by canon.
- The SCP-001 proposals are all listed, Ouroboros as its four parts.

### Tried and dropped — do not propose again unless the owner raises it

- Authors menu ("not useful").
- Sliders for tag weights and layout shape, and morphing between precomputed layouts (built in version 3, removed in version 4: "things work well as it stands").
- A layer of character names ("unreadable in all the noise").
- "N of M shown" on the highlight chip.
- Clicking outside a highlighted region to close it (replaced by the × only).
- Region names coloured like their cloud, and a colour picker for region names (one violet for all).
- A black-to-white gradient for years (unreadable); the first blue-gradient look ("screams AI").

## Technical notes

- One self-contained HTML page, canvas 2D, no framework. All code lives in one IIFE in `page3.src.html`; the data is inserted at `/*__DATA__*/`.
- State is in `S`; `rebuild()` recomputes what is visible, `draw()` paints the map, `drawHover()` paints the hovered dot on a second canvas laid over the first.
- `?scpdebug` in the address exposes `window.__scp` for tests.
- Pipeline: tags → roles (hidden, class, housekeeping, content) → TF-IDF → cosine, 10 nearest pages → Leiden communities (regions, 40 pages minimum) → UMAP (seed 42) → radial spread of the centre in the page.
- Links in the address: `#h=<highlight>&p=<page>` (t. tag, r. region, a. author, g. GoI formats, s. series, u. tale series, l. list, k. all of a kind). Written only when the page is not inside a frame.
- Reading the live wiki from the cloud session went through a summarising reader with a request limit, which is why some pages are missing or approximate.
  From this computer pages can be downloaded directly. Be polite: one request per second at most, and **keep every downloaded page** in a folder
  (for example `raw_wiki/<slug>.html`) so nothing is fetched twice and every extraction can be re-run. Useful address forms: `/<slug>/norender/true`
  (tags and discussion link without the body), `/<slug>/noredirect/true`.
- Crom (a community GraphQL service for the SCP wiki) was blocked from the cloud session. If it is reachable here, it is the better source for
  creation dates, ratings, tags and credited authors (co-authors and rewrites included), for every language branch. Check that it still exists before relying on it.

## Backlog — everything kept for Claude Code

### A. Validated by the owner, waiting to be done

1. **Finish the Tale series menu.** 42 of about 270 series are in (the dataset only holds hubs whose title starts with a digit, A or B).
   Download the 23 pages of `scp-wiki.wikidot.com/series-archive` (`/p/2` … `/p/23`) for the list, then each hub page, keep the HTML,
   and feed `make_hubs.py` (it expects `raw_content`, `tags`, `title`, `creator`, `created_at` per hub). Check a sample by eye against the wiki:
   the owner asked for careful work because a series is often a sub-story of a canon. Then remove the word "preview" from the menu note and the limits text.
2. **Colour redesign.** Announced by the owner as the next topic; nothing decided. Earlier remarks: the look should stay close to the Foundation's;
   object-class colours "don't look very great"; the light theme was once "a bit too bright". Directions offered once and never mocked up:
   the current wiki look, a paper dossier (typewriter type, stamps, redaction bars), a containment terminal (dark, monochrome, class colours as the only colour),
   a printed star atlas (engraved ink chart, regions lettered like constellations — closest to the original idea). Show variants on the same piece of map, in the owner's own browser.
3. **Reading order on the map** for a tale series: undecided between nothing, a thin line joining the dots in order, or small numbers next to the dots. Ask.

### B. Data that direct access to the wiki can complete or correct

4. **Missing joke entries (25):** 13 refused by the reader (scp-056-j, 067-j, 069-j, 078-j, 273-j, 2006-j, 2041-j, 4463-j, 9000-j, meta-ex-j, mystery-j, wcpgw-j, tldr-j),
   10 unreadable or absent, 2 without rating. Lists in `README.md` and `jokes/failed_*.txt`.
5. **Missing Lost entries:** SCP-L033, SCP-L076, SCP-L744.
6. **Re-read all 589 hand-added pages from their HTML** (129 Lost, 64 SCP-001 proposals, 396 jokes) to check tags, ratings and authors, and to fill what the reader
   could not give: real posting dates (Lost entries carry last-edit dates, 20 jokes an estimate, proposals the date of their discussion thread),
   word counts, exact esoteric class names, the classification bar (clearance, disruption, risk).
7. **Five SCP-001 proposals take their author from the code name** (DarkStuff, Poufy, Metaphysician/Karpin, Blank the First, Bleep): read the real credits.
8. **Authors.** 799 pages show "(deleted account)" and every page has a single author. The wiki's attribution records (or Crom) give the credited authors,
   co-authors and rewrite authors.
9. **Untitled entries.** SCP-970-EX, 999-EX, 1949-EX and 4853 are blank on the wiki's own lists (nothing to copy). SCP-9932 and 9945 could not be checked:
   read the live Series 10 list.
10. **Contests without archive text (7):** April Fools 2014, LoreCon 2023, Pridefest 2024/2025/2026, SPORTSCON, GoI Con 2026 carry an AI summary.
    Replace with the wiki's wording when the Contest Archive lists them, or quote each contest page. Some winners and dates are missing or approximate.
11. **GoIs without description (8):** Accelerate the Future, Children of the Night, Eric, Homo sapiens sidhe, ICSUT, JOICL, La Rue Macabre, Little Misters
    have no entry on the Groups of Interest page. Look for a hub of their own to quote.
12. **Reading order for canons and GoIs.** Canon hubs and GoI hubs list their pages too; the extraction written for tale series could give each canon and GoI a reading order.
13. **Page links.** The dataset counts every hyperlink on a page, author footers ("my other articles") included. With the HTML, keep only links in the body of the article.
14. **594 entries show "Esoteric (unnamed)"**: they are tagged esoteric but their class name could not be read from the page source. Read it properly.
15. **Odd pages:** scp-5490, 6197 and 6750 gave no tags; scp-9283, 9437 and 9496 were up for deletion on 10 October 2026; scp-6184 did not exist.
16. **Coverage.** Only the English wiki is mapped. The other language branches and the International Translation Archive are absent; so are hubs, art pages,
    essays and supplements. An international layer, or one map per branch, is possible with a source that covers them (Crom).
17. **Tell the dataset's maintainers** (github.com/scp-data/scp-api) that its hub list stops at the letter B and that SCP-001 proposals overwrite one another.

### C. Keeping the map alive

18. **A refresh command:** update the dataset, re-read the hand-added pages, rebuild, test, in one go. The map is a snapshot of 9 October 2026.
19. **A schedule** for that refresh (a scheduled task, or an automatic job on the hosting side).
20. **A layout that stays recognisable from one refresh to the next.** Today a recompute moves every dot. Start the new layout from the previous positions,
    and match regions to their old names by shared members instead of by their three top tags, so names survive.
21. **Version history** with git, one commit per validated change.

### D. Publishing

22. **A public website** (for example GitHub Pages; needs a free account). This is also what makes the shareable links and the "Copy link" button work,
    since both stay hidden inside the Claude viewer. Because the page quotes the wiki, the site must keep the CC BY-SA attribution.
23. **Split the page and the data** into separate files once hosted: faster loading, the data cached by the browser, no size limit on a single file.
24. **Host the fonts with the site**, including the wiki's own title typeface if its licence allows (the page currently uses the declared fallback).

### E. Computation and speed

25. **Timeline play** repaints every dot on every frame. Keep the settled dots as a picture between two months and animate only the new ones, if it is slow on real machines.
26. **Test on real devices:** pinch-zoom and speed on a phone, a trackpad, a large screen. Never done.
27. **Soft cloud fills** are a fixed-size picture, slightly soft when zoomed far in (a compromise chosen to avoid re-rendering). They could be drawn as shapes like the outlines.
28. **True live physics** (dragging dots and reshaping the map as in Obsidian) needs a GPU drawing engine such as the one behind Cosmograph, and a rebuild of the drawing layer.
    Parked: the owner liked the idea early on, then chose to keep the fixed layout.
29. **A map by meaning** instead of by tags: place pages by what their text says (the dataset holds the full text). An alternative view from the very first discussion; heavy to compute.
30. **Page links that pull.** Positions come from tags only; real links between pages could attract as well, which gives a different map.

### F. Small things noticed and left

31. The fix that lets the neighbours of a selected page be clicked under a highlight was never tested directly: add a test.
32. The Guide button and opening a page outside the highlight still close a highlight; the owner was told and has not asked to change it.
33. Keyboard and screen-reader use were only partly reviewed.
34. Prior art, for context: the "SCP Network Wiki" (2021) graphs which SCPs cite each other; Crom and Scpper are search and statistics tools. Nothing equivalent to this map was found.

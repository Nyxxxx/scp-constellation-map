# SCP Constellation Map — notes for continuing the work

An interactive map of the English SCP Wiki: every SCP entry, tale and GoI format is a dot, placed by the tags the pages share.
The map was first built in a cloud session (9 and 10 October 2026); this file carries its decisions and backlog forward.
`README.md` lists the files and the commands. Read both before changing anything.
Personal notes about the owner and private links live in `CLAUDE.local.md`, which is kept out of the repository. Read it too when present.

## Where things stand

- Public site (GitHub Pages, branch `main`, root): https://nyxxxx.github.io/scp-constellation-map/ — `index.html` forwards to
  `scp-constellation-map-standalone.html`, keeping the `#h=…&p=…` part. Repository: https://github.com/Nyxxxx/scp-constellation-map (public).
  Publishing a change = `python make.py page`, test, commit, push; the site updates within a few minutes.
- Built from `site/scp-constellation-map.html` (version 16 at the hand-over).
- 18,083 pages, 58 regions, 58 canons, 54 GoIs, 49 contests, 42 tale series (preview), a timeline, highlight menus, search, light and dark themes.
- Automatic tests run in a headless browser. On 11 October 2026 the owner opened the public site on a real phone: "runs extremely well".
  Not yet tried: a trackpad, a large screen, an older or slower phone.

## Daily refresh (GitHub Actions)

`.github/workflows/daily-refresh.yml` runs every day at 06:40 UTC (and by hand from the Actions tab): newest dataset snapshot,
`make.py all --no-wiki` (refresh; tale series stay as in `hubs.json`), `make.py test`, then a commit by github-actions[bot] and a push,
which republishes the site. Nothing is published if a step fails; GitHub emails the owner. `out/dataset_commit.txt` records the dataset
commit last used, so a day without a new crawl does nothing.
**Before working on this computer, run `git pull`**: the bot commits to `main` every day. Text files are stored with LF line endings (`.gitattributes`).
Not refreshed by the bot: the tale series hubs (run `python make.py all` locally, which downloads them politely), the pages read by hand
from the live wiki (`extra_pages.json`, Lost/001/jokes), contests absent from the archive, region names (only needed after `--fresh`).

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

`python make.py all` is a **refresh** (since 11 October 2026): it starts from `out/data4.json` (the reference layout, copied to
`out/data4.prev.json`). Pages whose tags did not change keep their exact position and region; new or retagged pages go to the middle of
their closest pages and join the region of most of them; region names, name labels and their anchors are kept. Tested with the 11 October
crawl: 17,991 of 18,073 dots unchanged, 6 new pages, 10 deleted, 80 retagged. Do **not** run `python make.py all --fresh` casually:
it recomputes the layout (UMAP) and the regions (Leiden), moves every dot, and new regions need names in `region_names.json`.
The snapshot date is read from the dataset's last commit. A second dataset copy may sit in `scp-api-new/` (git worktree, ignored).

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
- Colours (chosen 11 October 2026, variant "Wiki, refined" of `mockups/make_mockups.py`): object classes in the wiki's Anomaly
  Classification Bar colours (Safe green, Euclid yellow, Keter red; Esoteric keeps a blue); no pink in the dark theme (menus and links
  in true red); region names in neutral ink (white in dark, near-black in light); canon and GoI names keep their original italic
  colours (canon `--canon-label`, GoI `--goi-label`). Map names must never share a colour with the dots.
- Object class list: Safe, Euclid, Keter, then the Esoteric group, then Neutralized, Pending, Explained, Decommissioned, None listed.
  Layers list ends with Timeline, then Outer ring.
- Outer ring hidden at launch; dots coloured by object class at launch; subtitle "Every SCP entry, tale and GoI format, mapped by the tags they share."
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
- Region names coloured like their cloud, and a colour picker for region names (one colour for all).
- Colour directions "Paper dossier" and "Star atlas" (mocked up 11 October 2026, not chosen; still buildable with `mockups/make_mockups.py`),
  and a "containment terminal" look (declined without a mock-up).
- A line joining the pages of a tale series in reading order, alone or with the numbers (mocked up 11 October 2026: "a bit confusing").
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

1. **Tale series menu: done on 11 October 2026.** `fetch_series.py` downloads the Series Archive (268 hubs) into `raw_wiki/`; `make_hubs.py`
   reads the dataset's 44 plus the rest; 253 series have two pages or more on the map. Owner spot-checked 8 (Olympia Project, Team Bird,
   Kit's Home, Revolution Earth, The Ballad of Neapolio, Schlangenkrieg: fine). SCP Anthology 2022 was missing 23 of 33 entries (one paragraph
   of "link + text" lines): fixed with the list-paragraph rule. Manhattan Crisis Hub: half its links are Japanese-branch or nonexistent pages,
   which cannot be on the map; SCP-4661 comes from a character blurb (known limit). Left out: 15 hubs (Japanese-branch pages, or lists the
   extraction cannot read: Mississippi Blues, World of Wolves, SCP Origins, SCP Anthology 2025, the SAPPHIRE Chronicles).
2. **Colour redesign.** Done on 11 October 2026 (see "Behaviour decided"). The guide's sentence on name colours ("Red italic names…
   brown italic names") still matches, since canon and GoI colours were kept. An earlier remark, not yet addressed: the light theme was once "a bit too bright".
3. **Reading order on the map: done on 11 October 2026.** A selected tale series shows each page's place in the hub's list as a small number
   above its dot (hidden where numbers would overlap; they appear when zooming in). The series panel says so.

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
20. **Layout that stays recognisable: done on 11 October 2026** (see "Setup"). Tried first and dropped: re-running UMAP from the previous
    positions, even gently (60 to 200 rounds, learning rate 0.1 to 1): median moves of 20 to 40 units on a radius of 1000, and UMAP's
    per-axis rescaling of the starting positions alone moved dots by about 16. Freezing positions was chosen instead. Known cost: over months
    the layout drifts from what a fresh computation would give; a deliberate `--fresh` rebuild resets it (and needs region names).
    Also: equally similar neighbours are now ordered by page index, so neighbour lists no longer depend on the machine (this changed the
    order of ties once, in about 7,000 lists).
21. **Version history** with git, one commit per validated change.

### D. Publishing

22. **A public website** (for example GitHub Pages; needs a free account). This is also what makes the shareable links and the "Copy link" button work,
    since both stay hidden inside the Claude viewer. Because the page quotes the wiki, the site must keep the CC BY-SA attribution.
23. **Split the page and the data** into separate files once hosted: faster loading, the data cached by the browser, no size limit on a single file.
24. **Host the fonts with the site**, including the wiki's own title typeface if its licence allows (the page currently uses the declared fallback).

### E. Computation and speed

25. **Timeline play** repaints every dot on every frame. Keep the settled dots as a picture between two months and animate only the new ones, if it is slow on real machines.
26. **Test on real devices:** phone done on 11 October 2026 (runs well). Still to try: a trackpad, a large screen, a slow phone.
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

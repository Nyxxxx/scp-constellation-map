# SCP Constellation Map

## ➜ [Open the map: nyxxxx.github.io/scp-constellation-map](https://nyxxxx.github.io/scp-constellation-map/)

An interactive map of the English [SCP Wiki](https://scp-wiki.wikidot.com): every SCP entry, tale and GoI format is a dot, and pages
that share tags sit close together. About 18,000 pages, grouped into 58 regions, with menus for canons, groups of interest,
contests and tale series, a timeline that replays how the map grew since 2008, search, and light and dark themes.
It runs in any browser, needs no account, and is rebuilt every day from the latest copy of the wiki.

Unofficial fan project, not affiliated with the SCP Wiki.

**Methodology: [METHODS.md](METHODS.md)**: how tags are weighted (TF-IDF), how pages are compared (cosine similarity), how regions are
found (Leiden), how positions are computed (UMAP), how region names were written, how the daily refresh and the timeline work, and what
the map leaves out.

## How it works, in short

1. **Data.** Titles, tags, ratings, authors and dates come from [scp-data/scp-api](https://github.com/scp-data/scp-api), a public daily
   crawl of the wiki. Pages missing from that crawl (Lost SCP Series, SCP-001 proposals, joke entries) and the tale series hubs were read
   from the wiki directly.
2. **Placement.** Each page is described by its tags, rare tags counting more. Pages are compared with each other, regions are found
   among similar pages, and the layout is computed so that similar pages land near each other.
3. **Daily refresh.** A GitHub Action takes the newest crawl each morning. Pages already on the map keep their place; new pages are placed
   beside the pages they resemble most. The map is published only if the automatic browser tests pass.

## Building it yourself

Requires Python 3.12 and Git. The dataset snapshot is about 1.2 GB.

```
python -m pip install -r requirements.txt
python -m playwright install chromium
git init scp-api
git -C scp-api remote add origin https://github.com/scp-data/scp-api
git -C scp-api fetch --depth 1 origin HEAD
git -C scp-api checkout FETCH_HEAD
python make.py all
python make.py preview
```

Do not `git clone` the dataset: with its history it is about 16.6 GB, and only the last snapshot is needed.

| Command | What it does |
|---|---|
| `python make.py page` | rebuilds the page after editing `page/page3.src.html` |
| `python make.py data` | rebuilds the data from the last layout (after editing anything in `data/`) |
| `python make.py all` | refresh from the dataset: existing dots keep their place, new pages are added (`--no-wiki` skips re-reading the tale series hubs) |
| `python make.py all --fresh` | a new layout from scratch: every dot moves, and new regions need names in `data/region_names.json` |
| `python make.py test` | the automatic browser tests |
| `python make.py preview` | opens the local copy of the map in the browser (on Windows: double-click `Preview the map.bat`) |

On Windows, run the scripts through `make.py` (or with `python -X utf8`), so files are read as UTF-8.

## What is in this repository

| Folder or file | Contents |
|---|---|
| `scp-constellation-map-standalone.html`, `index.html` | the published map (one self-contained page) and the address that leads to it |
| `page/page3.src.html` | the page's source: layout, styles and code; the data is inserted at `/*__DATA__*/` |
| `scripts/` | the build steps, run in order by `make.py`: `build.py` (tags, regions, layout), `finalize.py` (descriptions, repairs), `assemble.py` (data into the page), and the readers for contests, notes, tale series and the map through time |
| `data/` | inputs and lists: contest and GoI/canon descriptions, tale series, region names, pages read from the live wiki, the past layouts for the timeline |
| `out/` | the computed data (`data4.json` is the reference layout each refresh starts from) |
| `site/` | the page without its `<html>` wrapper |
| `tests/` | automatic browser tests (Playwright) |
| `mockups/` | scripts that build design variants for comparison |
| `old-versions/` | earlier versions of the page and of some inputs |
| `METHODS.md` | sources, method and limits, with every count |
| `CLAUDE.md` | working notes: decisions taken, things tried and dropped, and the backlog |

## Licence

The code is under the MIT licence ([LICENSE](LICENSE)). The content and data come from the SCP Wiki and are under CC BY-SA 3.0
([LICENSE-CONTENT.md](LICENSE-CONTENT.md)); anyone reusing them must credit the SCP Wiki and share alike.

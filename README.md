# SCP Constellation Map

## ➜ [Open the map: nyxxxx.github.io/scp-constellation-map](https://nyxxxx.github.io/scp-constellation-map/)

An interactive map of the English SCP Wiki: every SCP entry, tale and GoI format is a dot, placed by the tags the pages share.
Updated every day from the wiki. Free, no account. Unofficial fan project; content from the SCP Wiki under CC BY-SA 3.0.
How it is made, and its limits: [METHODS.md](METHODS.md).

## To look at this computer's copy (changes not yet published)

Double-click **`Preview the map.bat`** in this folder: it opens the map in the default browser through a small local web server.
Keep the black window open while looking; close it to stop. (Same as `python make.py preview`.)

`scp-constellation-map-standalone.html` is the whole map in one file; `site/scp-constellation-map.html` is the same page without
the surrounding `<html>` wrapper.

## What is in this folder

| File or folder | What it is |
|---|---|
| `METHODS.md` | Sources, method and limits in full, with every count. The map's own "Sources and limits" section is the short version and links here. |
| `page3.src.html` | The page itself: layout, styles and all the code. The data is inserted where it says `/*__DATA__*/`. |
| `out/data.json` | The finished data the page reads (18,083 pages, positions, regions, tags, descriptions). |
| `out/data4.json` | The raw result of the layout computation, before the last step. Kept so the last step can be run again without recomputing. |
| `build.py` | Step 1. Reads the dataset, weighs the tags, finds each page's nearest pages, detects the regions and computes the positions. About 2 minutes. |
| `finalize.py` | Step 2. Adds the contest, GoI and canon descriptions, repairs titles and series, opens up stacked dots. |
| `make.py` | One command for every step (see Commands below). |
| `assemble.py` | Step 3. Puts the data into the page. (`mkpreview.sh` is the older shell version of `python make.py page`.) |
| `requirements.txt` | The Python libraries to install. |
| `CLAUDE.md` | Working rules, decisions taken, and the list of ideas still to build. Read by Claude Code at the start of each session. |
| `make_extra.py` → `extra_pages.json` | The pages missing from the dataset and read from the live wiki: 129 Lost SCP Series entries, 64 SCP-001 proposals, 396 joke entries. |
| `lost_raw.txt`, `lost_titles.json` | What was read for the Lost SCP Series. |
| `p001_raw.txt`, `p001_list.txt`, `p001_dates.txt` | What was read for the SCP-001 proposals. |
| `jokes/`, `jokes_list.json` | What was read for the joke entries (`part_*.txt`), and the list taken from the Joke SCPs hub. `failed_*.txt` lists pages that could not be read. |
| `make_contests.py`, `contests_base.json` → `contests.json` | Contest names, dates, links, and the descriptions copied from the wiki's Contest Archive. |
| `make_notes.py` → `notes.json` | GoI and canon descriptions copied from the wiki's Groups of Interest page and Canon Hub. |
| `fetch_series.py` → `series_hubs.json` | Downloads the wiki's Series Archive and every series hub it lists (one request per second; pages kept in `raw_wiki/`, never fetched twice). |
| `make_hubs.py` → `hubs.json` | The tale series: reading lists extracted from the series hubs (the dataset's 44, plus the rest downloaded from the wiki). |
| `series_overrides.json` | Reading lists entered by hand, with their source, for hubs whose list the extraction cannot read (SCP Anthology 2025). |
| `mockups/` | Colour variants (`make_mockups.py`) and a spot-check page for tale series (`make_series_check.py`). Their output is not kept in git. |
| `region_names.json` | Names and one-line descriptions of the regions (written with an AI assistant; the page says so). Keyed by the three most typical tags of each region. |
| `fuzz.py`, `shot17.py`, `shot18.py` | Automatic browser tests (random clicking on five screen sizes; checks of the latest changes). |
| `history/` | Earlier versions of the page source and of some inputs. |

## Setting up on your computer (Windows)

The project is worked on with Claude Code, which is the **Code** tab of the Claude desktop app. `CLAUDE.md` in this folder
tells it how the project works and what is left to do, and it can carry out every step below for you.

1. Open the Claude desktop app, click the **Code** tab, choose **Local**, click **Select folder** and pick this folder.
2. Ask it to "set up the project as described in CLAUDE.md". It will install or check, in this order:
   - **Python 3** (3.12 or 3.13) — the language of the build scripts.
   - **The libraries**: `python -m pip install -r requirements.txt`
   - **A test browser**: `python -m playwright install chromium`
   - **Git for Windows** — to download the dataset and keep a history of changes.
   - **The dataset**, inside this folder: only the snapshot the map was built from, commit `b69934c` (automatic crawl of 9 October 2026), about 1.2 GB.
     A plain `git clone` downloads every past crawl as well (about 16.6 GB) and is not needed. Fetch the one snapshot instead:
     ```
     git init scp-api
     git -C scp-api remote add origin https://github.com/scp-data/scp-api
     git -C scp-api fetch --depth 1 origin b69934c67940e8512a345fae2615e3e6e14efeaf
     git -C scp-api checkout FETCH_HEAD
     ```
3. Check that everything works: `python make.py page` then `python make.py test`.

## Commands

Everything goes through `make.py`:

| Command | When | Needs the dataset |
|---|---|---|
| `python make.py page` | after editing `page3.src.html` (texts, colours, behaviour) | no |
| `python make.py data` | after editing contests, GoI/canon notes or tale series | yes |
| `python make.py all` | after a new copy of the dataset: a refresh that keeps every existing dot in place and adds the new pages | yes |
| `python make.py all --fresh` | a new layout from scratch (every dot moves, new regions need names); about 2 minutes | yes |
| `python make.py test` | the automatic browser tests | no |

`python make.py page` writes `scp-constellation-map-standalone.html` (to open in a browser) and `site/scp-constellation-map.html`
(the published form). A newer copy of the dataset gives a different map: regions move and may need new names in
`region_names.json` (the build prints the ones it could not name).

The scripts can also be run one by one; `make.py` shows the order and the arguments. On Windows start them with
`python -X utf8 …`, otherwise the files are read with the wrong character set.

## Licence

Unofficial fan project, not affiliated with the SCP Wiki.
The code is under the MIT licence (`LICENSE`). The content and data come from the SCP Wiki and are under CC BY-SA 3.0 (`LICENSE-CONTENT.md`).

## Known gaps

- Tale series: 253 of the 268 hubs on the Series Archive (downloaded 11 October 2026). 15 are left out because fewer than two of their pages
  are on the map (other language branches, pages newer than the dataset, or lists built in a way the extraction cannot read).

- 25 joke entries listed on the Joke SCPs hub are not on the map. 13 were refused by the reading tool (too many requests):
  scp-056-j, 067-j, 069-j, 078-j, 273-j, 2006-j, 2041-j, 4463-j, 9000-j, meta-ex-j, mystery-j, wcpgw-j, tldr-j.
  10 could not be read or do not exist (scp-017-and-a-half-j, 1414-j, 3303-j, 3428-j, 5304-j, 7419-j, 7519-j, 9139-j, j-j, numberonedoggo-j),
  and 2 show no rating (scp-4297-j, scp-why-are-you-reading-a-url-go-be-productive-j).
  The hub also links 17 pages that are not entries (essays, themes, collections); they are left out on purpose.
- 20 joke entries have a posting date estimated from the number of their discussion thread.
- SCP-L033, SCP-L076 and SCP-L744 could not be read.
- SCP-970-EX, SCP-999-EX, SCP-1949-EX and SCP-4853 have no title on the wiki's own lists; SCP-9932 and SCP-9945 are not on the copy of the Series 10 list in the dataset.
- Links that carry what is shown (`#h=…&p=…`) and the "Copy link" button only work when the page is opened at its own address, not inside the Claude viewer.

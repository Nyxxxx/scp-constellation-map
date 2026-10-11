# SCP Constellation Map: sources, method and limits

The map at https://nyxxxx.github.io/scp-constellation-map/ shows every SCP entry, tale and GoI format of the English SCP Wiki as a dot,
placed by the tags the pages share. This page gives the full detail behind the short "Sources and limits" section of the map:
where the data come from, how pages are weighted, compared, grouped and placed, which algorithms are used, and what is left out.
The map is rebuilt every day; figures here are those of the build of 11 October 2026 (dataset snapshot of that day).

## Source

Titles, tags, ratings, authors, creation dates, page text and links come from [scp-data/scp-api](https://github.com/scp-data/scp-api),
a public GitHub repository that republishes a daily crawl of scp-wiki.wikidot.com. The map was first built from the crawl of 9 October
2026 (commit `b69934c`) and is refreshed from each new crawl. Edits, votes and tag changes reach the map with the next crawl.

## Coverage

Only the English-language wiki is covered. The other language branches and the International Translation Archive are absent, apart from
4 translated entries hosted on the English wiki. Hubs, art pages, essays, author pages, supplements and deleted pages are not in the dataset.

The map holds 18,079 pages: 10,480 SCP entries, 6,761 tales and 838 GoI formats, joined by 57,729 page links.

## Pages added from the live wiki

The dataset stores SCP entries under their number, so the SCP-001 proposals overwrite one another and a single one remains; the Lost SCP
Series and most joke entries are absent. 129 Lost entries, 64 SCP-001 proposals and 396 joke entries were therefore read one by one from
the live wiki on 9 and 10 October 2026 (tags, rating, author and date), and take part in the layout like any other page.

- SCP-001 proposals and joke entries carry the date their discussion thread was opened; for 20 joke entries that date is estimated from the
  number of the thread. Lost entries carry their last-edit date.
- 25 joke entries listed on the Joke SCPs hub are not on the map: their page could not be read or shows no rating.
- SCP-L033, SCP-L076 and SCP-L744 could not be read.

## Method, step by step

The map is built by `make.py`, which runs the scripts in `scripts/` in order. Only tags decide where a page sits; object class, kind of page,
rating and date set colours and filters, never positions. All random steps use the seed 42, so the same input gives the same map.

### 1. Which tags count

Every tag on the wiki is given one of four roles (`scripts/build.py`, function `role`):

| Role | Tags | Use |
|---|---|---|
| hidden | tags starting with `_`, and the page-type tags `scp`, `tale`, `goi-format` | none |
| class | object classes: `safe`, `euclid`, `keter`, `neutralized`, `pending`, `explained`, `decommissioned`, the esoteric classes, `esoteric-class` | colour of the dot |
| housekeeping | 55 listed tags (`co-authored`, `featured`, `rewrite`, `illustrated`, `audio`, `collaboration`, `joke`, `international`, `001-proposal`, …) and every contest tag (a year, `N000`, `con-N`, `-unofficial`) | shown in a page's file, not used for placement |
| content | all other tags (themes, canons, GoIs, characters, locations, …) | placement |

A content tag is used only if at least two pages carry it. In the build of 11 October 2026, 740 of 835 tags are used, and 1,123 pages
have no usable tag (see step 5).

### 2. How a page is described: tags weighted by rarity (TF-IDF)

Each page becomes a list of numbers, one per used tag: 0 if the page does not carry the tag, and the tag's weight if it does. The weight
is `ln(N / df)`, where N is the number of pages (18,079) and df the number of pages carrying the tag. A tag on 10 pages therefore weighs
about 7.5, a tag on 2,000 pages about 2.2: sharing a rare tag says more about two pages than sharing a common one. Each list is then
scaled to length 1, so a page with many tags does not outweigh a page with few. (This is TF-IDF with binary term frequencies and L2
normalisation.)

### 3. How alike two pages are: cosine similarity and ten neighbours

Two pages are compared by the cosine similarity of their lists: 1 when they carry exactly the same tags, 0 when they share none, in between
otherwise, rare shared tags counting most. For every page the ten most similar pages are kept. Pages exactly as similar are ranked by their
place in the page list, so every computer gives the same neighbours. The lines drawn on the map join each page to its three closest
neighbours, and a page's file lists its ten.

### 4. Regions: communities in the network of neighbours (Leiden)

The neighbours form a network: each page is linked to its ten closest pages (when their similarity is above 0.05), the link weighing their
similarity. Regions are the communities of that network, found with the **Leiden algorithm** (`leidenalg`, modularity with resolution 1.0,
run until it no longer improves): groups of pages more linked to each other than to the rest. Communities of fewer than 40 pages are not
shown as regions, which leaves 1,497 pages without a region. The build of 11 October 2026 has 58 regions, from 41 to 1,475 pages.

A region and a position are computed separately: about 6% of pages lie outside the outline of their own region.

### 5. Positions: UMAP

The positions come from **UMAP** (Uniform Manifold Approximation and Projection, `umap-learn`), a method that lays out high-dimensional
data on a plane so that pages similar in their tags land near each other. Settings: cosine distance, 20 neighbours, minimum distance 0.3,
spread 1, repulsion 0.5, 3 negative samples, 400 rounds, started from the two main axes of the data (truncated SVD). Each page is described
for UMAP by its tag list (step 2) plus a small pull toward its own region (its region membership, weighted 0.2), which keeps regions
compact without deciding positions.

The result is centred, scaled so that 98.5% of pages lie within a radius of 1,000 units, and the few pages beyond are drawn in (distance
past 1,000 reduced to a fifth). UMAP keeps neighbours together but does not preserve distances: which pages sit next to each other is
meaningful, exact distances and absolute positions are not.

Pages without a usable tag: the 377 that link to other pages sit at the middle of the pages they link to, with a small offset; the 746
with neither tag nor link sit on an outer ring at radius 1,085 (hidden at launch; shown with Layers → Outer ring).

### 6. Finishing touches

- **Opening the centre.** UMAP packs many pages in the middle. The page spreads them out: a page at distance r from the centre is moved
  to `0.4 × r + 0.6 × 1000 × √(rank)`, where rank is its place (0 to 1) when all pages are sorted by distance. The order from the centre
  outward does not change.
- **Opening stacks.** Pages with exactly the same tags get exactly the same position. Each stack is opened into a small spiral (2 units
  apart, golden angle), the best-rated page in the middle (`scripts/finalize.py`; 713 pages in the build of 11 October 2026).
- **Dot size** grows with the square root of the rating.

### 7. Region names and descriptions

Each region is characterised by its most typical tags: for every tag carried by at least 4 of its pages and 8% of them, the score
`p × ln(p / q)` (p: share of the region's pages carrying the tag; q: share of all pages carrying it) rewards tags that are both common
in the region and rarer elsewhere. The three best tags form the region's key.

The names and one-line descriptions were **written with an AI assistant**, from those tags and the region's highest-rated pages; they are stored in `data/region_names.json` under each region's key, and labelled as AI-generated on the map. They are
not categories used by the wiki and do not describe every page of a region. When a region coincides with one canon or one GoI, it simply
carries that name (8 regions).

### 8. Where names sit

- **Region names** sit at the densest spot of the region: the point around which most of its pages lie within 40 units.
- **Canon and GoI names** are shown for tags of 10 to 600 pages whose pages gather in one place: at least 40% of them within 110 units of
  their densest spot. 41 canons and 27 GoIs qualify. A canon or GoI that is already a region name is not repeated.
- **Outlines and clouds** show where a region's pages are dense: every page adds a small cone of density (radius 52 units), cones combine
  like layers of translucent paint, and the outline is the line where the density reaches 0.3, traced once with the "marching squares"
  method. Neighbouring regions get different colours.

### 9. The daily refresh

Each morning the newest crawl is taken (`.github/workflows/daily-refresh.yml`) and the map is rebuilt from the previous one rather than
from scratch: a page whose tags did not change keeps its exact position and region; a new page, or one whose tags changed, is placed at
the middle of its closest pages and joins the region of most of them (at least half); region names, name positions and the set of canon
and GoI names are kept. The map is published only if the automatic browser tests pass. A full recomputation (`python make.py all --fresh`)
moves every dot and is done only on purpose.

## Timeline

Playing the timeline, or moving its end handle into the past, shows the map as it would have been laid out at that date: one layout per
year (end of December 2008 to 2025, then today), each computed as if only the pages written by then existed (`scripts/build_history.py`).
The layouts are computed backwards from today's map. For each year, the pages written after it are removed, their tags re-weighted among
the pages that remain (step 2), and the layout relaxes a little: a short UMAP run (60 rounds, learning rate 0.3) started from the
positions of the following year, carried back onto that year by a least-squares linear fit, of which half the change is kept. Dots
therefore drift rather than jump: from one year to the next the median dot moves 20 to 50 units (on a radius of 1,000), up to 120 in the
first years, when few pages exist. The size of each layout grows with the fourth root of its number of pages (238 pages, about a third of today's size, at
the end of 2008), and the camera follows that growth while playing. Between two years the dots glide from one layout to the next.

The animation opens on SCP-173 alone, then shows the 238 pages of 2008 one by one in the order they were created (the dataset's
timestamps), before playing year by year (about 220 milliseconds per month). Tags are those of today: the dataset keeps no history of tags.
Region outlines and names describe today's map, so they are hidden while the timeline is in the past and fade back in at the end.
Pages added by the daily refresh have no past layout and appear in today's map.

## Object classes

Classes are extracted from the page source: from the Anomaly Classification System bar on the 1,919 entries that use it, otherwise from
the "Object Class" line. Unusual page formats can be misread. For the pages added from the live wiki, the class is taken from their tags.
594 entries tagged esoteric show "Esoteric (unnamed)" because their class name could not be read.

Dot colours for Safe, Euclid and Keter follow the wiki's own Anomaly Classification Bar.

## Dates, ratings and lengths

Dates are the creation dates given by the dataset; a rewritten page keeps the date of the original. Ratings are those of the download date.
Word counts are computed from the plain text of each page and can differ from the lists kept on the wiki. Every page has a single author
in the dataset; 799 pages show "(deleted account)".

## Tale series

The Tale series menu lists 254 of the 268 series hubs on the wiki's Series Archive.

- 44 hubs were read from the source dataset, which holds only the hubs whose title begins with a digit, A or B; the other 224 were
  downloaded from the wiki on 11 October 2026 (`scripts/fetch_series.py`; the pages are kept so the extraction can be re-run).
- 14 hubs are left out because fewer than two of the pages they link to are on the map: their pages belong to other language branches or
  are newer than the dataset, or their list is built in a way the extraction cannot read (Mississippi Blues, World of Wolves, SCP Origins,
  the SAPPHIRE Chronicles).
- Each reading list is extracted automatically from the hub page (`scripts/make_hubs.py`): links placed in lists, headings, tables, or paragraphs
  made of one link per line are kept in the order of the page; links inside running text are left out; the section names are the headings
  of the hub. A page can be missing or sit under the wrong heading when a hub has an unusual layout.
- The reading list of SCP Anthology 2025 is drawn by a script on its hub; it was copied from that script by hand (`data/series_overrides.json`).
- The canons and GoIs given for a series are the canon and GoI tags carried by its hub page.
- On the map, a selected series shows each page's place in the hub's list as a number above its dot.

## Contests, GoIs and canons

The contest list follows the wiki's Contest Archive. 42 contests carry the description and winners given by the archive, word for word.
7 events absent from the archive carry an AI-generated summary of their own page (April Fools 2014, LoreCon 2023, Pridefest 2024, 2025
and 2026, SPORTSCON, GoI Con 2026). Contests described or tagged as unofficial are excluded.

GoI and canon descriptions are quoted from the wiki's Groups of Interest page and Canon Hub; 8 GoI tags have no entry there and therefore no
description. Canon tags were matched to the Canon Hub by name. GoI tags are those the wiki uses to label GoI formats.

## AI-generated text

Region names and descriptions, and the summaries of the 7 contests absent from the Contest Archive, were written with an AI assistant and
are labelled as such on the map. Every other description is quoted from the wiki.

## Licence

Unofficial fan project, not affiliated with the SCP Wiki. Content from the SCP Wiki is under CC BY-SA 3.0; see `LICENSE-CONTENT.md`.
The code is under the MIT licence; see `LICENSE`.

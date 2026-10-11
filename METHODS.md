# SCP Constellation Map: sources, method and limits

The map at https://nyxxxx.github.io/scp-constellation-map/ shows every SCP entry, tale and GoI format of the English SCP Wiki as a dot,
placed by the tags the pages share. This page gives the full detail behind the short "Sources and limits" section of the map.
Figures are those of the build of 11 October 2026.

## Source

Titles, tags, ratings, authors, creation dates, page text and links come from [scp-data/scp-api](https://github.com/scp-data/scp-api),
a public GitHub repository that republishes a regular crawl of scp-wiki.wikidot.com. The copy used was downloaded on 9 October 2026
(commit `b69934c`). It contains 9,895 SCP entries, 6,760 tales and 839 GoI formats. Edits, votes and tag changes made after that date
are not reflected.

## Coverage

Only the English-language wiki is covered. The other language branches and the International Translation Archive are absent, apart from
4 translated entries hosted on the English wiki. Hubs, art pages, essays, author pages, supplements and deleted pages are not in the dataset.

The map holds 18,083 pages: 10,483 SCP entries, 6,761 tales and 839 GoI formats, joined by 57,728 page links.

## Pages added from the live wiki

The dataset stores SCP entries under their number, so the SCP-001 proposals overwrite one another and a single one remains; the Lost SCP
Series and most joke entries are absent. 129 Lost entries, 64 SCP-001 proposals and 396 joke entries were therefore read one by one from
the live wiki on 9 and 10 October 2026 (tags, rating, author and date), and take part in the layout like any other page.

- SCP-001 proposals and joke entries carry the date their discussion thread was opened; for 20 joke entries that date is estimated from the
  number of the thread. Lost entries carry their last-edit date.
- 25 joke entries listed on the Joke SCPs hub are not on the map: their page could not be read or shows no rating.
- SCP-L033, SCP-L076 and SCP-L744 could not be read.

## Placement

Positions are computed from tags alone. Object class and kind of page set colours and filters, never positions.

- 737 of 832 tags are used; contest tags and housekeeping tags such as co-authored, illustrated or featured are excluded.
- Tags are weighted by rarity (TF-IDF), pages are compared by cosine similarity, and each page is linked to its ten most similar pages.
- The layout is produced by UMAP, a dimension-reduction method (random seed 42), then stretched radially to open up the dense centre.
  UMAP keeps similar pages close but does not preserve distances, and its result depends on the seed: which pages are neighbours is
  meaningful, exact distances and absolute positions are not. A page with few or imprecise tags is placed accordingly.
- 378 pages that share no tag with any other page are placed next to the pages they link to, and 748 pages with neither a shared tag nor
  a link are placed on the outer ring (hidden at launch; shown with Layers → Outer ring).

## Regions

The 58 regions are communities detected by the Leiden algorithm in the network of nearest-neighbour links. Communities of fewer than
40 pages are not shown, which leaves 1,484 pages without a region. Membership of a region and position on the map are computed separately,
so about 6% of pages lie outside the outline of their own region. An outline marks where the pages of a region are dense; it is not a
boundary that contains all of them.

Region names and descriptions are AI-generated from the most frequent tags and the highest-rated pages of each region. They are not
categories used by the wiki and do not describe every page of a region. A region that coincides with one canon or one GoI carries that name.

## Object classes

Classes are extracted from the page source: from the Anomaly Classification System bar on the 1,920 entries that use it, otherwise from
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
  downloaded from the wiki on 11 October 2026 (`fetch_series.py`; the pages are kept so the extraction can be re-run).
- 14 hubs are left out because fewer than two of the pages they link to are on the map: their pages belong to other language branches or
  are newer than the dataset, or their list is built in a way the extraction cannot read (Mississippi Blues, World of Wolves, SCP Origins,
  the SAPPHIRE Chronicles).
- Each reading list is extracted automatically from the hub page (`make_hubs.py`): links placed in lists, headings, tables, or paragraphs
  made of one link per line are kept in the order of the page; links inside running text are left out; the section names are the headings
  of the hub. A page can be missing or sit under the wrong heading when a hub has an unusual layout.
- The reading list of SCP Anthology 2025 is drawn by a script on its hub; it was copied from that script by hand (`series_overrides.json`).
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

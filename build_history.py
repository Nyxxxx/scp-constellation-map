"""The map through time: one layout per date, as if only the pages written by then existed, for the timeline animation.

Usage: python -X utf8 build_history.py out/data.json history.json [months between frames, default 12]

Frames are computed backwards from today's map: the pages written after a date are removed and the layout relaxes (UMAP, starting
from the positions of the frame after it), then it is spread like the page spreads today's map and turned and scaled onto that
next frame. Consecutive frames therefore flow into each other, and the last frame is today's map exactly.
Tags are those of today: the dataset keeps no history of tags. Pages placed by their links follow their linked pages;
pages on the outer ring stay where they are.

Output: {"cutoffs": [month index of each frame], "slugs": [...], "pos": [one base64 string per frame: int16 x, y for every slug,
-32768 where the page did not exist yet]}. finalize.py puts the frames into the page's data.
"""
import base64, collections, json, math, sys, zlib
import numpy as np
import scipy.sparse as sp
import umap

DATA, OUT = sys.argv[1], sys.argv[2]
STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 12
SEED, ABSENT = 42, -32768
d = json.load(open(DATA, encoding="utf-8"))
N = len(d["slug"])
mo = np.array(d["mo"]); placed = np.array(d["placed"]); cluster = np.array(d["cluster"])
P = np.array(d["P"][0], dtype=float).reshape(-1, 2)
EVEN = d["meta"].get("defaultEven", 0.6)
ring = placed == 2


def spread(pos, idx, even=EVEN):
    """The page's own stretch: distances from the centre are pulled toward an even fill of the disc (see computePositions)."""
    out = pos.copy()
    r0 = np.sqrt((pos[idx] ** 2).sum(axis=1))
    rank = np.argsort(np.argsort(r0)) / max(1, len(idx) - 1)
    r1 = (1 - even) * r0 + even * 1000.0 * np.sqrt(rank)
    out[idx] *= (r1 / np.maximum(r0, 1e-9))[:, None]
    return out


# today's map as the page shows it: the last frame
today = spread(P, np.where(~ring)[0])

# links between pages, for the pages placed by their links
link_nb = collections.defaultdict(set)
for a, b in zip(d["cites"][0::2], d["cites"][1::2]):
    link_nb[a].add(b); link_nb[b].add(a)
_h = [zlib.crc32(s.lower().encode()) for s in d["slug"]]
jit = np.array([[(6 + (x // 3600 % 1000) / 100) * math.cos((x % 3600) / 3600 * 2 * math.pi),
                 (6 + (x // 3600 % 1000) / 100) * math.sin((x % 3600) / 3600 * 2 * math.pi)] for x in _h]) * 0.4

used = np.array(d["tagUsed"], dtype=bool)
tg = d["tg"]
n_reg = len(d["clusters"])
last = int(mo.max())
cutoffs = list(range(11, last, STEP))     # end of December 2008, 2009, …
if cutoffs and cutoffs[-1] >= last: cutoffs.pop()
cutoffs.append(last)
print(f"{N} pages; frames at {len(cutoffs)} dates: " + ", ".join(f"{2008 + c // 12}-{c % 12 + 1:02d}" for c in cutoffs), flush=True)


def features(idx):
    """Tags weighted by rarity among the pages of that date, plus the pull toward today's region (as in build.py)."""
    sub = set(idx.tolist())
    df = collections.Counter(t for i in idx for t in tg[i] if used[t])
    n = len(idx)
    rows, cols, vals = [], [], []
    for r, i in enumerate(idx):
        for t in tg[i]:
            if used[t] and df[t] >= 2:
                rows.append(r); cols.append(t); vals.append(math.log(n / df[t]))
    X = sp.csr_matrix((vals, (rows, cols)), shape=(n, len(used)))
    norm = np.sqrt(X.multiply(X).sum(axis=1)).A1
    ok = norm > 0
    norm[~ok] = 1
    X = sp.diags(1 / norm) @ X
    c = cluster[idx]
    oh = sp.csr_matrix((np.ones(int((c >= 0).sum())), (np.where(c >= 0)[0], c[c >= 0])), shape=(n, max(1, n_reg)))
    return sp.hstack([X, 0.2 * oh]).tocsr(), ok


def align(src, dst):
    """Turn, scale and shift src onto dst (least squares, never a mirror image)."""
    ma, mb = src.mean(axis=0), dst.mean(axis=0)
    u, s, vt = np.linalg.svd((src - ma).T @ (dst - mb))
    if np.linalg.det(u @ vt) < 0: u[:, -1] *= -1; s[-1] *= -1
    rot = u @ vt
    sc = s.sum() / ((src - ma) ** 2).sum()
    return lambda p: (p - ma) @ rot * sc + mb


N_TAGGED = int((placed == 0).sum())
_t = today[placed == 0]
R_TODAY = np.percentile(np.sqrt(((_t - np.median(_t, axis=0)) ** 2).sum(axis=1)), 98.5)
frames = [None] * len(cutoffs)
frames[-1] = today.copy()
for k in range(len(cutoffs) - 2, -1, -1):
    nxt = frames[k + 1]
    here = mo <= cutoffs[k]
    tagged = np.where(here & (placed == 0))[0]
    pos = np.full((N, 2), np.nan)
    if len(tagged) >= 30:
        F, ok = features(tagged)
        init = nxt[tagged] / 250.0 + np.random.RandomState(SEED).normal(0, 0.01, (len(tagged), 2))
        nn = min(20, len(tagged) - 1)
        emb = umap.UMAP(n_neighbors=nn, min_dist=0.3, spread=1.0, metric="cosine", random_state=SEED, n_epochs=200, init=init,
                        repulsion_strength=0.5, negative_sample_rate=3).fit_transform(F)
        emb = emb - np.median(emb, axis=0)
        emb = emb / np.percentile(np.sqrt((emb ** 2).sum(axis=1)), 98.5) * 1000.0
        tmp = np.zeros((N, 2)); tmp[tagged] = emb
        emb = spread(tmp, tagged)[tagged]
        emb = align(emb, nxt[tagged])(emb)
        # size: the map grows with the number of pages (a quarter power: about a third of today's size in 2008), around its own middle
        target = R_TODAY * (len(tagged) / N_TAGGED) ** 0.25
        mid = np.median(emb, axis=0)
        r98 = np.percentile(np.sqrt(((emb - mid) ** 2).sum(axis=1)), 98.5)
        pos[tagged] = mid + (emb - mid) * (target / max(r98, 1e-9))
    else:
        pos[tagged] = nxt[tagged]
    # pages placed by their links: beside their linked pages of that date, or where they will be next
    for i in np.where(here & (placed == 1))[0]:
        nb = [j for j in link_nb[i] if here[j] and placed[j] == 0]
        pos[i] = np.median(pos[nb], axis=0) + jit[i] if nb else nxt[i]
    pos[here & ring] = today[here & ring]
    frames[k] = pos
    moved = np.sqrt(((pos[tagged] - nxt[tagged]) ** 2).sum(axis=1)) if len(tagged) else np.zeros(1)
    print(f"  {2008 + cutoffs[k] // 12}-{cutoffs[k] % 12 + 1:02d}: {int(here.sum())} pages; "
          f"compared with the next frame, median move {np.median(moved):.0f}, 90% under {np.percentile(moved, 90):.0f}", flush=True)


def pack(pos, k):
    a = np.full((N, 2), ABSENT, dtype=np.int16)
    here = (mo <= cutoffs[k]) & ~np.isnan(pos[:, 0])
    a[here] = np.clip(np.round(pos[here]), -32000, 32000).astype(np.int16)
    return base64.b64encode(a.astype("<i2").tobytes()).decode()


json.dump({"cutoffs": cutoffs, "slugs": d["slug"], "pos": [pack(f, k) for k, f in enumerate(frames)]}, open(OUT, "w", encoding="utf-8"))
print("wrote", OUT)

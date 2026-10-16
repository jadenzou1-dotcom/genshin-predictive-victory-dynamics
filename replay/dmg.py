"""Damage-number reading for Predictive Victory Dynamics replays (1920x1080).

Usage: python -m replay.dmg <video.mp4> <round> [extracted_dir] [fps]
  -> <round>_dmg_raw.csv   every digit string read (before cleaning)
  -> <round>_hits.csv      cleaned hit events: match, battle time, value, element,
                           target side (the side whose unit the number pops over)

Why it is built this way
  * Colour masks alone fail: Cryo/Hydro numbers share colours with ice effects and
    HP bars. A text detector (rapidocr DBNet) on the frame upscaled 1.6x, run on
    each half separately, finds the numbers reliably.
  * Overlapping pops get read as one string ("17528" = 1752 + 578). But each attacker
    hits for a fixed amount against a given target, so values recur. A match's
    vocabulary = values read cleanly (exact, standalone) at least VOCAB_MIN times;
    any other read is mapped to the longest vocabulary value it contains, else dropped.
  * A number stays on screen for ~1 s, so the same value within POP_DIST px and
    POP_GAP s is one hit, not several.
Element = median hue/saturation of the bright pixels inside the number's box.
Target side = colour of the nearest overhead HP bar below the number (replay/bars.py).
"""
import csv, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import cv2, numpy as np
from rapidocr_onnxruntime import RapidOCR

from replay.bars import detect as detect_bars
from replay.extract import read_clock

Y0, Y1 = 230, 960
HALVES = ((200, 960), (960, 1720))
SCALE = 1.6
VOCAB_MIN, POP_DIST, POP_GAP = 3, 70, 1.0
_ocr = None


def ocr(img):
    global _ocr
    if _ocr is None:
        _ocr = RapidOCR(text_score=0.3, box_thresh=0.3, unclip_ratio=1.6)
    res, _ = _ocr(img)
    return res or []


def element(hsv_px):
    """Element from the bright pixels of a number (OpenCV HSV, hue 0..179)."""
    if len(hsv_px) == 0:
        return "?"
    bright = hsv_px[hsv_px[:, 2] > 170]
    if len(bright) < 10:
        return "?"
    sat = bright[bright[:, 1] > 60]
    if len(sat) < 0.35 * len(bright):
        return "Physical"
    h = float(np.median(sat[:, 0])); s = float(np.median(sat[:, 1]))
    if h < 23 or h >= 170: return "Pyro"
    if h < 34: return "Geo"
    if h < 60: return "Dendro"
    if h < 85: return "Anemo"
    if h < 119: return "Cryo" if (s < 150 or h < 92) else "Hydro"
    return "Electro"


def read_frame(frame):
    out = []
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    bars = detect_bars(frame)
    for x0, x1 in HALVES:
        roi = cv2.resize(frame[Y0:Y1, x0:x1], None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
        for box, txt, conf in ocr(roi):
            t = re.sub(r"\D", "", txt)
            if not t or ":" in txt or float(conf) < 0.5 or len(t) > 8:
                continue
            xs = [p[0] / SCALE + x0 for p in box]; ys = [p[1] / SCALE + Y0 for p in box]
            bx0, bx1, by0, by1 = int(min(xs)), int(max(xs)), int(min(ys)), int(max(ys))
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            px = hsv[max(by0, 0):by1, max(bx0, 0):bx1].reshape(-1, 3)
            below = [b for b in bars if b["y"] > cy - 20 and abs(b["x"] + b["total"] / 2 - cx) < 150]
            side = min(below, key=lambda b: (b["y"] - cy) ** 2 + (b["x"] + b["total"] / 2 - cx) ** 2)["side"] if below else ""
            out.append(dict(txt=t, conf=round(float(conf), 3), x=int(cx), y=int(cy), h=by1 - by0,
                            el=element(px), target=side))
    return out


POP_LIFE = 1.2   # a damage number is on screen for about a second


def pops(rows, value_of):
    """Group reads into pops: same value, nearby, within POP_LIFE s of the pop's FIRST read
    (anchoring to the first read stops identical repeated hits chaining into one)."""
    events = []
    for r in sorted(rows, key=lambda r: r["tau"]):
        v = value_of(r)
        if v is None:
            continue
        for e in reversed(events):
            if e["value"] == v and r["tau"] - e["tau"] <= POP_LIFE and abs(r["x"] - e["x"]) <= POP_DIST \
                    and -80 <= e["y"] - r["y"] <= 140:   # pops drift upward
                e["x"], e["y"] = r["x"], r["y"]; e["n"] += 1
                e["els"].append(r["el"]); e["tgts"].append(r["target"])
                break
        else:
            events.append(dict(tau=r["tau"], value=v, x=r["x"], y=r["y"], n=1, els=[r["el"]], tgts=[r["target"]]))
    return events


def clean(raw):
    """raw: rows with match, tau, txt, el, x, y, target. Returns hit events per match.
    Vocabulary = values of 3-5 digits read exactly in >= VOCAB_MIN distinct pops, minus
    fragments (a value contained in a more frequent vocabulary value, e.g. 752 / 175 inside
    1752) and merges (a value that contains another vocabulary value it is more than one
    digit longer than... handled by matching the longest contained value only for reads
    that are not themselves in the vocabulary)."""
    by = defaultdict(list)
    for r in raw:
        by[r["match"]].append(r)
    hits = []
    for m, rows in by.items():
        exact = pops([r for r in rows if 3 <= len(r["txt"]) <= 5], lambda r: r["txt"])
        cnt = Counter(e["value"] for e in exact)
        vocab = {v for v, c in cnt.items() if c >= VOCAB_MIN}
        vocab = {v for v in vocab if not any(v != w and v in w and cnt[w] >= cnt[v] for w in vocab)}
        # drop merges: a vocab value formed from two other vocab values overlapping
        vocab = {v for v in vocab if not any(w != v and w in v and cnt[w] > cnt[v] for w in vocab)}
        order = sorted(vocab, key=len, reverse=True)
        val = lambda r: (int(r["txt"]) if r["txt"] in vocab
                         else next((int(w) for w in order if w in r["txt"]), None))
        for e in pops(rows, val):
            el = Counter(x for x in e["els"] if x != "?").most_common(1)
            tg = Counter(x for x in e["tgts"] if x).most_common(1)
            hits.append(dict(match=m, tau=round(e["tau"], 2), value=e["value"], element=el[0][0] if el else "?",
                             target=tg[0][0] if tg else "", frames=e["n"]))
    return hits


def reclean(rnd, d="data/replays/extracted"):
    d = Path(d)
    raw = []
    for r in csv.DictReader(open(d / f"{rnd}_dmg_raw.csv")):
        r["tau"] = float(r["tau"]); r["x"] = int(r["x"]); r["y"] = int(r["y"]); raw.append(r)
    hits = clean(raw)
    with open(d / f"{rnd}_hits.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["match", "tau", "value", "element", "target", "frames"]); w.writeheader()
        for h in hits: w.writerow(h)
    print(f"{rnd}: {len(raw)} raw reads -> {len(hits)} hits")


def main(video, rnd, d="data/replays/extracted", fps_out=5):
    d = Path(d)
    cap = cv2.VideoCapture(str(video)); fps = cap.get(cv2.CAP_PROP_FPS)
    step = max(1, round(fps / fps_out))
    raw, i, match, last_clock, v0 = [], 0, 0, None, {}
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            _, f = cap.retrieve()
            vt = i / fps
            clock = read_clock(f)
            if clock is not None:
                if last_clock is None or clock > last_clock + 5:
                    match += 1
                    v0[match] = vt - (45 - clock)
                last_clock = clock
            if match and (clock is not None or (last_clock is not None and last_clock <= 1)):
                tau = vt - v0[match]
                if tau <= 75:
                    for r in read_frame(f):
                        r.update(match=match, tau=round(tau, 2), vt=round(vt, 2)); raw.append(r)
        i += 1
    cols = ["match", "vt", "tau", "txt", "conf", "x", "y", "h", "el", "target"]
    with open(d / f"{rnd}_dmg_raw.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for r in raw: w.writerow({k: r[k] for k in cols})
    hits = clean(raw)
    with open(d / f"{rnd}_hits.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["match", "tau", "value", "element", "target", "frames"]); w.writeheader()
        for h in hits: w.writerow(h)
    print(f"{rnd}: {len(raw)} raw reads -> {len(hits)} hits")


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "--reclean":
        for rnd in a[2:]: reclean(rnd)
        sys.exit()
    main(a[1], a[2], a[3] if len(a) > 3 else "data/replays/extracted", int(a[4]) if len(a) > 4 else 5)

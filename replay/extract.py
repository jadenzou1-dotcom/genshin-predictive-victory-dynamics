"""Extract everything measurable from a Predictive Victory Dynamics replay recording.

Usage: python -m replay.extract <video.mp4> <round> <out_dir> [fps]

Writes to <out_dir>/<round>_*.csv:
  frames.csv  one row per sampled frame (default 10/s): video time, match, clock
              (OCR, seconds left), team HP bar fill L/R, visible unit bars L/R,
              sum of visible unit HP fractions L/R
  bars.csv    every detected overhead unit bar: side, x, y, filled px, total px, hp fraction
  events.csv  commentary lines (OCR, ~2/s, de-duplicated) with video time and clock

A frame belongs to a battle when the clock is readable. Matches are numbered in order
of appearance (a jump of the clock back up to ~45 s starts a new match).
"""
import csv, re, sys
from pathlib import Path
import cv2, numpy as np
from rapidocr_onnxruntime import RapidOCR

from replay.bars import detect

TEAM_Y, TEAM_L, TEAM_R = 175, (666, 934), (988, 1254)   # top team HP bars (1920x1080)
CLOCK_BOX = (830, 195, 1090, 260)                        # x0, y0, x1, y1
TALK_BAND = (660, 860)                                    # rows where commentary boxes appear

_ocr = None


def ocr(img):
    global _ocr
    if _ocr is None:
        _ocr = RapidOCR()
    res, _ = _ocr(img)
    return res or []


def team_fill(f):
    band = f[TEAM_Y - 2:TEAM_Y + 3].astype(int)
    b, g, r = band[..., 0], band[..., 1], band[..., 2]
    red = ((r > 180) & (g < 130) & (b < 130)).mean(0) > 0.5
    blue = ((b > 200) & (g > 150) & (r < 150)).mean(0) > 0.5
    return float(red[TEAM_L[0]:TEAM_L[1]].mean()), float(blue[TEAM_R[0]:TEAM_R[1]].mean())


def read_clock(f):
    x0, y0, x1, y1 = CLOCK_BOX
    for _, txt, _ in ocr(f[y0:y1, x0:x1]):
        m = re.search(r"(\d)(\d)\s*[:：.]\s*(\d)(\d)\s*$", txt.replace(" ", ""))
        if m:
            a, b, c, d = map(int, m.groups())
            return (a * 10 + b) * 60 + c * 10 + d
    return None


def read_talk(f):
    lines = []
    for x0, x1 in ((0, 960), (960, 1920)):        # the detector misses text on very wide crops
        for box, txt, conf in ocr(f[TALK_BAND[0]:TALK_BAND[1], x0:x1]):
            if float(conf) > 0.75 and sum(ch.isalpha() for ch in txt) >= 8:
                lines.append(txt.strip())
    return " ".join(lines)


def main(video, rnd, out_dir, fps_out=10):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video)); fps = cap.get(cv2.CAP_PROP_FPS)
    step = max(1, round(fps / fps_out))
    fw = csv.writer(open(out / f"{rnd}_frames.csv", "w", newline=""))
    fw.writerow(["vt", "match", "clock", "team_L", "team_R", "bars_L", "bars_R", "hpsum_L", "hpsum_R"])
    bw = csv.writer(open(out / f"{rnd}_bars.csv", "w", newline=""))
    bw.writerow(["vt", "match", "side", "x", "y", "filled", "total", "frac"])
    ew = csv.writer(open(out / f"{rnd}_events.csv", "w", newline=""))
    ew.writerow(["vt", "match", "clock", "text"])
    i, match, last_clock, last_talk, clock = 0, 0, None, "", None
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            _, f = cap.retrieve()
            vt = round(i / fps, 2)
            if i % (step * 5) == 0:          # clock OCR twice a second
                clock = read_clock(f)
                if clock is not None:
                    if last_clock is None or clock > last_clock + 5:
                        match += 1
                    last_clock = clock
            in_battle = last_clock is not None and clock is not None
            tl, tr = team_fill(f)
            if in_battle or (last_clock is not None and last_clock <= 1 and (tl > 0 or tr > 0)):
                bars = detect(f)
                nL = [b for b in bars if b["side"] == "L"]; nR = [b for b in bars if b["side"] == "R"]
                fr = lambda b: b["filled"] / max(b["total"], b["filled"])
                fw.writerow([vt, match, clock if clock is not None else "", round(tl, 3), round(tr, 3),
                             len(nL), len(nR), round(sum(map(fr, nL)), 3), round(sum(map(fr, nR)), 3)])
                for b in bars:
                    bw.writerow([vt, match, b["side"], b["x"], b["y"], b["filled"], b["total"], round(fr(b), 3)])
                if i % (step * 5) == 0:
                    talk = read_talk(f)
                    key = "".join(ch for ch in talk.lower() if ch.isalpha())[:30]
                    if talk and key != last_talk:
                        ew.writerow([vt, match, clock if clock is not None else "", talk]); last_talk = key
        i += 1


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 10)

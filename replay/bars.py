"""Per-unit overhead HP bar detection for Predictive Victory Dynamics replays (1920x1080).

Each living unit shows a ~4 px bar above it: bright red (left team) or light blue
(right team) for remaining HP, followed by a dark segment for HP already lost.
detect(frame) returns one record per visible bar: side, x, y, filled px, total px.
"""
import cv2, numpy as np

Y0, Y1 = 230, 960          # battle area (excludes team bars, clock, bottom banner)


def _dark_seg(roi, y, h, x):
    """Lost-HP segment: dark, and darker than the scene just above and below the bar."""
    px = roi[y + h // 2, x].astype(int)
    if px.max() >= 115:
        return False
    up = roi[max(y - 3, 0), x].astype(int).mean()
    dn = roi[min(y + h + 2, roi.shape[0] - 1), x].astype(int).mean()
    return px.mean() < min(up, dn) - 12


def detect(frame):
    roi = frame[Y0:Y1]
    b, g, r = (roi[..., i].astype(np.int16) for i in range(3))
    masks = {"L": (r > 215) & (g < 120) & (b < 130),
             "R": (b > 215) & (g > 140) & (g < 215) & (r < 150)}
    out = []
    W = roi.shape[1]
    for side, m in masks.items():
        n, _, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
        for i in range(1, n):
            x, y, w, h, a = st[i]
            if not (2 <= h <= 9 and w >= 6 and w / h >= 2.5 and a / (w * h) > 0.55):
                continue
            xe = x + w
            skip = 0
            while xe < W and skip < 4 and not _dark_seg(roi, y, h, xe):
                xe += 1; skip += 1
            run, miss = 0, 0
            while xe + run < W and run < 400:
                if _dark_seg(roi, y, h, xe + run):
                    miss = 0
                else:
                    miss += 1
                    if miss > 2:
                        break
                run += 1
            run -= miss
            total = w + (skip + run if run >= 3 else 0)
            out.append(dict(side=side, x=int(x), y=int(y + Y0), filled=int(w), total=int(total)))
    return out

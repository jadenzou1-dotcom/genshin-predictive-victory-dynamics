"""Turn extracted replay frames into per-match observation curves on the battle clock.

Battle time tau = 45 - clock while the clock runs; after 00:00 (overtime, clock hidden)
tau = 45 + (video time since the clock first read 0).

For each match and each whole second tau = 0..T:
  hp_L, hp_R      team HP bar fill (median over that second)
  alive_L/R       visible unit bars, smoothed: forward-looking max over 4 s (units hidden
                  behind effects or off camera can't be counted, but a dead unit never
                  comes back), then a running minimum so the curve can only fall; normalised by the count at the start of the fight
Usage: python -m replay.observe <round> [extracted_dir]   -> <round>_curves.csv
"""
import csv, sys
from collections import defaultdict
from pathlib import Path
from statistics import median

CLOCK = 45


MIN_BAR_PX = 30   # real overhead HP bars are ~38-57 px long; elemental effects make 6-20 px blobs
                  # that were being counted as units (panel agent 5: Sappho read as 5 bars in R16-A M2)


def load_frames(path):
    rows = list(csv.DictReader(open(path)))
    bars_path = Path(str(path).replace("_frames.csv", "_bars.csv"))
    if bars_path.exists():   # recount bodies from bars.csv, keeping only bar-length detections
        cnt = defaultdict(lambda: {"L": 0, "R": 0})
        for b in csv.DictReader(open(bars_path)):
            if int(b["total"]) >= MIN_BAR_PX:
                cnt[(b["vt"], b["match"])][b["side"]] += 1
        for r in rows:
            c = cnt.get((r["vt"], r["match"]), {"L": 0, "R": 0})
            r["bars_L"], r["bars_R"] = c["L"], c["R"]
    by = defaultdict(list)
    for r in rows:
        by[int(r["match"])].append(r)
    return by


def battle_time(rows):
    """Assign tau to each frame row of one match (fills clock gaps by video time)."""
    anchors = [(float(r["vt"]), int(r["clock"])) for r in rows if r["clock"] != ""]
    if not anchors:
        return []
    # robust offset: tau = vt - v0 where v0 = median(vt - (45 - clock)) over clock reads
    v0 = median(vt - (CLOCK - c) for vt, c in anchors if c > 0) if any(c > 0 for _, c in anchors) else anchors[0][0] - CLOCK
    out = []
    for r in rows:
        tau = float(r["vt"]) - v0
        if tau >= -0.5:
            out.append((tau, r))
    return out


def curves(rows):
    tr = battle_time(rows)
    if not tr:
        return []
    sec = defaultdict(list)
    for tau, r in tr:
        sec[int(max(tau, 0))].append(r)
    T = max(sec)
    raw = []
    for s in range(T + 1):
        rs = sec.get(s, [])
        if not rs:
            raw.append(None); continue
        raw.append(dict(hp_L=median(float(r["team_L"]) for r in rs), hp_R=median(float(r["team_R"]) for r in rs),
                        n_L=max(int(r["bars_L"]) for r in rs), n_R=max(int(r["bars_R"]) for r in rs)))
    # forward-fill gaps
    for i in range(len(raw)):
        if raw[i] is None:
            raw[i] = dict(raw[i - 1]) if i else dict(hp_L=1.0, hp_R=1.0, n_L=0, n_R=0)
    # end of fight: the loser's bar is empty; stop once one side reads 0 for 1 s
    end = len(raw)
    for i in range(1, len(raw)):
        if raw[i]["hp_L"] == 0 and raw[i - 1]["hp_L"] == 0 or raw[i]["hp_R"] == 0 and raw[i - 1]["hp_R"] == 0:
            end = i + 1; break
    raw = raw[:end]
    out = []
    for side in "LR":
        k = f"n_{side}"
        # forward-looking max over the next 4 s bridges short occlusions without delaying a
        # death (a death at t lowers every window starting at or after t); running min then
        # enforces "dead stays dead"
        sm = [max(raw[j][k] for j in range(i, min(len(raw), i + 5))) for i in range(len(raw))]
        for i in range(1, len(sm)):
            sm[i] = min(sm[i], sm[i - 1])
        n0 = max(sm[:4]) or 1
        for i, v in enumerate(sm):
            raw[i][f"alive_{side}"] = round(v / n0, 3)
            raw[i][f"n0_{side}"] = n0
    for i, r in enumerate(raw):
        out.append(dict(tau=i, hp_L=round(r["hp_L"], 3), hp_R=round(r["hp_R"], 3),
                        alive_L=r["alive_L"], alive_R=r["alive_R"], n0_L=r["n0_L"], n0_R=r["n0_R"]))
    return out


def main(rnd, d="data/replays/extracted"):
    by = load_frames(Path(d) / f"{rnd}_frames.csv")
    w = csv.writer(open(Path(d) / f"{rnd}_curves.csv", "w", newline=""))
    cols = ["tau", "hp_L", "hp_R", "alive_L", "alive_R", "n0_L", "n0_R"]
    w.writerow(["match"] + cols)
    for m in sorted(by):
        for c in curves(by[m]):
            w.writerow([m] + [c[k] for k in cols])


def load_curves(rnd, d="data/replays/extracted"):
    p = Path(d) / f"{rnd}_curves.csv"
    if not p.exists():
        return {}
    by = defaultdict(list)
    for r in csv.DictReader(open(p)):
        by[r["match"]].append({k: float(v) for k, v in r.items() if k != "match"})
    return by


if __name__ == "__main__":
    main(*sys.argv[1:])

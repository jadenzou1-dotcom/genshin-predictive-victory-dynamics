"""Allocate one round's emblems under each strategy.

Reads data/matches.csv (model_p_left + multipliers) for a round and prints:
  A  max-Sharpe      : tangency portfolio, weights ∝ excess EV / variance
  B  max-EV          : everything on the single highest-EV leg
  benchmarks (paper only, not played):
    naive-underdog   : split evenly across the highest-multiplier side of each match
    crowd-favourite  : split evenly across the most-supported side of each match

Each match is an independent binary bet. Excess EV is measured over the
guaranteed 10 points per emblem. Assumes one shared pool of emblems per round.

Usage: python strategies.py <round> [emblems]
"""
import csv, math, sys
from pathlib import Path

FLOOR = 10
rnd = sys.argv[1]
POOL = int(sys.argv[2]) if len(sys.argv) > 2 else 100

legs = []
for m in csv.DictReader(open(Path(__file__).parent / "data" / "matches.csv")):
    if m["round"] != rnd or not m["model_p_left"]: continue
    pl = float(m["model_p_left"])
    for side, team, p, mult, sup in (("L", m["left_team"], pl, float(m["left_mult"]), float(m["left_support_pct"])),
                                     ("R", m["right_team"], 1 - pl, float(m["right_mult"]), float(m["right_support_pct"]))):
        mu = p * mult + (1 - p) * FLOOR
        sd = (mult - FLOOR) * math.sqrt(p * (1 - p))
        legs.append(dict(match=m["match"], side=side, team=team, p=p, mult=mult, sup=sup,
                         mu=mu, sd=sd, sharpe=(mu - FLOOR) / sd if sd else 0))

def stats(w):  # w: list of emblem counts aligned with legs (independent across matches)
    mu = sum(x * l["mu"] for x, l in zip(w, legs))
    var = sum((x * l["sd"]) ** 2 for x, l in zip(w, legs))
    sd = math.sqrt(var)
    return mu, sd, (mu - FLOOR * sum(w)) / sd if sd else float("inf")

def show(name, w):
    mu, sd, sh = stats(w)
    picks = ", ".join(f"{x:.0f} on {l['team']} (M{l['match']})" for x, l in zip(w, legs) if x >= 0.5)
    print(f"{name:18s} EV {mu:6.0f}  SD {sd:6.0f}  Sharpe {sh:5.2f}   {picks}")

print(f"Per-emblem legs, {rnd}:")
for l in legs:
    print(f"  M{l['match']} {l['team'][:30]:30s} p={l['p']:.3f} x{l['mult']:<4g} EV {l['mu']:5.1f} SD {l['sd']:5.1f} Sharpe {l['sharpe']:.2f}")
print()

# A: tangency. Can't hold both sides of one match, so per match keep the higher-Sharpe side.
best = {}
for i, l in enumerate(legs):
    if l["match"] not in best or l["sharpe"] > legs[best[l["match"]]]["sharpe"]:
        best[l["match"]] = i
raw = {i: (legs[i]["mu"] - FLOOR) / legs[i]["sd"] ** 2 for i in best.values()}
tot = sum(raw.values())
show("A  max-Sharpe", [POOL * raw.get(i, 0) / tot for i in range(len(legs))])

# B: max EV, corner solution
top = max(range(len(legs)), key=lambda i: legs[i]["mu"])
show("B  max-EV", [POOL if i == top else 0 for i in range(len(legs))])

print("\nPaper benchmarks (not played):")
for name, key in (("naive-underdog", "mult"), ("crowd-favourite", "sup")):
    sel = {}
    for i, l in enumerate(legs):
        if l["match"] not in sel or l[key] > legs[sel[l["match"]]][key]:
            sel[l["match"]] = i
    show(name, [POOL / len(sel) if i in sel.values() else 0 for i in range(len(legs))])

"""Allocate one round's emblems.

Each match is an independent binary bet: emblems e on a side with win probability p and
multiplier M score e*M if it wins and e*10 if it loses. Up to CAP (100) emblems per match.

  A  max-CE   : maximise CE = EV - (lambda/2) * Var over the side and emblem count of every
                match (exhaustive grid). lambda = risk aversion; lambda = 0 is pure EV.
  B  max-EV   : CAP on the higher-EV side of every match (every emblem earns >= 10, so EV
                is maximised by spending the cap on the better side of each match)
  benchmarks (paper only): naive-underdog, crowd-favourite (CAP on that side of each match)

Probabilities come from blend.py (sim stacked with the crowd) unless --model is given,
which uses the raw sim probability. A lambda sweep is printed because lambda has not
been fixed yet (README "Strategy decisions" #2).

Usage: python strategies.py <round> [--pool N] [--lambda L] [--model]
"""
import argparse, csv
from pathlib import Path
import blend

FLOOR, CAP = 10, 100
ap = argparse.ArgumentParser()
ap.add_argument("round")
ap.add_argument("--pool", type=int, default=2 * CAP, help="emblems available this round")
ap.add_argument("--lambda", dest="lam", type=float, default=None)
ap.add_argument("--model", action="store_true", help="use raw sim probability instead of the blend")
a = ap.parse_args()

matches = blend.load()
train = blend.training_rows(matches)
games = []
for m in matches:
    if m["round"] != a.round or not m["model_p_left"]:
        continue
    pm, pc = float(m["model_p_left"]), float(m["left_support_pct"]) / 100
    p = pm if a.model else blend.predict(train, pm, pc)
    games.append(dict(match=m["match"], sides=[
        dict(team=m["left_team"], p=p, M=float(m["left_mult"]), sup=float(m["left_support_pct"])),
        dict(team=m["right_team"], p=1 - p, M=float(m["right_mult"]), sup=float(m["right_support_pct"]))]))


def leg(s, e):
    """EV and variance of e emblems on side s."""
    ev = e * (s["p"] * s["M"] + (1 - s["p"]) * FLOOR)
    var = (e * (s["M"] - FLOOR)) ** 2 * s["p"] * (1 - s["p"])
    return ev, var


def best_ce(lam, pool):
    """Exhaustive search (side x emblems in steps of 5) for max CE under the pool limit."""
    best = None
    def rec(i, left, ev, var, picks):
        nonlocal best
        if i == len(games):
            ce = ev - lam / 2 * var
            if best is None or ce > best[0]:
                best = (ce, ev, var, picks)
            return
        for si, s in enumerate(games[i]["sides"]):
            for e in range(0, min(CAP, left) + 1, 5):
                lev, lvar = leg(s, e)
                rec(i + 1, left - e, ev + lev, var + lvar, picks + [(e, s["team"], games[i]["match"])])
    rec(0, pool, 0.0, 0.0, [])
    return best


def show(name, ev, var, picks):
    txt = ", ".join(f"{e} on {t} (M{m})" for e, t, m in picks if e)
    print(f"{name:22s} EV {ev:7.0f}  SD {var ** 0.5:6.0f}   {txt}")


src = "raw sim" if a.model else "sim+crowd blend"
print(f"{a.round}: probabilities from {src}; pool {a.pool}, cap {CAP}/match")
for g in games:
    for s in g["sides"]:
        ev1, var1 = leg(s, 1)
        print(f"  M{g['match']} {s['team'][:32]:32s} p={s['p']:.3f} x{s['M']:<4g} EV/emblem {ev1:5.1f}")
print()
lams = [a.lam] if a.lam is not None else [0.0, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4]
for lam in lams:
    ce, ev, var, picks = best_ce(lam, a.pool)
    show(f"A  max-CE  lambda={lam:g}", ev, var, picks)

picks, ev, var = [], 0.0, 0.0
for g in games:
    s = max(g["sides"], key=lambda s: leg(s, 1)[0])
    e = min(CAP, a.pool - sum(p[0] for p in picks))
    lev, lvar = leg(s, e); ev += lev; var += lvar; picks.append((e, s["team"], g["match"]))
show("B  max-EV", ev, var, picks)

print("\nPaper benchmarks (not played):")
for name, key in (("naive-underdog", "M"), ("crowd-favourite", "sup")):
    picks, ev, var = [], 0.0, 0.0
    for g in games:
        s = max(g["sides"], key=lambda s: s[key])
        lev, lvar = leg(s, CAP); ev += lev; var += lvar; picks.append((CAP, s["team"], g["match"]))
    show(name, ev, var, picks)

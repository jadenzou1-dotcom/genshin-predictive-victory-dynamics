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
ap.add_argument("--w", type=float, default=None, help="fixed model weight in the log-odds blend (0 = crowd only)")
ap.add_argument("--have", type=float, default=None, help="prediction points already earned (enables P(>=16000))")
ap.add_argument("--future-p", type=float, default=0.68, help="win prob of a typical future favourite bet")
ap.add_argument("--future-n", type=int, default=4, help="future 100-emblem favourite bets (x30) after tonight")
a = ap.parse_args()

matches = blend.load()
train = blend.training_rows(matches)
games = []
for m in matches:
    if m["round"] != a.round or not m["model_p_left"]:
        continue
    pm, pc = float(m["model_p_left"]), float(m["left_support_pct"]) / 100
    p = pm if a.model else (blend.blend(pm, pc, a.w) if a.w is not None else blend.predict(train, pm, pc))
    games.append(dict(match=m["match"], pm=pm, pc=pc, sides=[
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


# ---- break-even and trust-weight sweep (panel agents 1 and 4) ----
print("\nBreak-even win probability (bet the underdog side if its P exceeds this):")
for g in games:
    a_, b_ = g["sides"]
    be = (b_["M"] - FLOOR) / ((a_["M"] - FLOOR) + (b_["M"] - FLOOR))
    print(f"  M{g['match']} {a_['team'][:28]:28s} x{a_['M']:g} vs x{b_['M']:g}: P({a_['team'][:14]}) > {be:.3f}")
print("\nPick by model weight w (log-odds blend; w = share of trust in the sim):")
for g in games:
    row = []
    for wv in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0):
        p = blend.blend(g["pm"], g["pc"], wv)
        ev = [p * g["sides"][0]["M"] + (1 - p) * FLOOR, (1 - p) * g["sides"][1]["M"] + p * FLOOR]
        row.append(f"w={wv:.1f}:{'L' if ev[0] > ev[1] else 'R'}({p:.2f})")
    print(f"  M{g['match']}: " + "  ".join(row))

# ---- probability of reaching the 16,000-point tier (panel agent 4) ----
if a.have is not None:
    from itertools import product
    from math import comb
    def p16(alloc):
        """alloc: per match (side index, emblems). Future: future_n favourite bets of 100 at x30."""
        tot = 0.0
        for outs in product((0, 1), repeat=len(games)):
            pr, pts = 1.0, a.have
            for g, (si, e), o in zip(games, alloc, outs):
                s = g["sides"][si]
                pr *= s["p"] if o else 1 - s["p"]
                pts += e * (s["M"] if o else FLOOR)
            for k in range(a.future_n + 1):
                fp = comb(a.future_n, k) * a.future_p ** k * (1 - a.future_p) ** (a.future_n - k)
                if pts + 100 * (30 * k + 10 * (a.future_n - k)) >= 16000:
                    tot += pr * fp
        return tot
    best = []
    sides = [range(2)] * len(games)
    for choice in product(*[[(si, e) for si in (0, 1) for e in range(0, 101, 10)] for _ in games]):
        ev = sum(leg(g["sides"][si], e)[0] for g, (si, e) in zip(games, choice))
        best.append((round(p16(choice), 3), ev, choice))
    best.sort(key=lambda x: (-x[0], -x[1]))
    print(f"\nP(reach 16,000) with {a.have:.0f} pts now, {a.future_n} future fav bets at p={a.future_p}:")
    for pr, ev, ch in best[:3]:
        print(f"  P={pr:.3f} EV {ev:6.0f}  " + ", ".join(f"{e} on {games[i]['sides'][si]['team'][:24]}" for i, (si, e) in enumerate(ch) if e))
    allin = tuple((max(range(2), key=lambda si: leg(g["sides"][si], 1)[0]), 100) for g in games)
    print(f"  max-EV allocation: P={p16(allin):.3f}")

"""Strict walk-forward backtest: the final model's code, but only what was knowable before each round.

The ordinary walk-forward in loo.py reweights the main posterior by earlier replays only. That
removes parameter look-ahead, but its draws were sampled from priors centred on values measured
in LATER replays (the overtime pulse, hit sizes, squad HP), and it switches on mechanics that
were only discovered later (Sappho's frost field, the Ninken plunge). This script removes that
leakage too. For each target round T it:

  1. builds a prior from what was known before T. Every replay-measured value or replay-discovered
     mechanic is used only from the round AFTER the replay it came from (KNOWN_FROM below).
     Before that, a measured value gets a vague prior and a discovered mechanic is switched off;
  2. fits that prior to the replays of rounds before T only (same kernel ABC as calibrate_traj.py);
  3. predicts every match in T with the fitted draws.

Still shared with the final model (can't be removed without rewriting the sim): the overall
battle engine (grid, movement, targeting modes, reactions, squads), the unit cards themselves
(known before every match), and the DEF x RES hit formula (public game maths).

Output: data/backtest_strict_wf.csv.  Usage: python walk_forward_strict.py [draws] [workers]
"""
import copy
import csv
import math
import random
import re
import sys
from itertools import accumulate
from multiprocessing import Pool

import calibrate_traj as ct
import sim

ORDER = ["R16-A", "R16-B", "R16-C", "R16-D", "QF-A", "QF-B", "SF", "Final"]
idx = ORDER.index
M = 12            # unit draws per (global draw, replay)
TARGET_ESS = 40
SHRINK_N0 = sim.SHRINK_N0

# First target round where each replay-derived item may be used (= round after its source replay).
KNOWN_FROM = {
    "sappho_splash": "R16-B",   # R16-A frame study: volleys splash 3 targets
    "k_near_1": "R16-B",        # counters ~1x: damage numbers from R16-A onward
    "boss_freeze_ev": "R16-B",  # R16-A frame sweep: Sappho never froze
    "per_member": "R16-C",      # full HP per squad member: R16-B damage totals vs HP bars
    "flat_reactions": "R16-D",  # flat 400/800 reaction damage: R16-C
    "overtime": "QF-B",         # overtime pulse ~11% max HP: first measured in QF-A M1
    "kill_plunge": "SF",        # Ninken post-kill plunge: QF-B frames
    "self_aura": "SF",          # slimes' permanent own-element aura: R16-D/QF-B
    "frost_field": "Final",     # Sappho's frost field: SF M1
}


def known(item, T):
    return idx(T) >= idx(KNOWN_FROM[item])


def strict_prior_global(T):
    G = sim.prior_global()
    if not known("k_near_1", T):
        G["k"] = random.uniform(1.0, 2.0)
    if not known("boss_freeze_ev", T):
        G["boss_freeze"] = float(random.random() < 0.5)
    if not known("per_member", T):
        G["per_member"] = float(random.random() < 0.5)   # shared vs full HP per squad member
    if not known("overtime", T):
        G["ot_pct"] = random.uniform(0.0, 0.30)
        G["ot_period"] = random.uniform(2.0, 15.0)
    G["flat_rx"] = sim.FLAT_RX if known("flat_reactions", T) else random.uniform(200.0, 2500.0)
    return G


def strict_units(T):
    """Unit table as it was knowable before T: replay-discovered flags removed."""
    U = copy.deepcopy(ct.units)
    for u in U.values():
        if not known("kill_plunge", T):
            u["kill_plunge"] = "no"
        if not known("self_aura", T):
            u["self_aura"] = "no"
        if not known("frost_field", T):
            u["frost_field"] = "no"
    if not known("sappho_splash", T) and "sappho_amidst_the_waves" in U:
        s = U["sappho_amidst_the_waves"]
        s["special_tags"] = s.get("special_tags", "").replace("Splash AoE", "").strip("; ,")
        s["secondary_aoe"] = "no"
    return U


MEAS = {}
for r in csv.DictReader(open(sim.DATA / "unit_hits_measured.csv")):
    rounds = re.findall(r"R16-[A-D]|QF-[AB]|SF|Final", r["source"])
    MEAS[r["unit_id"]] = (float(r["hit_ratio"]), min(rounds, key=idx))


def strict_prior_unit(uid, T):
    m = MEAS.get(uid)
    if m and idx(m[1]) < idx(T):
        return dict(dmg=random.lognormvariate(math.log(m[0] / sim.HIT_G), 0.2), iv=random.uniform(1.0, 6.0))
    return dict(dmg=random.lognormvariate(0.0, 0.45), iv=random.uniform(1.0, 6.0))


def run(units, pl, G, U, trace=None):
    sim.FLAT_RX = G["flat_rx"]          # module constant in sim.py; set per draw
    return sim.run(units, pl, G, U, trace=trace)


def one(args):
    seed, T = args
    random.seed(seed)
    units = strict_units(T)
    G = strict_prior_global(T)
    past = [o for o in ct.obs if idx(o["round"]) < idx(T)]
    out = []
    for o in past:
        pl = ct.plists[(o["round"], o["match"])]
        mids = sorted({p["unit_id"] for p in pl})
        dl, Ul = [], []
        for _ in range(M):
            U = {u: strict_prior_unit(u, T) for u in mids}
            tr = []
            dl.append(ct.distance(o, run(units, pl, G, U, trace=tr), tr))
            Ul.append(U)
        out.append((f"{o['round']}_{o['match']}", dl, Ul, mids))
    return G, out


def fit(T, n, pool):
    res = pool.map(one, [(s, T) for s in range(n)], chunksize=10)
    if not res[0][1]:                  # R16-A: nothing earlier, prior only
        return [(G, {}) for G, _ in res], [1.0] * n, None
    for eps in [0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4, 0.6]:
        lw = []
        for _, out in res:
            s = 0.0
            for _, dl, _, _ in out:
                lik = sum(math.exp(-0.5 * (d / eps) ** 2) for d in dl) / len(dl)
                s = s + math.log(lik) if lik > 0 else -math.inf
            lw.append(s)
        mx = max(lw)
        w = [math.exp(x - mx) if x > -math.inf else 0.0 for x in lw]
        if sum(w) ** 2 / sum(x * x for x in w) >= TARGET_ESS:
            break
    rng = random.Random(12345)
    draws = []
    for G, out in res:                 # keep, per replay, one unit draw chosen by kernel weight
        picked = {}
        for key, dl, Ul, mids in out:
            ks = [math.exp(-0.5 * (d / eps) ** 2) for d in dl]
            picked[key] = rng.choices(Ul, weights=ks)[0] if sum(ks) > 0 else Ul[min(range(len(dl)), key=dl.__getitem__)]
        draws.append((G, picked))
    return draws, w, eps


def predict(T, match, draws, w, runs=2000):
    units = strict_units(T)
    pl = sim.match_units(ct.places if hasattr(ct, "places") else sim.load()[1], T, match)
    seen = {}                          # unit -> past replay keys it appeared in
    for o in ct.obs:
        if idx(o["round"]) < idx(T):
            key = f"{o['round']}_{o['match']}"
            for p in ct.plists[(o["round"], o["match"])]:
                seen.setdefault(p["unit_id"], []).append(key)
    ids = sorted({p["unit_id"] for p in pl})
    cw = list(accumulate(w))
    random.seed(7)
    left = 0
    for _ in range(runs):
        G, picked = random.choices(draws, cum_weights=cw)[0]
        U = {}
        for u in ids:
            src = sorted(set(seen.get(u, [])) & set(picked))
            n = len(src)
            if n and random.random() < n / (n + SHRINK_N0):
                U[u] = dict(picked[random.choice(src)][u])
            else:
                U[u] = strict_prior_unit(u, T)
        left += run(units, pl, G, U)[0] == "L"
    return left / runs


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    P = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    _, places, matches = sim.load()
    ct.places = places
    targets = [m for m in matches if m["model_p_left"] and m["round"] != "R16-D"]
    rows = []
    with Pool(P) as pool:
        for T in [r for r in ORDER if any(m["round"] == r for m in targets)]:
            draws, w, eps = fit(T, N, pool)
            ess = sum(w) ** 2 / sum(x * x for x in w)
            for m in [m for m in targets if m["round"] == T]:
                p = predict(T, m["match"], draws, w)
                rows.append(dict(round=T, match=m["match"], strict_wf_p_left=f"{p:.3f}",
                                 eps="" if eps is None else eps, ess=f"{ess:.0f}",
                                 past_replays=sum(idx(o["round"]) < idx(T) for o in ct.obs)))
                print(rows[-1], flush=True)
    with open(sim.DATA / "backtest_strict_wf.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print("wrote data/backtest_strict_wf.csv")

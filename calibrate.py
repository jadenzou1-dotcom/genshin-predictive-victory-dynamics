"""Calibrate sim parameters to observed replays (nested ABC rejection sampling).

A parameter draw "reproduces" a replay if the simulated battle has the right
winner, the winner's remaining HP within ±TOL_HP, and the loser wiped within
±TOL_T seconds. Global parameters are weighted by how often random per-unit
parameters reproduce every observed match. Kept draws (with weights) are written
to data/calibration_samples.csv and become the parameter source for sim.py.

Calibration is cumulative: it uses every round listed in data/replays/*_outcomes.csv.

Usage: python calibrate.py [draws]
"""
import csv, glob, random, statistics, sys
from pathlib import Path
import sim

TOL_HP, TOL_T = 0.15, 8.0
ROOT = Path(__file__).parent

obs = []
for f in sorted(glob.glob(str(ROOT / "data" / "replays" / "*_outcomes.csv"))):
    obs += list(csv.DictReader(open(f)))
units, places, _ = sim.load()
plists = {(o["round"], o["match"]): sim.match_units(places, o["round"], o["match"]) for o in obs}
ids = sorted({p["unit_id"] for pl in plists.values() for p in pl})

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2500   # global-parameter draws
M = 40                                                   # unit-parameter draws per match per global draw
random.seed(1)

def hit(o, res):
    w, hp, tw = res
    return (w == o["winner_side"] and abs(hp - float(o["winner_hp_frac"])) <= TOL_HP
            and tw is not None and abs(tw - float(o["loser_wiped_at_s"])) <= TOL_T)

# Nested ABC: matches share only the global parameters, so for each global draw G we
# estimate each match's acceptance probability with M independent unit-parameter draws.
# The weight of G is the product of those probabilities (an ABC likelihood estimate);
# for each match we keep one accepted unit draw at random.
kept = []
for i in range(N):
    G = sim.prior_global()
    weight, row = 1.0, dict(G)
    for o in obs:
        pl = plists[(o["round"], o["match"])]
        mids = sorted({p["unit_id"] for p in pl})
        good = []
        for _ in range(M):
            U = {u: sim.prior_unit() for u in mids}
            if hit(o, sim.run(units, pl, G, U)): good.append(U)
        if not good: weight = 0; break
        weight *= len(good) / M
        U = random.choice(good)
        for u in mids:
            for k in sim.UNIT_KEYS: row[f"{u}.{k}"] = U[u][k]
    if weight > 0:
        row["weight"] = weight
        kept.append(row)

print(f"{len(kept)} of {N} global draws reproduce every observed replay")
if not kept: sys.exit("no draws accepted; widen priors or tolerances")
with open(ROOT / "data" / "calibration_samples.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(kept[0].keys()))
    w.writeheader()
    for r in kept: w.writerow({k: f"{v:.4g}" for k, v in r.items()})

def q(xs):
    """Weighted 10/50/90% quantiles over kept draws."""
    pairs = sorted(zip(xs, (r["weight"] for r in kept)))
    tot = sum(w for _, w in pairs); out = []
    for target in (0.1, 0.5, 0.9):
        c = 0
        for x, w in pairs:
            c += w
            if c >= target * tot: out.append(x); break
    return out

print("\nparameter            prior median   posterior 10% / 50% / 90%")
prior = [sim.prior_global() for _ in range(20000)]
for k in sim.GLOBAL_KEYS:
    pm = statistics.median(p[k] for p in prior)
    lo, md, hi = q([r[k] for r in kept])
    print(f"  {k:18s} {pm:8.3f}       {lo:7.3f} / {md:7.3f} / {hi:7.3f}")
# dmg and iv trade off (only damage per second is identifiable), so report the
# per-unit damage-rate multiplier dmg/iv relative to its prior median.
pr = statistics.median(p["dmg"] / p["iv"] for p in (sim.prior_unit() for _ in range(20000)))
print("\nunit damage rate (dmg/iv) relative to prior median = 1.00   posterior 10% / 50% / 90%")
for u in ids:
    lo, md, hi = q([r[f"{u}.dmg"] / r[f"{u}.iv"] / pr for r in kept])
    print(f"  {u:32s} {lo:5.2f} / {md:5.2f} / {hi:5.2f}")

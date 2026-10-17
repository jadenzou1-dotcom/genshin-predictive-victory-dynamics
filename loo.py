"""Honest hindsight predictions: leave-one-replay-out (LOO) without refitting.

calibrate_traj.py draws parameters from the prior and stores, per draw and per replayed
match j, the kernel likelihood lik_j and the unit parameters picked for that match. The
posterior given every match EXCEPT m is then the same draws reweighted by prod_{j != m} lik_j
(the draws came from the prior, so no other correction is needed).

For the held-out match m:
  * global parameters come from a draw sampled with the LOO weights;
  * each unit in m uses its parameters from another replay it appeared in (shrunk toward
    the prior with the usual n/(n+2), n counted WITHOUT m), else a fresh prior draw.
So nothing fitted to m's own replay is used. Prints P(left) per held-out match and the
effective sample size of the LOO weights.

Usage: python loo.py [runs_per_match]
"""
import csv, glob, math, random, sys
import sim

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
units, places, matches = sim.load()
post = sim.load_posterior()
obs = []
for f in sorted(glob.glob(str(sim.DATA / "replays" / "*_outcomes.csv"))):
    obs += list(csv.DictReader(open(f)))
keys = [f"{o['round']}_{o['match']}" for o in obs]
appears = {}
for o, key in zip(obs, keys):
    for p in sim.match_units(places, o["round"], o["match"]):
        appears.setdefault(p["unit_id"], set()).add(key)


def loo(m_key):
    lw = []
    for r in post:
        s = 0.0
        for k in keys:
            if k == m_key:
                continue
            v = float(r.get(f"lik.{k}", 0))
            if v <= 0:
                s = -math.inf; break
            s += math.log(v)
        lw.append(s)
    mx = max(lw)
    w = [math.exp(x - mx) if x > -math.inf else 0.0 for x in lw]
    ess = sum(w) ** 2 / sum(x * x for x in w)
    rnd, mt = m_key.rsplit("_", 1)
    pl = sim.match_units(places, rnd, mt)
    ids = sorted({p["unit_id"] for p in pl})
    random.seed(7)
    left = 0
    for _ in range(N):
        row = random.choices(post, weights=w)[0]
        G = {k: float(row[k]) for k in sim.GLOBAL_KEYS if k in row}
        G["g"] = sim.HIT_G
        U = {}
        for u in ids:
            others = sorted(appears.get(u, set()) - {m_key})
            n = len(others)
            if n and random.random() < n / (n + sim.SHRINK_N0) and f"{others[0]}|{u}.dmg" in row:
                src = random.choice(others)
                U[u] = {k: float(row[f"{src}|{u}.{k}"]) for k in sim.UNIT_KEYS}
            else:
                U[u] = sim.prior_unit()
        left += sim.run(units, pl, G, U)[0] == "L"
    return left / N, ess


if __name__ == "__main__":
    for k in keys:
        p, ess = loo(k)
        print(f"{k}: LOO P(left) = {p:.3f}   (LOO effective sample {ess:.0f})")

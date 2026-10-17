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


ORDER = ["R16-A", "R16-B", "R16-C", "R16-D", "QF-A", "QF-B", "SF", "Final"]


def allowed_keys(m_key, mode):
    """'loo': every other replay. 'past': only replays from rounds before m's round."""
    rnd = m_key.rsplit("_", 1)[0]
    if mode == "loo":
        return [k for k in keys if k != m_key]
    return [k for k in keys if ORDER.index(k.rsplit("_", 1)[0]) < ORDER.index(rnd)]


def loo(m_key, mode="loo", target=None):
    """P(left) for match m_key (a 'round_match' string) using only the allowed replays."""
    use = allowed_keys(m_key, mode)
    lw = []
    for r in post:
        s = 0.0
        for k in use:
            v = float(r.get(f"lik.{k}", 0))
            if v <= 0:
                s = -math.inf; break
            s += math.log(v)
        lw.append(s)
    mx = max(lw)
    w = [math.exp(x - mx) if x > -math.inf else 0.0 for x in lw]
    if not use:                      # nothing allowed: plain prior draws
        w = [1.0] * len(post)
    ess = sum(w) ** 2 / sum(x * x for x in w)
    rnd, mt = m_key.rsplit("_", 1)
    pl = sim.match_units(places, rnd, mt)
    allowed = set(use)
    ids = sorted({p["unit_id"] for p in pl})
    from itertools import accumulate
    cw = list(accumulate(w))
    random.seed(7)
    left = 0
    for _ in range(N):
        row = random.choices(post, cum_weights=cw)[0]
        G = {k: float(row[k]) for k in sim.GLOBAL_KEYS if k in row}
        G["g"] = sim.HIT_G
        U = {}
        for u in ids:
            others = sorted(appears.get(u, set()) & allowed)
            n = len(others)
            if n and random.random() < n / (n + sim.SHRINK_N0) and f"{others[0]}|{u}.dmg" in row:
                src = random.choice(others)
                U[u] = {k: float(row[f"{src}|{u}.{k}"]) for k in sim.UNIT_KEYS}
            else:
                U[u] = sim.prior_unit()
        left += sim.run(units, pl, G, U)[0] == "L"
    return left / N, ess


if __name__ == "__main__":
    targets = sys.argv[2].split(",") if len(sys.argv) > 2 else keys
    for k in targets:
        p, ess = loo(k, "loo")
        q, ess2 = loo(k, "past")
        print(f"{k}: LOO P(left) = {p:.3f} (ESS {ess:.0f})   past-only P(left) = {q:.3f} (ESS {ess2:.0f})")

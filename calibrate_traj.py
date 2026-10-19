"""Calibrate sim parameters to full replay trajectories (kernel ABC).

calibrate.py only checks 3 numbers per replay (winner, winner HP, wipe time). This
version compares the whole fight, second by second, using what replay/extract.py and
replay/observe.py pull out of the recordings:
  * both team HP curves (top bars)
  * both teams' share of bodies still alive (overhead unit bars, smoothed)
and falls back to the 3-number summary for a replay with no extracted curves.

Distance per match:
    d = RMSE(team HP, both sides)  +  W_ALIVE * RMSE(alive share, both sides)
        + W_WIN * [simulated winner != observed winner]
over battle seconds 0..end of the observed fight (the side that finished first is
padded with its final state). Each draw gets kernel weight exp(-0.5 (d / EPS)^2), with
EPS chosen after the run as the smallest grid value leaving an effective sample >= 40.

Nested structure as before: a global draw G is shared by all matches; for each match,
M per-unit draws estimate that match's likelihood (mean kernel weight); G's weight is
the product over matches, and one unit draw per match is kept in proportion to its
kernel weight. Output replaces data/calibration_samples.csv (same columns + weight).

Usage: python calibrate_traj.py [global_draws] [workers]
"""
import csv, glob, math, random, statistics, sys
from multiprocessing import Pool
from pathlib import Path
import sim
from replay.observe import load_curves

ROOT = Path(__file__).parent
W_ALIVE, W_WIN = 0.5, 0.25
M = 20

obs = []
for f in sorted(glob.glob(str(ROOT / "data" / "replays" / "*_outcomes.csv"))):
    obs += list(csv.DictReader(open(f)))
units, places, _ = sim.load()
plists = {(o["round"], o["match"]): sim.match_units(places, o["round"], o["match"]) for o in obs}
curves = {}
for rnd in {o["round"] for o in obs}:
    for m, c in load_curves(rnd).items():
        curves[(rnd, m)] = c
# Anchor each observed curve to the wipe time logged in the outcomes file: truncate or
# extend (holding the last row) to that second, and set the loser's HP and alive share to 0
# on the final row. The extracted curve alone stops early when the winner's bar drops
# below the tracker floor (R16-C M2) and never shows the loser's last body dying.
for o in obs:
    key = (o["round"], o["match"])
    if key not in curves or not o["loser_wiped_at_s"]:
        continue
    end = int(math.ceil(float(o["loser_wiped_at_s"])))
    c = [dict(r) for r in curves[key][:end + 1]]
    while len(c) < end + 1:
        c.append(dict(c[-1], tau=len(c)))
    lo = "L" if o["winner_side"] == "R" else "R"
    c[-1][f"hp_{lo}"] = 0.0; c[-1][f"alive_{lo}"] = 0.0
    curves[key] = c
ids = sorted({p["unit_id"] for pl in plists.values() for p in pl})


def pad(seq, n):
    return seq + [seq[-1]] * (n - len(seq)) if seq else [None] * n


def distance(o, res, tr):
    w, hp, tw = res
    c = curves.get((o["round"], o["match"]))
    if not c:   # no extracted curves: 3-number summary, scaled like an RMSE
        d = abs(hp - float(o["winner_hp_frac"])) + (abs(tw - float(o["loser_wiped_at_s"])) / 30 if tw else 0.5)
        return d + (W_WIN if w != o["winner_side"] else 0)
    n = len(c)
    n0L, n0R = (tr[0][3] or 1), (tr[0][4] or 1)
    sim_rows = pad([(r[1], r[2], r[3] / n0L, r[4] / n0R) for r in tr], n)
    if tw is not None and len(tr) < n:   # after the sim's wipe the loser stays at 0
        last = list(sim_rows[len(tr) - 1])
        loser = "L" if w == "R" else "R"
        if loser == "L": last[0], last[2] = 0.0, 0.0
        else: last[1], last[3] = 0.0, 0.0
        sim_rows = sim_rows[:len(tr)] + [tuple(last)] * (n - len(tr))
    # alive share is only trusted for a side whose visible bar count at the start matches
    # its body count (+-25%); bosses can carry extra bars (shields), squads can overlap
    use = [abs(c[0]["n0_L"] - n0L) <= 0.25 * n0L, abs(c[0]["n0_R"] - n0R) <= 0.25 * n0R]
    # low-HP squad members fall below the bar detector's minimum fill and read as dead, so
    # alive share is down-weighted for sides that contain squads (panel agent 5)
    pl = plists[(o["round"], o["match"])]
    sq = [0.5 if any(int(units[p["unit_id"]]["members_per_squad"]) > 1 for p in pl if p["side"] == s) else 1.0
          for s in "LR"]
    se_hp = se_al = 0.0
    for s, ob in zip(sim_rows, c):
        se_hp += (s[0] - ob["hp_L"]) ** 2 + (s[1] - ob["hp_R"]) ** 2
        se_al += use[0] * sq[0] * (s[2] - ob["alive_L"]) ** 2 + use[1] * sq[1] * (s[3] - ob["alive_R"]) ** 2
    d = math.sqrt(se_hp / (2 * n)) + W_ALIVE * math.sqrt(se_al / (max(sum(use), 1) * n))
    return d + (W_WIN if w != o["winner_side"] else 0)


def one(seed):
    """One global draw: returns its parameters and, per match, the M unit draws with their
    distances. After EPS is chosen, one unit draw per match is sampled in proportion to its
    kernel weight (not the best one, which would make unit posteriors overconfident)."""
    random.seed(seed)
    G = sim.prior_global()
    row, ds = dict(G), []
    for o in obs:
        pl = plists[(o["round"], o["match"])]
        mids = sorted({p["unit_id"] for p in pl})
        dl, Ul = [], []
        for _ in range(M):
            U = {u: sim.prior_unit(u) for u in mids}
            tr = []
            dl.append(distance(o, sim.run(units, pl, G, U, trace=tr), tr)); Ul.append(U)
        ds.append((dl, Ul, mids))
    return row, ds


def weights(results, eps):
    lw = []
    for _, ds in results:
        s = 0.0
        for dl, _, _ in ds:
            lik = sum(math.exp(-0.5 * (d / eps) ** 2) for d in dl) / len(dl)
            if lik <= 0: s = -math.inf; break
            s += math.log(lik)
        lw.append(s)
    mx = max(lw)
    if mx == -math.inf: return None
    return [math.exp(x - mx) if x > -math.inf else 0.0 for x in lw]


def ess(w):
    return sum(w) ** 2 / sum(x * x for x in w) if any(w) else 0


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    P = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    print(f"replays: {len(obs)}  with full curves: {sum((o['round'], o['match']) in curves for o in obs)}")
    with Pool(P) as pool:
        results = pool.map(one, range(N), chunksize=10)
    # tolerance: the smallest EPS (from a grid) that leaves an effective sample of >= TARGET_ESS
    TARGET_ESS = 40
    w = None
    for eps in [0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4]:
        w = weights(results, eps)
        if w and ess(w) >= TARGET_ESS:
            break
    if not w:
        sys.exit("no draw has positive weight at any tolerance")
    print(f"tolerance EPS = {eps}  effective sample size {ess(w):.1f} of {N} draws"
          + ("" if ess(w) >= TARGET_ESS else "  (TARGET NOT REACHED: posterior is thin)"))
    random.seed(12345)
    kept = []
    # Every row is kept (not only high-weight ones) together with, per match, its likelihood
    # lik.<round>_<match> and the unit draw picked for that match (<round>_<match>|<unit>.<key>).
    # loo.py divides one match's likelihood out of the weights to get honest leave-one-out
    # predictions without refitting (panel agent 3).
    keys = [f"{o['round']}_{o['match']}" for o in obs]
    for (row, ds), wi in zip(results, w):
        for key, (dl, Ul, mids) in zip(keys, ds):
            ks = [math.exp(-0.5 * (d / eps) ** 2) for d in dl]
            row[f"lik.{key}"] = sum(ks) / len(ks)
            U = random.choices(Ul, weights=ks)[0] if sum(ks) > 0 else Ul[min(range(len(dl)), key=dl.__getitem__)]
            for u in mids:
                for k in sim.UNIT_KEYS:
                    row[f"{u}.{k}"] = U[u][k]; row[f"{key}|{u}.{k}"] = U[u][k]
        row["weight"] = wi; kept.append(row)
    print(f"{len(kept)} draws with non-negligible weight")
    cols = list(kept[0].keys())
    with open(ROOT / "data" / "calibration_samples.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in kept: w.writerow({k: f"{r.get(k, 0):.6g}" for k in cols})

    def q(xs):
        pairs = sorted(zip(xs, (r["weight"] for r in kept))); tot = sum(w for _, w in pairs); out = []
        for target in (0.1, 0.5, 0.9):
            c = 0
            for x, w in pairs:
                c += w
                if c >= target * tot: out.append(x); break
        return out
    print("\nparameter            posterior 10% / 50% / 90%")
    for k in sim.GLOBAL_KEYS:
        lo, md, hi = q([r[k] for r in kept])
        print(f"  {k:18s} {lo:9.3f} / {md:9.3f} / {hi:9.3f}")
    W = sum(r["weight"] for r in kept)
    for m, name in ((0, "nearest"), (1, "lowest HP"), (2, "sticky random")):
        print(f"P(target_mode = {name}) = {sum(r['weight'] for r in kept if int(r['target_mode']) == m) / W:.2f}")

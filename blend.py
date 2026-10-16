"""Blend the simulator with the crowd (stacking in log-odds space).

    logit p_blend = w * logit p_model + (1 - w) * logit p_crowd

w is fit on every decided match that has BOTH a pre-match model prediction and a
crowd support rate. With so few matches, w gets a Bayesian treatment: a
Beta(2, 2) prior (mild pull toward 50/50), a grid posterior, and the blended
probability averaged over that posterior. Leave-one-out log loss is reported for
model-only, crowd-only and blend so the blend has to earn its place.

The crowd's probabilities are the support rates, clipped to [3%, 97%].

Usage: python blend.py [round]     # round to predict, e.g. QF-A
"""
import csv, math, sys
from pathlib import Path

ROOT = Path(__file__).parent
GRID = [i / 200 for i in range(201)]


def logit(p):
    p = min(max(p, 0.03), 0.97)
    return math.log(p / (1 - p))


def sig(x):
    return 1 / (1 + math.exp(-x))


def blend(pm, pc, w):
    return sig(w * logit(pm) + (1 - w) * logit(pc))


def loglik(rows, w):
    s = 0.0
    for pm, pc, y in rows:
        p = min(max(blend(pm, pc, w), 1e-6), 1 - 1e-6)
        s += math.log(p if y else 1 - p)
    return s


def posterior(rows):
    lp = [math.log(max(w * (1 - w), 1e-12)) + loglik(rows, w) for w in GRID]  # Beta(2,2) prior
    m = max(lp)
    wts = [math.exp(x - m) for x in lp]
    z = sum(wts)
    return [x / z for x in wts]


def predict(rows, pm, pc):
    post = posterior(rows)
    return sum(pw * blend(pm, pc, w) for pw, w in zip(post, GRID))


def logloss(p, y):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -math.log(p if y else 1 - p)


def load():
    return list(csv.DictReader(open(ROOT / "data" / "matches.csv")))


def training_rows(matches):
    out = []
    for m in matches:
        if m["winner"] in ("L", "R") and m["model_p_left"] and m["left_support_pct"]:
            out.append((float(m["model_p_left"]), float(m["left_support_pct"]) / 100, m["winner"] == "L"))
    return out


if __name__ == "__main__":
    matches = load()
    rows = training_rows(matches)
    post = posterior(rows)
    w_mean = sum(p * w for p, w in zip(post, GRID))
    cdf, lo, hi = 0.0, None, None
    for p, w in zip(post, GRID):
        cdf += p
        if lo is None and cdf >= 0.1:
            lo = w
        if hi is None and cdf >= 0.9:
            hi = w
    print(f"training matches: {len(rows)}")
    print(f"model weight w: mean {w_mean:.2f}, 80% interval [{lo:.2f}, {hi:.2f}]   (0 = crowd only, 1 = model only)")

    loo = {"model": 0.0, "crowd": 0.0, "blend": 0.0}
    for i, (pm, pc, y) in enumerate(rows):
        rest = rows[:i] + rows[i + 1:]
        loo["model"] += logloss(pm, y)
        loo["crowd"] += logloss(min(max(pc, 0.03), 0.97), y)
        loo["blend"] += logloss(predict(rest, pm, pc), y)
    print("leave-one-out mean log loss (lower is better): " +
          ", ".join(f"{k} {v / len(rows):.3f}" for k, v in loo.items()))

    if len(sys.argv) > 1:
        rnd = sys.argv[1]
        for m in matches:
            if m["round"] == rnd and m["model_p_left"] and m["left_support_pct"]:
                pm, pc = float(m["model_p_left"]), float(m["left_support_pct"]) / 100
                p = predict(rows, pm, pc)
                lm, rm = float(m["left_mult"]), float(m["right_mult"])
                evl, evr = p * lm + (1 - p) * 10, (1 - p) * rm + p * 10
                print(f"\n{rnd} M{m['match']}: {m['left_team']} vs {m['right_team']}")
                print(f"  model {pm:.3f}  crowd {pc:.2f}  ->  blend P(left) = {p:.3f}")
                print(f"  EV/emblem: left {evl:.1f} (x{lm:g})   right {evr:.1f} (x{rm:g})")

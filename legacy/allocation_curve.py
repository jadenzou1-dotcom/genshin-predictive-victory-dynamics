"""SUPERSEDED by strategies.py (kept for history). Writes legacy/charts/<round>_allocation.png.

Sweep Strategy A's split between the two per-match favourites and plot
Sharpe, EV and SD against the allocation. Saves charts/<round>_allocation.png.

x = emblems on the Match-1 leg, the rest on the Match-2 leg.
Usage: python allocation_curve.py <round> [emblems]
"""
import csv, math, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FLOOR = 10
ROOT = Path(__file__).resolve().parent.parent
rnd = sys.argv[1]
POOL = int(sys.argv[2]) if len(sys.argv) > 2 else 100

# per match, the higher-Sharpe side (same rule as strategies.py)
legs = []
for m in csv.DictReader(open(ROOT / "data" / "matches.csv")):
    if m["round"] != rnd or not m["model_p_left"]: continue
    pl = float(m["model_p_left"])
    best = None
    for team, p, mult in ((m["left_team"], pl, float(m["left_mult"])),
                          (m["right_team"], 1 - pl, float(m["right_mult"]))):
        mu = p * mult + (1 - p) * FLOOR
        sd = (mult - FLOOR) * math.sqrt(p * (1 - p))
        s = (mu - FLOOR) / sd
        if best is None or s > best["sharpe"]:
            best = dict(team=team, match=m["match"], mu=mu, sd=sd, sharpe=s)
    legs.append(best)
assert len(legs) == 2, "sweep is defined for two matches per round"
a, b = legs

xs, sh, ev, sds = [], [], [], []
for x in range(POOL + 1):
    mu = x * a["mu"] + (POOL - x) * b["mu"]
    sd = math.sqrt((x * a["sd"]) ** 2 + ((POOL - x) * b["sd"]) ** 2)
    xs.append(x); ev.append(mu); sds.append(sd); sh.append((mu - FLOOR * POOL) / sd)
k = max(range(len(xs)), key=lambda i: sh[i])

print(f"x = emblems on {a['team']}; rest on {b['team']}")
print("  x   Sharpe    EV     SD")
for x in sorted({0, 25, 40, 45, 48, 49, 50, 51, 52, 55, 60, 75, 100, xs[k]}):
    print(f"{x:3d}  {sh[x]:6.3f}  {ev[x]:5.0f}  {sds[x]:5.0f}" + ("   <- peak" if x == xs[k] else ""))

INK, MUTED, GRID, LINE, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED})
fig, axs = plt.subplots(3, 1, figsize=(8, 8.5), sharex=True, facecolor=SURF)
for ax, ys, label in zip(axs, (sh, ev, sds), ("Sharpe (excess over 10-pt floor)", "Expected round score", "Std dev of round score")):
    ax.set_facecolor(SURF)
    ax.plot(xs, ys, color=LINE, lw=2)
    ax.scatter([xs[k]], [ys[k]], s=40, color=LINE, edgecolor=SURF, linewidth=2, zorder=3)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.set_ylabel(label)
axs[0].annotate(f"peak {sh[k]:.2f} at {xs[k]}/{POOL - xs[k]}", (xs[k], sh[k]),
                xytext=(-60, -32), textcoords="offset points", color=INK)
axs[0].annotate(f"all on {a['team'].split()[-2]} {a['team'].split()[-1]}: {sh[-1]:.2f}", (xs[-1], sh[-1]),
                xytext=(-150, 8), textcoords="offset points", color=MUTED)
axs[2].set_xlabel(f"Emblems on {a['team']} (M{a['match']})  ·  rest on {b['team']} (M{b['match']})")
fig.suptitle(f"Strategy A allocation sweep — {rnd}", x=0.06, ha="left", color=INK, fontsize=13)
fig.tight_layout()
out = ROOT / "legacy" / "charts" / f"{rnd}_allocation.png"
out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=150, facecolor=SURF)
print(f"\nsaved {out.relative_to(ROOT)}")

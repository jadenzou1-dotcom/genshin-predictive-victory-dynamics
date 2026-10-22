"""Build the README charts from data/matches.csv and data/leaderboard.csv.

Writes a light and a dark PNG of each chart to charts/:
  points_by_round_{light,dark}.png   cumulative prediction score per account
  model_vs_crowd_{light,dark}.png    probability each predictor gave the eventual winner

Usage: python make_charts.py
"""
import csv
import re
from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
OUT = ROOT / "charts"

# Palette: validated categorical slots (blue, orange, violet) plus neutral ink.
THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", grid="#e4e3df",
                  shado="#2a78d6", dino="#eb6834", model="#6250d6", crowd="#7a7975"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", grid="#33322f",
                 shado="#3987e5", dino="#d95926", model="#9085e9", crowd="#8f8e88"),
}


def load(name):
    with open(ROOT / "data" / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


matches = load("matches.csv")
board = load("leaderboard.csv")
best_friend = max(int(r["score"]) for r in board if r["is_ours"] != "yes")

# ---- cumulative points by round ---------------------------------------------
rounds = OrderedDict()
tot = {"Shadow": 0, "Dino": 0}
for m in matches:
    for acct, pts in re.findall(r"(Shadow|Dino) (\d+)", m["score_earned"]):
        tot[acct] += int(pts)
    rounds[m["round"]] = dict(tot)
labels = list(rounds)
shado = [rounds[r]["Shadow"] for r in labels]
dino = [rounds[r]["Dino"] for r in labels]
skipped = {m["round"] for m in matches if m["pick"].startswith("none")}

# ---- model vs crowd on the winner -------------------------------------------
mv = []
for m in matches:
    if m["winner"] not in ("L", "R") or not m["model_p_left"]:
        continue
    p, s = float(m["model_p_left"]), float(m["left_support_pct"]) / 100
    if m["winner"] == "R":
        p, s = 1 - p, 1 - s
    mv.append((f"{m['round']}\nM{m['match']}", p, s))


def style(ax, t):
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["grid"])
    ax.tick_params(colors=t["ink2"], length=0, labelsize=9)
    ax.grid(axis="y", color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def points_chart(mode):
    t = THEMES[mode]
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=160, facecolor=t["surface"])
    style(ax, t)
    x = range(len(labels))
    ax.hlines(best_friend, -0.3, len(labels) - 1, color=t["crowd"], linewidth=1.2, linestyle=(0, (4, 3)))
    ax.annotate(f"Best friend\n{best_friend:,}", (len(labels) - 1, best_friend), xytext=(8, 0),
                textcoords="offset points", va="center", fontsize=9, color=t["ink2"])
    for ys, c, name in ((dino, t["dino"], "Dino · max EV"), (shado, t["shado"], "Shado · risk-adjusted")):
        ax.plot(x, ys, color=c, linewidth=2, marker="o", markersize=5,
                markeredgecolor=t["surface"], markeredgewidth=1.5, zorder=3)
        ax.annotate(f"{name}\n{ys[-1]:,}", (len(labels) - 1, ys[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=9, color=t["ink"])
    for i, r in enumerate(labels):
        if r in skipped:
            ax.text(i, -6500, "no bets", ha="center", fontsize=7.5, color=t["ink2"], style="italic")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 90000)
    ax.set_xlim(-0.3, len(labels) - 1 + 1.9)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1000:.0f}k"))
    ax.set_title("Cumulative prediction score by round", loc="left", color=t["ink"], fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(OUT / f"points_by_round_{mode}.png", facecolor=t["surface"])
    plt.close(fig)


def model_chart(mode):
    t = THEMES[mode]
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=160, facecolor=t["surface"])
    style(ax, t)
    xs = range(len(mv))
    ax.axhline(0.5, color=t["ink2"], linewidth=1, linestyle=(0, (4, 3)))
    ax.text(len(mv) - 0.5, 0.515, "coin flip", ha="right", fontsize=8, color=t["ink2"])
    for i, (_, p, s) in enumerate(mv):
        ax.plot([i, i], [p, s], color=t["grid"], linewidth=2, zorder=1, solid_capstyle="round")
    ax.scatter(xs, [s for _, _, s in mv], s=46, color=t["crowd"], edgecolor=t["surface"],
               linewidth=1.5, zorder=2, label="Crowd (support rate)")
    ax.scatter(xs, [p for _, p, _ in mv], s=52, color=t["model"], edgecolor=t["surface"],
               linewidth=1.5, zorder=3, label="Model (call made before the match)")
    ax.set_xticks(list(xs), [lab for lab, _, _ in mv], fontsize=7.5)
    ax.set_ylim(0, 1.04)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_ylabel("Chance given to the actual winner", color=t["ink2"], fontsize=9)
    leg = ax.legend(loc="lower left", frameon=False, fontsize=8.5, ncol=2, bbox_to_anchor=(0, 1.0))
    for txt in leg.get_texts():
        txt.set_color(t["ink"])
    ax.set_title("Above the dashed line = picked the winner", loc="right", color=t["ink2"], fontsize=8.5, pad=10)
    fig.tight_layout()
    fig.savefig(OUT / f"model_vs_crowd_{mode}.png", facecolor=t["surface"])
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for mode in THEMES:
        points_chart(mode)
        model_chart(mode)
    print("final:", {"Shado": shado[-1], "Dino": dino[-1]}, "| modelled matches:", len(mv),
          "| model right:", sum(p > 0.5 for _, p, _ in mv), "| crowd right:", sum(s > 0.5 for _, _, s in mv))

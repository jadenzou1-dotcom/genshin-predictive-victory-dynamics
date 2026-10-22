"""Build RESULTS.md, a human-readable view of data/matches.csv and data/crowd_log.csv.

The CSVs stay the source of truth. Re-run after editing them:
    python make_results.py
"""
import csv
from pathlib import Path
from collections import OrderedDict

MATCHES = "data/matches.csv"
CROWD = "data/crowd_log.csv"
BOARD = "data/leaderboard.csv"
BACKTEST = "data/backtest_v8.csv"
ROOT = Path(__file__).parent
OUT = "RESULTS.md"


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}".rstrip("0").rstrip(".") + "%"


def mult(x):
    return "—" if not x else f"×{x}"


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


matches = load(MATCHES)
crowd = load(CROWD)
try:
    board = load(BOARD)
except FileNotFoundError:
    board = []

# ---- track record (model vs backtests vs crowd) -----------------------------
SHORT = {
    "The Mysterious Howl Crew": "Howl Crew", "Little Fungi Clan": "Fungi Clan",
    "Frostarm and Shaman Formation": "Frostarm & Shaman", "Saurians Are the Cutest": "Saurians",
    "Elemental Dye Experts": "Dye Experts", "Mirror Fruity Order": "Mirror Fruity",
    "Unofficial Blazing Beasts Members": "Blazing Beasts", "Rude-a-Lot, Hats-a-Not": "Rude-a-Lot",
    "Reserve Grenadier Squad": "Grenadier", "Seahorse and Crab": "Seahorse & Crab",
    "A Little Chubby Crisis": "Chubby Crisis", "Consecrated Beast Frightfest": "Consecrated Beast",
    "What Does the Ninken Say?": "Ninken", "Simple-Soul Hilichurl Fighters": "Hilichurl Fighters",
    "Ultra-Ancient Heavy Assault Formation": "Ultra-Ancient", "Round-and-Frost Assault": "Round-and-Frost",
}
short = lambda t: SHORT.get(t, t)
backtest = {(b["round"], b["match"]): b for b in load(BACKTEST)}
ROUND_LABEL = {("Final", "1"): "3rd&nbsp;place", ("Final", "2"): "Final"}

decided = [m for m in matches if m["winner"] in ("L", "R")]
scored = [m for m in decided if num(m["model_p_left"]) is not None]  # the matches with a live call

# each predictor as P(left) per match; crowd = support rate
PREDICTORS = [
    ("live", "**Live model**", lambda m: num(m["model_p_left"])),
    ("wf", "Walk-forward backtest", lambda m: num(backtest.get((m["round"], m["match"]), {}).get("past_only_p_left"))),
    ("loo", "Leave-one-out CV", lambda m: num(backtest.get((m["round"], m["match"]), {}).get("loo_p_left"))),
    ("crowd", "Crowd", lambda m: None if num(m["left_support_pct"]) is None else num(m["left_support_pct"]) / 100),
]


def score(get):
    right, briers = 0, []
    for m in scored:
        p = get(m)
        y = 1.0 if m["winner"] == "L" else 0.0
        right += (p > 0.5) == (y == 1.0)
        briers.append((p - y) ** 2)
    return right, sum(briers) / len(briers)


def call(p, w):
    if p is None:
        return "—"
    side = "L" if p > 0.5 else "R"
    c = max(p, 1 - p) * 100
    pct = f"{c:.1f}" if c < 55 else f"{c:.0f}"  # keep near-coin-flips distinguishable from 50%
    return f"{side}&nbsp;{pct}%&nbsp;{'✅' if side == w else '❌'}"


S = {k: score(get) for k, _, get in PREDICTORS}
n = len(scored)
crowd_all = sum((num(m["left_support_pct"]) > 50) == (m["winner"] == "L") for m in decided)
DESC = {
    "live": ("The call actually made before the match, by the model version of the day (v1–v8)",
             "**None**: true out-of-sample"),
    "wf": ("Final model (v8), refit using only rounds before the match",
           "Structural only: v8's mechanics were found by watching every replay"),
    "loo": ("Final model (v8), refit on every other match, earlier and later",
            "Parameter + structural: later rounds leak into the fit"),
    "crowd": ("Support rate read as a win probability", "None"),
}

track = [
    f"**Scoreboard: the {n} matches with a live model call**",
    "",
    "| Predictor | How the prediction was made | Look-ahead bias | Correct | Brier ↓ |",
    "|---|---|---|---|---|",
]
for k, label, _ in PREDICTORS:
    r, b = S[k]
    cnt = f"**{r} / {n}**" if k == "live" else f"{r} / {n}"
    track.append(f"| {label} | {DESC[k][0]} | {DESC[k][1]} | {cnt} | {b:.3f} |")
track += [
    "",
    "- **Live is the headline.** It is the only model row with no look-ahead bias. The two backtests "
    "show what the finished model would have called. The gap between live "
    f"({S['live'][0]}/{n}) and walk-forward ({S['wf'][0]}/{n}) is roughly what the mechanics learned during "
    "the event were worth. Two of walk-forward's wins (R16-B) are 50–51% coin flips, so treat 13/14 as about 11–13.",
    "- **Brier score** is the mean squared error of the probability (0 is perfect, 0.25 is always saying 50%). It rewards calibrated confidence, not just the right side.",
    f"- **R16-D** had no model call (the losing teams' unit cards were never captured). The crowd went "
    f"{crowd_all} / {len(decided)} counting it.",
    "",
    "**Every match**",
    "",
    "Each model or crowd cell shows the side it favoured (L/R) and how confident it was. The winner is in bold.",
    "",
    "| Round | Left vs Right | Live model | Walk-forward | Leave-one-out | Crowd | Winner |",
    "|---|---|---|---|---|---|---|",
]
for m in decided:
    w = m["winner"]
    L, R = short(m["left_team"]), short(m["right_team"])
    L, R = (f"**{L}**", R) if w == "L" else (L, f"**{R}**")
    rnd = ROUND_LABEL.get((m["round"], m["match"]), f"{m['round']}&nbsp;M{m['match']}")
    cells = [call(get(m), w) for _, _, get in PREDICTORS]
    track.append(f"| {rnd} | {L} vs {R} | " + " | ".join(cells) + f" | {w} |")
totals = [f"**{S[k][0]}&nbsp;/&nbsp;{n}**" for k, _, _ in PREDICTORS]
track.append(f"| **Correct** | *out of the {n} matches with a model call* | " + " | ".join(totals) + f" | {n}&nbsp;/&nbsp;{n} |")
track.append("")

START, END = "<!-- track-record:start -->", "<!-- track-record:end -->"


def inject(path, heading_level):
    """Replace the generated block between the markers in a hand-written doc."""
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    if START not in s:
        return
    a, b = s.index(START) + len(START), s.index(END)
    body = "\n".join(track).replace("**Scoreboard", "**Scoreboard", 1)
    p.write_text(s[:a] + "\n<!-- generated by make_results.py from data/matches.csv and data/backtest_v8.csv; do not edit by hand -->\n\n"
                 + body + "\n" + s[b:], encoding="utf-8")


lines = [
    "# Results",
    "",
    "Human-readable view of every match. Generated by `python make_results.py` from "
    "[`data/matches.csv`](data/matches.csv), [`data/backtest_v8.csv`](data/backtest_v8.csv) and "
    "[`data/crowd_log.csv`](data/crowd_log.csv); edit the CSVs, not this file.",
    "",
    "## Track record",
    "",
] + track

# ---- final friends leaderboard ---------------------------------------------
if board:
    top = max(int(r["score"]) for r in board)
    lines += [
        "## Final leaderboard (friends, prediction score)",
        "",
        "End-of-event Friend Records board from the game. Charts: [README](README.md). Source: "
        "[`data/leaderboard.csv`](data/leaderboard.csv). Other players are anonymized.",
        "",
        "| Rank | Player | Score | vs. 1st |",
        "|---|---|---|---|",
    ]
    for r in board:
        name = f"**{r['player']}**" if r["is_ours"] == "yes" else r["player"]
        gap = "—" if int(r["score"]) == top else f"−{top - int(r['score']):,}"
        lines.append(f"| {r['rank']} | {name} | {int(r['score']):,} | {gap} |")
    lines.append("")

# ---- per round --------------------------------------------------------------
rounds = OrderedDict()
for m in matches:
    rounds.setdefault(m["round"], []).append(m)

for rnd, ms in rounds.items():
    lines += [f"## {rnd}", ""]
    for m in ms:
        L, R = m["left_team"], m["right_team"]
        p = num(m["model_p_left"])
        s = num(m["left_support_pct"])
        w = m["winner"]
        winner = L if w == "L" else R if w == "R" else None

        def tick(side_left):
            if winner is None or side_left is None:
                return ""
            return " ✅" if side_left == (w == "L") else " ❌"

        model_side = None if p is None else p > 0.5
        crowd_side = None if s is None else s > 50
        model_call = "—" if p is None else f"{L if model_side else R} ({pct(max(p, 1 - p))}){tick(model_side)}"
        crowd_call = "—" if s is None else f"{L if crowd_side else R} ({max(s, 100 - s):.0f}%){tick(crowd_side)}"

        lines += [
            f"### {ROUND_LABEL.get((m['round'], m['match']), 'Match ' + m['match']).replace('&nbsp;', ' ')}: {L} vs {R}",
            "",
            "| | Left | Right |",
            "|---|---|---|",
            f"| Team | {'**' + L + '**' if w == 'L' else L} | {'**' + R + '**' if w == 'R' else R} |",
            f"| Crowd support | {m['left_support_pct'] or '—'}% | {m['right_support_pct'] or '—'}% |",
            f"| Multiplier | {mult(m['left_mult'])} | {mult(m['right_mult'])} |",
            f"| Model win chance | {pct(p)} | {pct(None if p is None else 1 - p)} |",
            "",
            f"- **Winner:** {winner or 'pending'}",
            f"- **Model's call:** {model_call}",
            f"- **Crowd's call:** {crowd_call}",
        ]
        if m["pick"]:
            lines.append(f"- **Picks:** {m['pick']}")
        if m["score_earned"]:
            lines.append(f"- **Score earned:** {m['score_earned']}")
        if num(m["brier_model"]) is not None:
            lines.append(f"- **Brier:** model {num(m['brier_model']):.3f}, crowd {num(m['brier_crowd']):.3f}")
        if m["notes"]:
            lines.append(f"- **Notes:** {m['notes']}")
        lines.append("")

    snaps = [c for c in crowd if c["round"] == rnd]
    if snaps:
        lines += [
            "<details><summary>Crowd snapshots this round</summary>",
            "",
            "| Match | Time (ET) | Locked | Left support | Right support | Left mult | Right mult | Notes |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for c in snaps:
            lines.append(
                f"| {c['match']} | {c['snapshot_time_et']} | {c['locked']} | {c['left_support_pct']}% | "
                f"{c['right_support_pct']}% | {mult(c['left_mult'])} | {mult(c['right_mult'])} | {c['notes']} |"
            )
        lines += ["", "</details>", ""]

for doc in ("README.md", "docs/SUMMARY.md"):
    inject(doc, 2)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines).rstrip() + "\n")
print(f"wrote {OUT}: {len(matches)} matches, {len(decided)} decided")

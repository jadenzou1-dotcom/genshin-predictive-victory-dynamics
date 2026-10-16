# Genshin Impact — Predictive Victory Dynamics Model

A small quantitative model for betting on Genshin Impact's *Predictive Victory Dynamics* event (October 2026). In the event, players place Victory Emblems on one of two simulated armies, and a crowd-driven multiplier pays more for backing the less popular side.

The goal is to beat the crowd's support rate by combining (1) a Monte Carlo battle simulation built from each unit's listed stats and skills with (2) the event's payout math.

## The event in one paragraph

There are 16 simulated battles across 8 rounds (Round of 16 → Final). Each round, you commit up to 100 Victory Emblems per match to one side. The **support rate** (the share of all players' emblems on each side) sets a **score multiplier**: the less popular the side, the higher the multiplier. Support rates lock 4 hours before the round ends. A correct pick scores `emblems × multiplier`. A wrong pick still scores `emblems × 10`. Reward tiers run up to a 16,000 prediction score.

## Workflow (each round)

1. **Capture.** Screenshot each unit's detail card (stats, tags, skill text) and the board layout.
2. **Record.** Add new unit types to `data/units.csv` and each unit's grid position to `data/placements.csv`. Log support rates and multipliers to `data/matches.csv`.
3. **Simulate.** Run `python sim.py <round>`, e.g. `python sim.py R16-A`. This prints P(left wins), how sensitive that is to the biggest unknowns, and the expected value per emblem for each side.
4. **Decide.** Two fixed strategies run in parallel: Run `python strategies.py <round>`. **A (max-Sharpe, main account)** takes the tangency portfolio across each match's favourite, and **B (max-EV, second account)** puts everything on the highest-EV side. It also scores two paper benchmarks (naive-underdog, crowd-favourite) for comparison. Commit shortly before the support-rate lock so the multiplier you see is close to final.
5. **Calibrate.** After the battle, run `python replay_hp_tracker.py <video> data/replays/<round>_hp_bars.csv` to extract both team HP curves, log winner / remaining HP / wipe time to `data/replays/<round>_outcomes.csv`, note unit behaviour in `data/units.csv` and `notes/`, then run `python calibrate.py` to refit the model to every replay so far. Every change is logged in [`PROCESS.md`](PROCESS.md).

## Payout math

With `p` = true win probability of the side you back and `M` = its multiplier:

```
EV per emblem = p·M + (1 − p)·10
```

Fitted from observed (support rate, multiplier) pairs: `M ≈ 20 + 28·(1−s)/s`, apparently capped at 200.

Because the score is linear in emblems and wrong picks still pay, EV maximization puts all emblems on the single best pick. Splitting only buys lower variance.

## Repo layout

| Path | What it is |
|---|---|
| `data/units.csv` | One row per unit type: stats, counter tags, skill flags, skill text, replay findings |
| `data/placements.csv` | One row per unit per match: team, side, grid row and column |
| `data/matches.csv` | One row per match: crowd odds, model probability, pick, result, score. This is the track record |
| `sim.py` | Monte Carlo battle model (elements, reactions, kiting, 45 s clock) plus EV calculation |
| `calibrate.py` | Approximate Bayesian calibration of sim parameters to observed replays |
| `replay_hp_tracker.py` | OpenCV: extracts both team HP bars from a replay video |
| `data/replays/` | HP-bar traces and observed outcomes per round |
| `data/calibration_samples.csv` | Weighted posterior parameter draws used by `sim.py` |
| `strategies.py` | Per-round emblem allocation for Strategies A and B plus paper benchmarks |
| `allocation_curve.py` | Sweeps Strategy A splits and plots Sharpe / EV / SD to `charts/` |
| `notes/` | Per-round analysis and replay observations |
| `PROCESS.md` | How the model was developed, every assumption, and a dated change log |
| `SKILLS.md` | Skills used and developed to build this project |

## Results so far

| Round | Match | Crowd (left) | Model (left, pre-match) | Pick | Winner |
|---|---|---|---|---|---|
| R16-A | Howl Crew vs Fungi Clan | 25% | 8.5% | A: Fungi | **Fungi** ✓ |
| R16-A | Frostarm vs Saurians | 87% | 88.1% | A: Frostarm, B: Saurians | **Saurians** (B ✓) |
| R16-B | Elemental Dye vs Mirror Fruity | 21% | 78.5% | A: 28 Dye, B: 100 Dye | **Mirror Fruity** ✗ |
| R16-B | Blazing Beasts vs Rude-a-Lot | 78% | 60.5% | A: 72 Blazing Beasts | **Blazing Beasts** (A ✓) |

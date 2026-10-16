# Genshin Impact — Predictive Victory Dynamics Model

A small quantitative model for betting on Genshin Impact's *Predictive Victory Dynamics* event (October 2026). In the event, players place Victory Emblems on one of two simulated armies, and a crowd-driven multiplier pays more for backing the less popular side.

The goal is to beat the crowd's support rate by combining (1) a Monte Carlo battle simulation built from each unit's listed stats and skills with (2) the event's payout math.

## The event in one paragraph

There are 16 simulated battles across 8 rounds (Round of 16 → Final). Each round, you commit up to 100 Victory Emblems per match to one side. The **support rate** (the share of all players' emblems on each side) sets a **score multiplier**: the less popular the side, the higher the multiplier. Support rates lock 4 hours before the round ends. A correct pick scores `emblems × multiplier`. A wrong pick still scores `emblems × 10`. Reward tiers run up to a 16,000 prediction score.

## Workflow (each round)

1. **Capture.** Screenshot each unit's detail card (stats, tags, skill text) and the board layout.
2. **Record.** Add new unit types to `data/units.csv` and each unit's grid position to `data/placements.csv`. Log support rates and multipliers to `data/matches.csv`.
3. **Simulate.** Run `python sim.py <round>`, e.g. `python sim.py R16-A`. This prints P(left wins), how sensitive that is to the biggest unknowns, and the expected value per emblem for each side.
4. **Decide.** Run `python strategies.py <round>`. Two strategies run in parallel, one per account: **A (risk-adjusted, main account)** and **B (max-EV, second account)**. A was max-Sharpe for R16-A and R16-B and switches to max certainty equivalent (CE) from here on; see [Strategy decisions](#strategy-decisions). It also scores two paper benchmarks (naive-underdog, crowd-favourite). Commit shortly before the support-rate lock so the multiplier you see is close to final.
   - **Log the crowd.** Before the round closes, add a row per match to `data/crowd_log.csv` with the support rates and multipliers on screen. The game stops showing them once the round ends.
5. **Calibrate.** After the battle, run `python replay_hp_tracker.py <video> data/replays/<round>_hp_bars.csv` to extract both team HP curves, log winner / remaining HP / wipe time to `data/replays/<round>_outcomes.csv`, note unit behaviour in `data/units.csv` and `notes/`, then run `python calibrate.py` to refit the model to every replay so far, and `python make_results.py` to refresh [RESULTS.md](RESULTS.md). Every change is logged in [`PROCESS.md`](PROCESS.md).

## Payout math

With `p` = true win probability of the side you back and `M` = its multiplier:

```
EV per emblem = p·M + (1 − p)·10
```

The multiplier is a **step function of support rate**, not a smooth curve (the earlier fit `M ≈ 20 + 28·(1−s)/s` is retired). Observed tiers so far:

| Support rate seen | Multiplier |
|---|---|
| 13% | ×200 (cap?) |
| 17–25% | ×105 |
| 34–39% | ×70 |
| 61–66% | ×35 |
| 75–83% | ×30 |
| 87% | ×25 |

Tier edges between these points are unknown. Inside a tier the payout is flat, so a 17% underdog pays the same as a 25% one.

Because the score is linear in emblems and wrong picks still pay, EV maximization puts all emblems on the single best pick. Splitting only buys lower variance.

## Strategy decisions

### 1. Sharpe ratio was the wrong objective, and I only caught it by intuition

Strategy A started as **max-Sharpe**, the standard risk-adjusted yardstick in quant finance. I didn't question it in R16-A, because there it gave a sensible answer: split across the two favourites (51 Fungi / 49 Frostarm).

In R16-B (the second round) it produced an allocation that felt wrong. It put **28** emblems on Elemental Dye (model 78.5% to win, ×105) and **72** on Blazing Beasts (60.5%, ×30), even though Elemental Dye was better on *both* win probability *and* payout. Sharpe scored the split higher, but it was plainly a worse decision.

To find out why, I reduced it to two coins:

| Coin | Lose | Win | EV | Sharpe |
|---|---|---|---|---|
| 2 | 40% → 10 | 60% → 50 | 34.0 | 1.22 |
| 2′ (win payout cut to 20) | 40% → 10 | 60% → 20 | 16.0 | **2.04** |

Making the bet strictly worse (same odds, smaller payout, half the EV) *raised* its Sharpe. With a fixed 10-point floor, Sharpe on a binary bet reduces to `sqrt(p/(1−p))`: the payout cancels out entirely, so Sharpe only rewards how *reliably* a bet wins, never how *much*.

Sharpe isn't wrong in general. It's the right yardstick when you can lever a portfolio up or down to your risk target. Here stakes are capped at 100 emblems, there's no leverage, payoffs are lumpy and skewed, and the downside is bounded by the floor. Under those conditions max-Sharpe just picks the smallest swings and leaves EV on the table. Full write-up: [PROCESS.md, 2026-10-13 "where the Sharpe ratio falls short"](PROCESS.md).

(Honest footnote: in R16-B the Sharpe split happened to score better, 2,440 vs 1,000 for all-in on Dye, because Dye lost. One outcome doesn't make it the right rule.)

### 2. Switching Strategy A to certainty equivalent (CE)

From here on, Strategy A maximizes

```
CE = EV − (λ/2) · Var
```

over the emblem split. EV counts in full, so a bigger payout always makes a bet better, and risk is a separate penalty set by one dial, λ (risk aversion). λ = 0 is pure EV (Strategy B), and larger λ trades EV for steadiness. This is the textbook mean-variance utility Sharpe itself comes from: with leverage, max-CE means "hold the max-Sharpe portfolio, scaled by 1/λ". Without leverage that scaling step isn't available, so CE is optimized directly. λ is fixed once for the rest of the event so the A-vs-B comparison stays clean. R16-A and R16-B stay logged as max-Sharpe rounds.

### 3. Saving emblems for later rounds, when the model knows more

The model gets more accurate as more battle replays come in:
- Calibration is cumulative: every replay refits the shared mechanics (time scale, counter strength, AoE radius, overtime).
- A unit's fitted strength only gets weight `n/(n+2)` after `n` replays, so units seen several times are predicted much better than new ones.
- Predictions for lineups of unseen units are pulled toward 50% (tempering), which shrinks the edge on early rounds by design.

Group C was entirely unseen units, so the model's edge there was thin (one lean, one coin flip). The quarterfinals are fought by R16 winners whose units will already have been watched in replays. So the plan is to **skip Groups C and D and save emblems for the quarterfinals**, where an emblem should be worth more.

This only works if unused emblems carry over (the counter reads 100/300, which is ambiguous). So it's being tested first: Account A skips Group C, Account B bets it as a control. If A shows 200/300 when Group D opens, rollover is real. Two other caveats: the slider caps at 100 per match, so 300 banked emblems need 3 matches to spend; and every skipped round forgoes at least the 10-per-emblem floor.

## Repo layout

| Path | What it is |
|---|---|
| `data/units.csv` | One row per unit type: stats, counter tags, skill flags, skill text, replay findings |
| `data/placements.csv` | One row per unit per match: team, side, grid row and column |
| `data/matches.csv` | One row per match: crowd odds, model probability, pick, result, score. This is the track record |
| `data/crowd_log.csv` | Timestamped snapshots of each side's support rate and multiplier. The game hides these after the round ends |
| `sim.py` | Monte Carlo battle model (elements, reactions, kiting, 45 s clock) plus EV calculation |
| `calibrate.py` | Approximate Bayesian calibration of sim parameters to observed replays (3-number summary per replay; superseded by `calibrate_traj.py`) |
| `calibrate_traj.py` | Kernel ABC calibration against full fight trajectories: both team HP curves and the share of bodies alive, second by second |
| `replay/` | Replay extraction framework. `extract.py` reads a recording at 10 frames/s: team HP bars, every overhead unit HP bar (`bars.py`), the clock (OCR) and commentary lines (OCR). `observe.py` turns that into per-second battle-time curves |
| `data/replays/extracted/` | Extractor output per round: `*_frames.csv`, `*_bars.csv`, `*_events.csv` (commentary log), `*_curves.csv` |
| `blend.py` | Stacks the sim with the crowd's support rate in log-odds space (Bayesian weight, leave-one-out check) |
| `replay_hp_tracker.py` | OpenCV: extracts both team HP bars from a replay video (older, team bars only) |
| `data/replays/` | HP-bar traces and observed outcomes per round |
| `data/calibration_samples.csv` | Weighted posterior parameter draws used by `sim.py` |
| `strategies.py` | Per-round emblem allocation for Strategies A and B plus paper benchmarks (A still implements max-Sharpe; CE switch pending) |
| `allocation_curve.py` | Sweeps Strategy A splits and plots Sharpe / EV / SD to `charts/` |
| `notes/` | Per-round analysis and replay observations |
| `RESULTS.md` | Readable results page generated from the CSVs by `make_results.py` (don't edit by hand) |
| `PROCESS.md` | How the model was developed, every assumption, and a dated change log |
| `SKILLS.md` | Skills used and developed to build this project |

## Results so far

See **[RESULTS.md](RESULTS.md)**: every match with crowd support, multipliers, the model's call, the winner and Brier scores, plus the crowd snapshots for each round. It's generated from the CSVs by `python make_results.py`.

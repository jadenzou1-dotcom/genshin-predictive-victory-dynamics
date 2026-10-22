# Skills

What it took to build this project, grouped by area. Items marked *(planned)* aren't done yet; everything else is implemented in this repo.

## Probability and decision theory
- **Expected-value analysis** of a binary bet with a payout floor: `EV = p·M + (1−p)·10`, plus breakeven win probabilities for every option.
- **Risk-adjusted decision making:** Sharpe ratio, mean-variance utility, and the tangency (max-Sharpe) portfolio for independent bets, with weights `∝ excess EV / variance`.
- **Finding a use-case gap in the Sharpe ratio:** showed with a worked counterexample that cutting a bet's payout (a strictly worse bet) *raises* its Sharpe when stakes can't be levered, and switched to mean-variance certainty equivalent (`EV − λ/2·Var`). See `PROCESS_LOG.md`.
- **Recognizing when a metric doesn't apply:** showed that with a fixed payout floor Sharpe reduces to `sqrt(p/(1−p))` and ignores payout, and that without leverage, max-Sharpe isn't max-return. Documented in `PROCESS_LOG.md`.
- **Portfolio construction:** diversification across similar-risk independent bets (Sharpe 3.28 → 4.26), and why adding a high-variance bet lowers it.
- **Objective selection:** separating risk-neutral (leaderboard) and risk-averse goals, and running both as a controlled comparison across two accounts.

## Market reasoning
- Treating the crowd's support rate as an **implied probability**, and the payout multiplier as **parimutuel-style odds**.
- **Reverse-engineering the pricing function** from observed points: `M ≈ 20 + 28·(1−s)/s`, capped at 200.
- Finding the edge in **payout asymmetry** rather than in disagreeing with the crowd's favourite.
- **Timing:** committing near the support-rate lock so the observed odds match the final odds.

## Simulation and modeling
- **Monte Carlo, agent-based battle simulation:** grid positions, nearest-target AI, melee movement, kiting, AoE splash, targeting restrictions, crowd control, healing, and elemental auras and reactions (Freeze, Vaporize/Melt, Electro-Charged, Superconduct, Swirl).
- **Uncertainty quantification:** unobservable mechanics (attack speed, counter strength, skill multipliers, squad-HP basis, freeze duration) are sampled from priors, so output probabilities reflect model uncertainty.
- **Sensitivity analysis:** checking that conclusions hold across assumption ranges.
- **Model criticism:** rejected a deterministic v1 as overconfident, and diagnosed v2's miss on Match 2 (no reactions, no kiting, wrong time model).
- **Approximate Bayesian computation (ABC):** nested rejection sampling that fits global and per-unit parameters to observed replay outcomes (winner, remaining HP, wipe time), producing a weighted posterior that the simulator samples from.
- **Forecast evaluation:** Brier scores for model vs crowd, logged per match.
- **Retrodiction vs prediction:** keeping posterior fits separate from honest out-of-sample tests.

## Computer vision and signal extraction
- **OpenCV video analysis:** pixel-color segmentation of both team HP bars, sampled 5×/s from 60 fps replays (`legacy/replay_hp_tracker.py`, later `replay/extract.py`), producing HP-vs-time traces.
- Using those traces to measure battle length, wipe times, damage phases and the absence of HP drain, and turning them into calibration targets.
- **ffmpeg** frame extraction and contact sheets for qualitative behaviour analysis (targeting, kiting, reactions).

## Data engineering
- **Schema design** for a growing dataset: unit-type, placement, match, replay-outcome and posterior-sample tables in CSV, with versioning (`as_of_round`) and a track-record table for evaluation.
- **Structured data capture** from unstructured sources (game screenshots and video → normalized rows).

## Software and tooling
- **Python** (stdlib, OpenCV, matplotlib) for the simulator, calibrator, strategy engine, video tracker and charts.
- **Reproducibility:** seeded runs, a scripted per-round workflow (`sim.py` → `strategies.py` → replay extraction → `calibrate_traj.py` → `make_results.py`), and a dated change log.

## Research practice
- **Writing down assumptions before results**, and logging corrections as dated entries instead of overwriting them.
- **Benchmarking:** scoring strategies against paper baselines (naive-underdog, crowd-favourite) to measure how much the model actually adds.
- **Final event write-up** comparing Strategy A, Strategy B and both benchmarks *(planned)*.

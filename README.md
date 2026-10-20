# Genshin Impact — Predictive Victory Dynamics Model

> New session? Start with [HANDOFF.md](HANDOFF.md) for the current state and the per-round workflow.

A small quantitative model for betting on Genshin Impact's *Predictive Victory Dynamics* event (October 2026). In the event, players place Victory Emblems on one of two simulated armies, and a crowd-driven multiplier pays more for backing the less popular side.

The goal is to beat the crowd's support rate by combining (1) a Monte Carlo battle simulation built from each unit's listed stats and skills with (2) the event's payout math.

## The event in one paragraph

There are 16 simulated battles across 8 rounds (Round of 16 → Final). Each round, you commit Victory Emblems to one side of each match (up to 300 per match; 100 new emblems per day, cap 300). The **support rate** (the share of all players' emblems on each side) sets a **score multiplier**: the less popular the side, the higher the multiplier. Support rates lock 4 hours before the round ends. A correct pick scores `emblems × multiplier`. A wrong pick still scores `emblems × 10`. Reward tiers run up to a 16,000 prediction score.

## Documentation

| Doc | What it covers |
|---|---|
| [docs/SUMMARY.md](docs/SUMMARY.md) | **Start here.** Overall results, the 14-match track record (model vs crowd), what worked and what didn't, points |
| [docs/VERSION_HISTORY.md](docs/VERSION_HISTORY.md) | Model v1 → v8: what each version changed, why, and how well it fit |
| [docs/MECHANICS.md](docs/MECHANICS.md) | Game rules and battle mechanics measured from replays and screens, plus the payout table |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Every major decision and its reasoning: objective (Sharpe → CE), λ, trust weights, panel, pacing, betting against the crowd |
| [docs/PROCESS_LOG.md](docs/PROCESS_LOG.md) | Full dated log of everything done, in order |
| [docs/rounds/](docs/rounds/) | Early per-round analysis notes (R16-A to R16-C) |
| [docs/SKILLS.md](docs/SKILLS.md) | Skills used and developed |
| [RESULTS.md](RESULTS.md) | Generated match-by-match results page (`python make_results.py`) |
| [HANDOFF.md](HANDOFF.md) | Current state and next steps, for picking up in a new session |

## Workflow (each round)

1. **Capture.** Screenshot each unit's detail card (stats, tags, skill text) and the board layout.
2. **Record.** Add new unit types to `data/units.csv` and each unit's grid position to `data/placements.csv`. Log support rates and multipliers to `data/matches.csv`.
3. **Simulate.** Run `python sim.py <round>`, e.g. `python sim.py R16-A`. This prints P(left wins), how sensitive that is to the biggest unknowns, and the expected value per emblem for each side.
4. **Decide.** Run `python strategies.py <round> --pool <emblems> --lambda 2.1e-4 --linw <w1>,<w2>`. Two strategies run in parallel, one per account: **A (risk-adjusted, main account)** and **B (max-EV, second account)**. A was max-Sharpe for R16-A and R16-B and switches to max certainty equivalent (CE) from here on; see [docs/DECISIONS.md](docs/DECISIONS.md). It also scores two paper benchmarks (naive-underdog, crowd-favourite). Commit shortly before the support-rate lock so the multiplier you see is close to final.
   - **Log the crowd.** Before the round closes, add a row per match to `data/crowd_log.csv` with the support rates and multipliers on screen. The game stops showing them once the round ends.
5. **Calibrate.** After the battle, run `python -m replay.extract <video> <round> data/replays/extracted` (team + unit HP bars, clock, commentary), `python -m replay.observe <round>` (battle-time curves) and `python -m replay.dmg <video> <round>` (damage numbers; `python -m replay.attribute <round>` maps them to attackers). Log winner / remaining HP / wipe time to `data/replays/<round>_outcomes.csv`, note unit behaviour in `data/units.csv` and `docs/rounds/`, then run `python calibrate_traj.py 3000 2` to refit the model to every replay so far, and `python make_results.py` to refresh [RESULTS.md](RESULTS.md). Every change is logged in [`docs/PROCESS_LOG.md`](docs/PROCESS_LOG.md).

## Repo layout

```
├── README.md, RESULTS.md, HANDOFF.md
├── docs/                      write-ups (see Documentation above)
├── sim.py                     Monte Carlo battle simulator (core model)
├── calibrate_traj.py          fits the sim to replay trajectories (kernel ABC) -> data/calibration_samples.csv
├── loo.py                     honest backtests: leave-one-out and past-only
├── strategies.py              emblem allocation: Strategy A (CE) and B (EV), benchmarks, break-evens
├── blend.py                   model/crowd blending (log-odds; trust-weight checks)
├── margin_check.py            where an actual result falls in the model's own outcome distribution
├── make_results.py            builds RESULTS.md from the CSVs
├── replay/                    replay video readers
│   ├── extract.py             team/unit HP bars, clock and commentary (OCR) per frame
│   ├── observe.py             per-second battle curves from the extracted frames
│   ├── bars.py                overhead HP-bar detector
│   ├── dmg.py                 damage-number reader (OCR)
│   └── attribute.py           maps damage values to attacking unit types
├── calibrate.py, replay_hp_tracker.py, allocation_curve.py    early tools, superseded (kept for history)
├── charts/                    early allocation charts
└── data/
    ├── units.csv              every unit type: stats, tags, element, special mechanics flags, replay notes
    ├── placements.csv         every unit's grid position per match
    ├── matches.csv            every match: crowd, multipliers, model P, picks, winner, points, Brier (the track record)
    ├── crowd_log.csv          timestamped support-rate / multiplier snapshots
    ├── unit_hits_measured.csv per-hit damage read from replays
    ├── calibration_samples.csv current posterior draws used by sim.py
    ├── backtest.csv, backtest_v8_loo.txt   backtest outputs (v5, v8)
    └── replays/               <round>_outcomes.csv (winner, HP left, wipe time) and extracted/ per-frame data
```

## Results so far

See **[RESULTS.md](RESULTS.md)**: every match with crowd support, multipliers, the model's call, the winner and Brier scores, plus the crowd snapshots for each round. It's generated from the CSVs by `python make_results.py`.

# Handoff: start here (state as of 2026-10-18)

New session: read this file first, then README.md (method, tier table, strategy decisions) and the last sections of PROCESS.md (dated log).

## Who / what
- Owner: Jaden. Two game accounts:
  - **Shado** (also spelled Shadow): Strategy A, max CE = EV − (λ/2)·Var, **λ = 2.1e-4 (fixed)**. Goal is "maximize score, minimize risk". It is NOT aiming for the 16k tier, so do not use 16k-threshold arguments to set λ.
  - **Dino:** Strategy B, max EV.
- Verified points before QF-B: Shado 12,685, Dino 31,500.

## Game rules (confirmed by Jaden; earlier docs may say otherwise)
- Up to **300 emblems per match** (slider max). 100 emblems granted per day, held cap 300.
- Wrong pick pays 10 per emblem. Right pick pays emblems × multiplier.
- The multiplier is a step function of crowd support. Support locks 4 h before the round ends (~18:00 ET); the round ends ~22:00 ET.
- Emblems can be split across a round's matches in any way (e.g. 150/50).
- The **Final has 2 matches**: a 1st-place match and a 3rd-place match.
- **Pacing plan:** 100 at QF-B (done), **200 per account at the Semifinals, 200 per account at the Final**.

## Model pipeline (v5)
- `sim.py`: Monte Carlo battle sim.
- `calibrate_traj.py`: kernel ABC on per-second replay trajectories. Run `python3 calibrate_traj.py 3000 2`.
- `loo.py`: leave-one-out and past-only backtests.
- `blend.py`: log-odds stacking with crowd support.
- `strategies.py`: allocation search. It runs a coarse 5-emblem search, then refines in 1-emblem steps.
  - Example: `python3 strategies.py QF-B --pool 100 --lambda 2.1e-4 --linw 0.59,0.33`
  - `--linw` gives a per-match linear-pool trust weight.
- Trust standard for P = w·model + (1−w)·crowd:
  - **~60% model** when all units have been seen in replays.
  - **~35% model** when key units are unseen. "Unseen" mostly means the units the current teams beat.
  - A 5-agent panel sets per-match weights.
- Replays are fit so far: R16-A, R16-B, R16-C and QF-A (2 matches each), 8 in total.
  - R16-D is extracted but not used, because the losers' unit cards are unknown (`data/replays/R16-D_outcomes.pending.csv`).

## Processing a new round
1. **Log the result.** Fill in winner and score_earned for the round in `data/matches.csv`, then run `python3 make_results.py`, which rebuilds RESULTS.md.
2. **Replay video.** Jaden records it on his Windows PC, in the "Genshin PVD Replays" folder under Videos\Captures. He attaches it or it is staged through the device bridge. Then run:
   - `python -m replay.extract <video> <round> data/replays/extracted`
   - `python -m replay.observe <round>`
   - optionally `python -m replay.dmg <video> <round>` and `python -m replay.attribute <rounds>`
3. **Outcomes.** Write `data/replays/<round>_outcomes.csv` with winner, winner HP and wipe time per match.
4. **Refit** with `python3 calibrate_traj.py 3000 2`. Choose EPS so that ESS ≥ 40.
5. **Next round:**
   - Enter any new units in `data/units.csv` and the placements in `data/placements.csv`. Jaden sends unit-card screenshots.
   - Enter the matchups and crowd support/multipliers in `data/matches.csv`. Take a snapshot before the lock, then update at the lock.
   - Run the sim for each match.
   - Get panel trust weights.
   - Run `strategies.py` for Shado (CE) and Dino (EV).

## Where things stand
- **QF-B bets (Oct 17):**
  - Shado: 52 on A Little Chubby Crisis (M1, ×105) and 48 on Round-and-Frost Assault (M2, ×105).
  - Dino: 100 on Chubby.
  - Model P(left): M1 Grenadier 0.607, M2 Ninken 0.564. Crowd 77/23 on both.
- **Next steps:**
  1. Log the QF-B results.
  2. Process the QF-B replay.
  3. Refit.
  4. Predict the Semifinals with 200 per account and a 300-per-match cap.
- **Scoreboard** (8 modelled matches, before QF-B):

  | Predictor | Correct | Brier |
  |---|---|---|
  | Model at the time | 6/8 | 0.254 |
  | Crowd | 4/8 | 0.334 |

## Working rules
- Commit locally after each step. Push only when Jaden says to.
- Jaden prefers short, direct answers. Show model P, crowd P and pooled P, plus EV per option and each account's split.
- Use the event's multiplier tiers from README; if in doubt, ask for a screenshot of the locked multipliers.

# Handoff: start here (state as of 2026-10-18 late)

New session: read this file first, then README.md (method, tier table, strategy decisions) and the last sections of PROCESS.md (dated log).

## Who / what
- Owner: Jaden. Two game accounts:
  - **Shado** (also spelled Shadow): Strategy A, max CE = EV − (λ/2)·Var, **λ = 2.1e-4 (fixed)**. Goal is "maximize score, minimize risk". It is NOT aiming for the 16k tier, so do not use 16k-threshold arguments to set λ.
  - **Dino:** Strategy B, max EV.
- Points after QF-B (both bets lost, 100 × 10 each): Shado ~13,685, Dino ~32,500.

## Game rules (confirmed by Jaden; earlier docs may say otherwise)
- Up to **300 emblems per match** (slider max). 100 emblems granted per day, held cap 300.
- Wrong pick pays 10 per emblem. Right pick pays emblems × multiplier.
- The multiplier is a step function of crowd support. Support locks 4 h before the round ends (~18:00 ET); the round ends ~22:00 ET.
- Emblems can be split across a round's matches in any way (e.g. 150/50).
- The **Final has 2 matches**: a 1st-place match and a 3rd-place match.
- **Pacing plan:** 100 at QF-B (done), **200 per account at the Semifinals, 200 per account at the Final**.

## Model pipeline (v7)
- `sim.py`: Monte Carlo battle sim. v6/v7 changes (2026-10-18):
  - `per_member` fixed to 1 (damage-number totals vs HP-bar loss in R16-B/R16-C).
  - Overtime = one-off hit of `ot_pct` (~11%) max HP to every unit 1.5 s after 00:00, repeating every `ot_period` s. The old continuous drain is gone.
  - `target_mode` fitted: lowest current HP 0.61, nearest 0.26, sticky random 0.13.
  - Ninken post-kill plunge (`kill_plunge` column), ~1× a normal hit, AoE.
  - Slimes carry a permanent own-element aura (`self_aura` column).
  - Unit damage priors centred on measured per-hit damage (`data/unit_hits_measured.csv`).
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
- Replays fit so far: R16-A, R16-B, R16-C, QF-A, QF-B (2 matches each), 10 in total. v7 refit: EPS 0.12, ESS 106.
  - R16-D is extracted but not used, because the losers' unit cards are unknown (`data/replays/R16-D_outcomes.pending.csv`).

## Processing a new round
1. **Log the result.** Fill in winner and score_earned for the round in `data/matches.csv`, then run `python3 make_results.py`, which rebuilds RESULTS.md.
2. **Replay video.** Jaden records it on his Windows PC, in the "Genshin PVD Replays" folder under Videos\Captures. He attaches it or it is staged through the device bridge. Then run:
   - `python -m replay.extract <video> <round> data/replays/extracted`
   - `python -m replay.observe <round>`
   - `python -m replay.dmg <video> <round> data/replays/extracted` (slow, ~20+ min) and `python -m replay.attribute <rounds>`. Use the damage numbers: they settled per_member and the plunge size.
3. **Outcomes.** Write `data/replays/<round>_outcomes.csv` with winner, winner HP and wipe time per match.
4. **Refit** with `python3 calibrate_traj.py 3000 2`. Choose EPS so that ESS ≥ 40.
5. **Next round:**
   - Enter any new units in `data/units.csv` and the placements in `data/placements.csv`. Jaden sends unit-card screenshots.
   - Enter the matchups and crowd support/multipliers in `data/matches.csv`. Take a snapshot before the lock, then update at the lock.
   - Run the sim for each match.
   - Get panel trust weights.
   - Run `strategies.py` for Shado (CE) and Dino (EV).

## Where things stand
- **QF-B (Oct 17):** both favourites won (Grenadier, Ninken); our underdog bets lost, 1,000 points per account. Model called both.
- **Semifinal bets (Oct 18, placed on v6):**
  - Shado: 115 on Mirror Fruity Order (M1, ×40), 85 on Reserve Grenadier Squad (M2, ×50).
  - Dino: 200 on Reserve Grenadier Squad.
  - Crowd locked 58/42 (×40/×50) and 47/53 (×50/×40).
  - v6 model: Fruity 0.91, Grenadier 0.80. Panel trust 0.61 / 0.56 → pooled 0.78 / 0.65.
  - v7 re-run (after bets): Fruity 0.88, Grenadier 0.73.
- **Panel trust standard:** ~0.6 when all units are seen; the 10-call log-loss optimum is 0.6–0.7.
- **Next steps:**
  1. Log the SF results (`data/matches.csv` → `make_results.py`).
  2. Process the SF replay (extract, observe, dmg); write outcomes.
  3. Refit v7. If an overtime game shows a second pulse, that pins `ot_period`.
  4. Final: 2 matches (1st place and 3rd place), 200 per account, cap 300 per match.
- **Open questions:** `ot_period` (only one pulse seen); target_mode is not yet decisive (0.61); Sappho's misses against airborne units are not modelled.
- **Scoreboard** (10 modelled matches, before SF): model 8/10, Brier 0.238; crowd 6/10, Brier 0.278.

## Working rules
- Commit locally after each step. Push only when Jaden says to.
- Jaden prefers short, direct answers. Show model P, crowd P and pooled P, plus EV per option and each account's split.
- Use the event's multiplier tiers from README; if in doubt, ask for a screenshot of the locked multipliers.

# Handoff: start here (state as of 2026-10-19 morning)

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
- **Semifinal results (Oct 18):**
  - M1: Saurians beat Fruity. v6 had Fruity at 0.91; Sappho won with ~11% HP left.
  - M2: Grenadier beat Ninken in overtime.
  - Points: Shado +5,400 (~19.1k total); Dino +10,000 (~42.5k total).
  - Scoreboard (12 modelled matches): model 9/12, Brier 0.270; crowd 6/12, 0.283.
- **Model v7 refit on 12 replays:** EPS 0.15, ESS 138. Overtime is a pulse of ~11% max HP every ~8.6 s. target_mode: lowest HP 0.61.
- **Final (round ends ~22:00 ET Oct 19; support locks ~18:00 ET):**
  - 3rd place: Fruity (L, crowd 14%, est. ×200) vs Ninken (R, 86%, est. ×25). Model P(Fruity) 0.925; units from prior 0.91.
  - Championship: Saurians (L, 29%, est. ×70) vs Grenadier (R, 71%, est. ×35). Model P(Saurians) 0.859; units from prior 0.66.
  - v8 (frost field) model: Fruity 0.919, Saurians 0.882. Trust w = 0.65 (backtest optimum 1.0, discounted for leakage; panel said 0.50) → pooled 0.65 / 0.68.
  - **Provisional bets (200 per account):** Shado ~60 Fruity + ~140 Saurians; Dino 200 Fruity.
- **Done before the lock (Oct 19):** v8 Sappho frost field + refit (ESS 188); v8 leave-one-out backtest (past-only 11/12, Brier 0.122). Still needed from Jaden: Final board screenshots.
- **To do at lock:**
  1. Get screenshots of both Final boards. Placements in `data/placements.csv` (round `Final`) are the SF layouts mirrored and unconfirmed. Fix them, then re-run `python3 sim.py Final 4000`.
  2. Read the real multipliers into `data/matches.csv` and re-run `strategies.py Final --pool 200 --lambda 2.1e-4 --linw 0.65,0.65`.
  3. If Saurians' multiplier ends up close to Grenadier's, the Championship break-even nears 0.5: re-check that pick. Fruity holds even at ×105.
- **After the Final:** log the results, process the replay, and write the summary (README results + what worked / didn't).
- **Open:** account names (Shadow/Dino) are in the pushed repo, which conflicts with the earlier "no real account names" rule. Jaden hasn't decided between keeping them, renaming them going forward, or scrubbing the history.

## Working rules
- Commit locally after each step. Push only when Jaden says to.
- Jaden prefers short, direct answers. Show model P, crowd P and pooled P, plus EV per option and each account's split.
- Use the event's multiplier tiers from README; if in doubt, ask for a screenshot of the locked multipliers.

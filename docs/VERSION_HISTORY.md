# Model version history

What each version of the battle model changed, why, and what it predicted. Dated detail: [PROCESS_LOG.md](PROCESS_LOG.md). Measured game rules: [MECHANICS.md](MECHANICS.md).

**How fit quality is measured:** calibration is kernel ABC on per-second replay trajectories (`calibrate_traj.py`). A smaller tolerance (EPS) at the same effective sample size (ESS) means the model reproduces the replays more closely. Fit numbers are only comparable at the same replay count.

| Version | Date | Key change | Replays fit | Fit | Used for |
|---|---|---|---|---|---|
| v1 | Oct 12 | Deterministic stat-pool battle | 0 | — | Rejected (0% / 99.9%) |
| v2 | Oct 12 | Monte Carlo over unknown mechanics | 0 | — | R16-A |
| v3 | Oct 13–16 | Elements and reactions, kiting, 45 s clock, replay calibration, measured hit size | 2–6 | EPS 0.10, ESS 70 | R16-B, R16-C |
| v4 | Oct 16 | Hit = 0.45 × ATK (DEF × RES); Sappho splash; counters ≈ 1×; long freezes | 6 | EPS 0.10, ESS 42 | — |
| v5 | Oct 16–18 | Panel round 1 fixes | 6 → 10 | ESS 68 (6); EPS 0.15, ESS 124 (10) | QF-A, QF-B |
| v6 | Oct 18 | Squad HP fixed from data; Ninken plunge; slime self-aura; measured hit priors | 10 | EPS 0.12, ESS 72 | **SF bets** |
| v7 | Oct 18 | Overtime = one-off pulse; targeting fitted; plunge = 1× | 10 → 12 | EPS 0.12, ESS 106 (10); EPS 0.15, ESS 138 (12) | Final (first pass) |
| v8 | Oct 19 | Sappho frost field | 12 | **EPS 0.15, ESS 188** | **Final bets** |

## v1: deterministic sim (rejected)

Listed ATK was treated as damage per hit, and the bigger stat pool always won (0% / 99.9%). Listed ATK isn't DPS: skill multipliers and attack speed are hidden.

## v2: Monte Carlo over the unknowns

Each run samples the unknowns:
- counter strength;
- squad HP rule (per member vs split);
- damage multiplier and attack interval per unit;
- splash;
- crowd control;
- healing.

Lesson from R16-A: counter tags are a tie-breaker; raw HP × ATK dominates.

## v3: after the first replays

- **R16-A replay findings:**
  - a fixed 45 s clock with no drain inside it;
  - Sappho freezes enemies by herself (Hydro + Cryo);
  - ranged bosses kite melee.
- **Added:** elemental auras and reactions (Freeze, Vaporize/Melt, Electro-Charged, Superconduct, Swirl), dual-element units, a shatter bonus, kiting.
- **Calibration:** first a 3-number replay summary (`calibrate.py`), then full per-second trajectories (`calibrate_traj.py`) from the replay extractor (`replay/`).
- **Damage-number reader (`replay/dmg.py`):** transformative reactions deal a flat ~800; a normal hit is a fixed fraction of ATK.

## v4: hit-size decomposition

- **Damage per hit:** 0.449 × ATK is exactly Genshin's DEF × RES factor at level 80 (0.5 × 0.9). Other hit sizes are skill multipliers (50% / 150% / 200%).
- **Sappho frame study:**
  - counters don't change damage;
  - her attacks splash at full damage;
  - freezes can last 10 s;
  - bosses may be unfreezable (new `boss_freeze` parameter).

## v5: panel round 1 fixes

- **Sappho and bosses:**
  - Sappho's splash hits the 3 nearest enemies;
  - bosses ignore immobilize.
- **Reactions:**
  - Anemo/Pyro hits end a Freeze;
  - Swirl spreads the absorbed element.
- **Calibration:**
  - shrinkage per replay group;
  - unit bar counts only from bars ≥ 30 px;
  - squad alive-share down-weighted.

Results:
- QF-A: both underdogs the model favoured won.
- QF-B: the model called both favourites correctly.

## v6: implementing the SF panel's fixes (Jaden: "just fix them")

1. **Squad HP rule settled from data:** damage-number totals vs HP-bar loss in R16-B (Fruity) and R16-C (Chubby). Only "full card HP per member" lands in the reader's capture range (0.43 / 0.36 vs 0.23–0.43 on single-unit teams); shared HP gives 0.82 / 0.95. `per_member` is now fixed to 1.
2. **Ninken post-kill plunge** added.
3. **Slimes carry their own element permanently,** so reactions fire on them.
4. **Unit damage priors** centred on measured per-hit damage (`data/unit_hits_measured.csv`).

SF: P(Fruity) 0.91, P(Grenadier) 0.80. Grenadier won; Fruity lost (see v8).

## v7: overtime, targeting, plunge

- **Overtime is a pulse, not a drain.** Every overtime replay shows a single ~11% max-HP hit ~1.3–1.5 s after 00:00, then flat bars for 2.5–4.4 s. Modelled as pulses every `ot_period` s (fit ≈ 8 s).
- **Targeting is now a fitted choice** (nearest / lowest HP / sticky random). The replays lean lowest HP (0.49–0.61), but it isn't settled.
- **Ninken plunge = a normal hit (1×) as AoE,** read off the QF-B frames. The earlier "3×" fit was compensating for nearest-enemy targeting.

## v8: Sappho's frost field (the SF M1 miss)

SF M1 frames show a large field dropped on the enemy cluster:
- an opening hit of 5,461 (0.281 × ATK, Hydro) on everyone inside;
- then repeated 1,092 Cryo ticks (0.0563 × ATK).

That's ~12k per unit per field: it nearly one-shots 13k Scouts and freezes the whole cluster. Damage is measured from the frames; timing, radius and lifetime are fitted. First cast fits at 11.6 s (frames: ~10 s).

Results:
- Best fit so far.
- In-sample, SF M1 now favours Sappho (0.67), as happened.
- Final: P(Fruity) 0.91, P(Saurians) 0.87.

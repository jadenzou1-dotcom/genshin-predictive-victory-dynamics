# Process and Change Log

How the model was built, why each decision was made, and what changed over time. Newest entries at the bottom.

---

## 2026-10-12 — Round of 16, Group A (initial build)

### 1. Understanding the event

- **Is "Switch Counter Relationships" a choice?** No. It's a display toggle ("Display as Selected"). Both counter triangles apply at once; the button just changes which badges are shown.
  - Ranged > Flying > Melee > Ranged
  - AoE > Squad > Single-Target > AoE
- **Scoring rules (in game):** correct pick = emblems × multiplier, wrong pick = emblems × 10, support rate locks 4h before the round ends.
- **Open question:** does betting itself close at the lock, or only the support rate? Unconfirmed, so commit before the lock to be safe.
- **Open question:** do unused emblems carry over (the counter shows 100/300)? Unconfirmed, so spend each round's allotment.

### 2. Payout math first, combat second

The first instinct was "bet the side paying more." That's only right if the crowd overrates the favourite. The correct comparison is EV per emblem, `p·M + (1−p)·10`, where `p` is the true win probability.

Breakeven win probability for an underdog paying `M` against a favourite paying `F`: `p* = (F − 10) / (M + F − 20)`.
- Match 1, Howl at ×105 vs ×30: p* ≈ 17%
- Match 2, Saurians at ×200 vs ×25: p* ≈ 7.3%

### 3. Multiplier formula

Four observed points: 25%→105, 75%→30, 87%→25, 13%→200. Linear and pure-inverse fits disagreed. `M ≈ 20 + 28·(1−s)/s` fits all four within display rounding, with an apparent cap at 200.

### 4. Why counters alone were misleading

The first read, from counter badges only, leaned Howl Crew in Match 1 (its leader counters every Fungi unit, and it has 13 bodies vs 6). The unit stat cards reversed that. Fungi have about 1.6× the total ATK, their AoE attacks one-shot whole 3,000-HP Cicin squads, and the Howl leader's 1,900 ATK barely matters. **Lesson: tags are a tie-breaker; raw HP × ATK dominates.**

### 5. Model v1: deterministic Lanchester-style sim → rejected

The first simulation used listed ATK as damage per hit. It gave 0% and 99.9%. That's not a real result: with no skill-level uncertainty, the larger stat pool always wins. Listed ATK isn't DPS, because skill multipliers and attack speed are hidden.

### 6. Model v2: Monte Carlo over unknown mechanics (current)

Every run samples:

| Unknown | Sampled as | Why |
|---|---|---|
| Counter strength `k` | U(1.1, 2.0), applied ×k or ÷k per triangle | Magnitude not stated in game |
| Squad HP basis | 50/50 per-member vs split across squad | Card says "Max HP" without specifying |
| Damage per hit vs listed ATK | Lognormal(0, 0.6) per unit type | Skill multipliers hidden |
| Attack interval | U(0.5, 2.0)s per unit type | Not shown |
| Splash on "rain/wave/vortex" skills | 50% chance, 0.5× to neighbours | Skill text implies area effects |
| Crowd control (freeze, immobilize, pull) | Stun U(0, 1.5)s per hit | Strength unknown |
| Healing (Hydro Samachurl) | U(0, 2%) max HP/s to allies | Strength unknown |
| Frost Armor damage reduction | U(0, 40%) | Card text cut off |
| HP drain | Starts U(30, 90)s, U(1–5%) max HP/s | Tutorial says it exists; timing unknown |

Targeting is nearest valid enemy. Melee walks in. "Cannot Target Flying" is enforced. AoE hits everything within one cell of the target.

**Sensitivity check:** varying the damage-uncertainty width σ from 0.3 to 1.0:
- Howl's win chance ranges 3.5–19%.
- Saurians' win chance ranges 10–13%, staying above its 7.3% breakeven throughout. That makes the Saurians bet robust to this assumption.

### 7. Results (3,000 runs)

| Match | Model P(left) | Crowd | EV left | EV right |
|---|---|---|---|---|
| Howl vs Fungi | 8.5% | 25% | 18.1 | **28.3** |
| Frostarm vs Saurians | 88.1% | 87% | 23.2 | **32.7** |

The model agrees with the crowd on the *favourites*. The edge comes from the payout asymmetry on Saurians, not from disagreeing about who wins.

### Known gaps (to fix after replays)
- Sappho's Iceshatter Strike follow-up and frost mist aren't modeled beyond generic freeze and splash.
- Movement is crude: only melee units move, and flying units have no special pathing.
- No elemental reactions (e.g. Hydro rain on allies + Cryo attacks → freeze).
- Win condition at timeout is assumed to be the higher remaining-HP fraction.

---

## 2026-10-12 — Risk analysis and allocation

Per emblem, using the model's probabilities. Sharpe is measured as excess over the guaranteed 10 points:

| Bet | P(win) | Mult | EV | SD | Sharpe |
|---|---|---|---|---|---|
| Howl (M1) | 8.5% | 105 | 18.1 | 26.5 | 0.30 |
| **Fungi (M1)** | 91.5% | 30 | **28.3** | 5.6 | **3.28** |
| Frostarm (M2) | 88.1% | 25 | 23.2 | 4.9 | 2.72 |
| **Saurians (M2)** | 11.9% | 200 | **32.6** | 61.5 | 0.37 |

**Sharpe is the wrong objective for this game.** For a binary bet with a fixed floor, `(EV − floor)/SD = sqrt(p/(1−p))`. Payout cancels out entirely, so Sharpe mechanically ranks every favourite above every underdog, however generous the odds. What actually matters:

1. **Reward tiers.** These are thresholds on cumulative score; the visible list tops out at 16,000. Betting favourites at about 28 per emblem over 8 rounds of 100 emblems gives about 22,600 expected, which clears 16,000 comfortably. Extra variance doesn't help here.
2. **Leaderboard rank** (if it exists). Rank is decided by the top of the score distribution, so variance helps and pure EV-maximizing plus variance is the right play.

Shared 100-emblem pool, with x on Saurians and the rest on Fungi:

| x | EV | SD | P(round score < 2000) |
|---|---|---|---|
| 0 | 2830 | 558 | 8% |
| 25 | 2938 | 1594 | 7% |
| 50 | 3046 | 3089 | 7% |
| 75 | 3153 | 4616 | 88% |
| 100 | 3261 | 6152 | 88% |

Up to 50 on Saurians costs nothing in downside: a Fungi win plus a Saurians loss still scores 2,000. Beyond 50, the bad case dominates.

**Two-account plan:**
- **Safe account:** maximize the chance of clearing reward tiers. Take the best-EV favourite each match, and add underdogs only up to the point where the downside floor holds.
- **Aggressive account:** pure EV maximization, aiming at the leaderboard.

---

## 2026-10-12 — Choosing an objective: why not Sharpe, and the two-strategy design

### The question
The first instinct was to maximize Sharpe ratio: Fungi has Sharpe 3.3 and Saurians 0.37, so "obviously" Fungi. Working through it showed why that reasoning doesn't carry over to this game.

### Why Sharpe is the wrong yardstick here
1. **Sharpe assumes leverage.** In markets you take the highest-Sharpe portfolio and lever it to your target risk. Here stakes are capped at 100 emblems per round, so a high-Sharpe, low-return bet can't be scaled up. It just stays low-return.
2. **Sharpe ignores the payout here.** With a guaranteed 10-point floor, `(EV − 10)/SD = sqrt(p/(1−p))`. Only the win probability survives; the multiplier cancels. A ×10,000 bet at 1% would have EV ≈ 110 per emblem but Sharpe 0.1.
3. **No compounding.** Emblems refill every round and losses don't shrink future stakes, so a bad early round costs nothing beyond its own score. Kelly-style bankroll logic doesn't apply.
4. **Variance averages out across rounds.** Over 8 rounds, edge scales with n and noise with √n. All-Saurians beats all-Fungi with just 1 win in 8 rounds, a 64% chance (1 − 0.881⁸).

### The real risk: model risk
Saurians beats Fungi only if its true win chance is above **9.6%**. The model says about 12% (10–13% across assumptions), from a model that hasn't been checked against a single replay yet. The danger is less the dice than the estimate itself being a few percentage points too high.

### Two strategies, run in parallel
Leaderboard reasoning: the top of the leaderboard will be taken by risk-neutral players, some running many accounts, whose high-variance bets hit. A risk-averse strategy can't compete there. So two policies, fixed for the whole event:

| | Strategy A: Risk-adjusted (main account) | Strategy B: EV-max (second account) |
|---|---|---|
| Objective | Maximize `EV − λ·Var` with λ fixed at 1e-4 | Maximize expected score (risk-neutral, λ = 0) |
| Goal | Reliable baseline | Leaderboard upside |
| R16-A pick | ~100 → Fungi (M1) (mean-variance optimum puts only ~1–7 on Saurians) | 100 → Saurians (M2) |

Why run both:
- Whichever way the model is wrong, one strategy captures it.
- Comparing final totals gives an empirical answer to "does risk-neutral EV-max beat risk-averse over an 8-round event?"
- λ stays fixed all event, so the comparison stays clean.

### Why specialize the two strategies instead of splitting 70/30 on each?

1. **70/30 isn't the max-Sharpe split.** Sharpe peaks at about 1 emblem on Saurians (3.29) and drops fast: 10 → 2.36, 30 → 1.04, 100 → 0.37. A 30-emblem underdog position already gives up about two-thirds of the Sharpe. If the goal is risk-adjusted return, the answer is essentially all Fungi.
2. **Combined, the totals are the same kind of thing.** 100 Fungi on one account plus 100 Saurians on the other is a 50/50 split of 200 emblems. 70/30 on both is a 70/30 split of 200. Splitting within an account vs across accounts doesn't change the *expected* total, only how the outcomes are distributed between the two accounts.
3. **Each account is scored separately.** Splitting within an account pulls its outcomes toward the middle: a lower floor than pure Fungi, a lower ceiling than pure Saurians. Specializing gives one account the strongest floor and the other the best shot at the top of the leaderboard. Two middling accounts get neither.
4. **Clean experiment.** Two pure strategies give an unambiguous answer about which objective wins over the event. Blended strategies blur that comparison.

---

## 2026-10-12 — Correction: Strategy A is max-Sharpe, diversified across favourites

The earlier analysis only considered splitting between Fungi and Saurians, and concluded that a risk-aware account goes about 100% Fungi. That missed the obvious diversifier: **the other match's favourite.** Diversification raises Sharpe when the bets have *similar* risk, and Fungi (SD 5.6 per emblem) and Frostarm (SD 4.9) do. Saurians (SD 61.5) doesn't.

For independent bets, the tangency (max-Sharpe) weights are proportional to `excess EV / variance`, and the combined Sharpe is `sqrt(S1² + S2²)`:

| Allocation | EV | SD | Sharpe |
|---|---|---|---|
| 100 Fungi | 2830 | 558 | 3.28 |
| **51 Fungi / 49 Frostarm** | **2582** | **371** | **4.26** |

Including Saurians in the tangency gives it about 0.5% weight, i.e. nothing.

**Final strategy definitions** (computed each round by `strategies.py`):

| | Strategy A: max-Sharpe (main account) | Strategy B: max-EV (second account) |
|---|---|---|
| Rule | Tangency portfolio across the per-match higher-Sharpe sides | All emblems on the single highest-EV side |
| R16-A | 51 Fungi / 49 Frostarm (EV 2582, Sharpe 4.26) | 100 Saurians (EV 3261, Sharpe 0.37) |

This replaces the earlier `EV − λ·Var` framing for A. With λ = 1e-4 that objective still chose about 100 Fungi, because it trades EV for variance at a fixed rate. Max-Sharpe is the cleaner "risk-adjusted" objective and matches the intent.

### Paper benchmarks
A "standard player" strategy doesn't need its own account. It can be scored on paper from the logged results:

- **naive-underdog**: split evenly across the highest-multiplier side of each match (what a player chasing big payouts without win estimates does). R16-A: 50 Howl / 50 Saurians, EV 2534.
- **crowd-favourite**: split evenly across the most-supported side of each match. R16-A: 50 Fungi / 50 Frostarm.

Comparing A and B against these at the end of the event shows how much the model actually added.

Note: if each match turns out to have its own 100-emblem pool rather than one shared pool, A becomes 100 on each favourite and B becomes 100 on the highest-EV side of each match.

### Where 51/49 comes from (and how flat the peak is)
For independent bets, Sharpe-maximizing weights are proportional to `excess EV / variance`:
- Fungi: 18.3 / 5.58² = 0.588
- Frostarm: 13.2 / 4.86² = 0.559

Normalized, that's 51.3% / 48.7%. Frostarm gets almost equal weight despite lower EV because it's slightly less risky per emblem, and the two outcomes are independent, so their noise partly cancels.

`allocation_curve.py` sweeps every split and plots Sharpe, EV and SD (`charts/R16-A_allocation.png`). The peak is very flat: 45/55 to 55/45 all give Sharpe 4.23–4.26. The trade-off versus 100 Fungi: EV −249 (2,830 → 2,581) for SD −187 (558 → 371). Strategy A accepts lower expected score in exchange for a much tighter outcome range; that's the definition of the strategy.

---

## 2026-10-13 — R16-A results, replay analysis, model v3 and calibration

### Results
| Match | Model (pre-match) | Crowd | Winner | Brier model | Brier crowd |
|---|---|---|---|---|---|
| Howl vs Fungi | Fungi 91.5% | Fungi 75% | **Fungi** | 0.007 | 0.063 |
| Frostarm vs Saurians | Saurians 11.9% | Saurians 13% | **Saurians** | 0.776 | 0.757 |
| **Mean** | | | | **0.392** | **0.410** |

The model's probabilities were slightly better than the crowd's on Brier score, mostly from being more confident on Fungi. Two matches is far too few to conclude anything. Strategy B (100 Saurians) hit, and Strategy A's Frostarm half missed.

### What the replay showed (`notes/R16-A.md` has the detail)
Measured with `replay_hp_tracker.py`: OpenCV samples both team HP bars 5×/s → `data/replays/R16-A_hp_bars.csv`. Plus frame inspection and the in-game commentary.
1. **Fixed 45 s battle clock**, with no visible HP drain inside it. The v2 drain assumption (starting 30–90 s in) was wrong; battles are decided by trading damage.
2. **Elemental reactions matter.** Sappho alternates Hydro and Cryo and freezes enemies by herself. The Fungi's mixed elements created "a cauldron of elemental reactions".
3. **Ranged bosses kite melee.** The Lawachurl, the last Frostarm unit alive, dealt no damage for the final ~13 s.
4. Observed outcomes, logged to `data/replays/R16-A_outcomes.csv`: Fungi won with ~54% HP, Howl wiped at ~35 s; Saurians won with ~26% HP, Frostarm wiped at ~43 s.

### Model v3 (`sim.py`)
- Every unit gets an `element` (`units.csv`). Hits apply auras (6 s). Reactions: Freeze (Hydro+Cryo, stuns), Vaporize/Melt (×amp), Electro-Charged (×1.25), Superconduct (×1.15), Swirl (0.5× splash).
- Dual-element units (`Hydro|Cryo`) alternate elements. Hits on frozen targets get a shatter bonus.
- `kites = yes` units step away from adjacent melee enemies.
- 45 s clock. At timeout the higher remaining-HP fraction wins (assumption; not yet observed).
- Squad members are spread slightly, so one AoE doesn't always hit a whole squad.
- New global parameter `g` (damage per hit ÷ listed ATK) sets the battle's time scale.

**v3 mechanics alone (prior, no calibration) moved Saurians from 11.9% → 19%.** That's directionally right, but it was only knowable after seeing the replay.

### Calibration (`calibrate.py`): nested approximate Bayesian computation
- A parameter draw "reproduces" a replay if the sim gets the right winner, the winner's HP within ±0.15, and the wipe time within ±8 s.
- For each of 2,500 global-parameter draws, 40 random per-unit draws are tried per match. The global draw's weight is the product of the per-match acceptance rates.
- 99 global draws reproduced both replays. They're saved with their weights to `data/calibration_samples.csv`, and `sim.py` now samples from them by default (`--prior` to disable).

What was learned (weighted 10/50/90%):

| Parameter | Prior | Posterior |
|---|---|---|
| `g` (time scale) | 0.02–1.0 (median 0.14) | **0.07 / 0.10 / 0.15**, tightly pinned by battle duration |
| `k` (counter strength) | 1.1–2.0 | 1.33 / 1.72 / 1.94, counters are strong |
| `freeze_s` | 0.5–4 s | 0.6 / 1.2 / 2.7 s |
| Sappho damage multiplier | ~1.0 | 0.8 / 1.6 / 2.8, hits harder than listed ATK |
| Ladler of Broth damage multiplier | ~1.0 | 0.9 / 1.7 / 3.3, consistent with cabbages hitting twice |
| most other unit params | — | still close to prior; one replay can't separate them |

### Caveats
- **Retrodiction isn't prediction.** On the same two matches, the calibrated model gives Saurians 96%, but it was fitted to that outcome. The honest test is the next round.
- Unit-specific posteriors come from a single battle each, so they're likely **overconfident** for units seen once. Global parameters (`g`, `k`, `freeze_s`) are shared across all matches and are the most reliable gain.
- Units not seen in any replay still use the prior.
- The calibration is cumulative: add each round's `*_outcomes.csv`, then rerun `python calibrate.py`.

### Same day: correcting overconfidence after the fit
The calibrated model gave Saurians 96% on a rematch. That's overconfident: the fit conditioned on a single close battle (Frostarm wiped 1–2 s before the clock), so it only kept parameters under which Saurians win. Three fixes:
1. **Shrinkage toward the prior for per-unit parameters.** A unit seen in n replays uses its fitted value with probability n/(n+2): about 33% after one battle, 50% after two, rising as evidence accumulates. Global parameters (`g`, `k`, `freeze_s`, …) are shared by every match and aren't shrunk.
2. **Per-battle noise.** Each unit's damage gets a lognormal(0, 0.15) "luck" draw per battle (crits, targeting order), so identical lineups don't always end the same way.
3. **Cryo-slow hypothesis.** New parameter `cryo_slow`: attack interval × (1 + cryo_slow) while the attacker has a Cryo aura. 50% prior mass at 0, otherwise 0–0.5. Posterior median 0, 90th percentile 0.35. Not ruled out, but no evidence for it yet.

Per-unit results are now reported as a **damage-rate multiplier** (damage ÷ attack interval). Those two can't be separated from HP curves; only their ratio can. Clear signals so far: Ladler of Broth ×2.5 and Sappho ×1.8. Every other unit's 10–90% range still spans roughly ×0.4 to ×2+, i.e. undetermined.

| Match | Pre-video (v2) | Post-video, fitted, unshrunk | Post-video, shrunk + noise (current) | Winner |
|---|---|---|---|---|
| Howl vs Fungi | Fungi 91.5% | Fungi 99.8% | Fungi 98.4% | Fungi |
| Frostarm vs Saurians | Saurians 11.9% | Saurians 96.2% | Saurians 30.0% | Saurians |

---

## 2026-10-13 — R16-B: learned AoE radius, overtime drain, picks
- **New global parameters:** `aoe_r`, the AoE radius in cells (prior 0.4–1.6), and `drain`, a flat HP/s lost by **every** unit once the 45 s clock ends (user hypothesis; prior 1k–8k). Battles now continue into an overtime until one side is wiped.
- **Recalibrated on the R16-A replays:** `aoe_r` → 0.67 / **1.35** / 1.52 (AoE hits wide, consistent with the Fungi shredding the Cicin squads). `per_member` → median 0, i.e. squad HP is more likely **shared** across members. `drain` stays at the prior because no replay has gone to time yet.
- **Model (support rates not used):** M1 Elemental Dye 78.5%; M2 Blazing Beasts 60.5%. In M2, 64% of sims go to overtime, where the Mechanoid's 93k HP under a flat drain helps the right.
- **Strategy A (max-Sharpe):** 28 on Elemental Dye (M1) + 72 on Blazing Beasts (M2): EV 3,952, Sharpe 2.28.
- **Strategy B (max-EV):** 100 on Elemental Dye (M1): EV 8,458.

### Rethinking Strategy A: Sharpe → mean-variance utility (proposed)
Worked examples showed the problem with Sharpe here. Dropping a coin's win payout from 50 to 20 nearly doubled its Sharpe while halving its EV. Without leverage, Sharpe rewards *smallness* of swings, not quality of bets.

**Proposed replacement:** maximize the certainty equivalent `CE = EV − (λ/2)·Var` over the emblem split. This keeps payout size in the objective, and λ is an explicit risk-aversion dial: λ = 0 is pure EV (Strategy B); large λ approaches minimum variance.

R16-B worked example (Elemental Dye p = .785 ×105, Blazing Beasts p = .605 ×30):

| λ | Elemental Dye / Blazing Beasts | EV | SD |
|---|---|---|---|
| 0 – 0.0002 | 100 / 0 | 8,458 | 3,903 |
| 0.0005 | 83 / 17 | 7,395 | 3,244 |
| 0.001 | 44 / 56 | 4,959 | 1,802 |
| 0.002 | 25 / 75 | 3,772 | 1,221 |

Context: every split's worst case is 1,000 (both picks lose), so downside is bounded and there's no ruin. The real risk is **model error**. Even at pessimistic win rates (Elemental Dye 49%, Blazing Beasts 57%), Elemental Dye's EV per emblem (56.6) beats Blazing Beasts' (21.4).

---

## 2026-10-13 — Finding: where the Sharpe ratio falls short (spotted by Jaden)

**The observation.** Jaden noticed that Strategy A (max-Sharpe) put *fewer* emblems on Elemental Dye (model 78.5%, ×105) than on Blazing Beasts (60.5%, ×30), even though Elemental Dye was better on both win rate and payout. He reduced it to two coins:

| Coin | Lose | Win | EV | SD | Sharpe (excess over 10) |
|---|---|---|---|---|---|
| 1 | 30% → 10 | 70% → 100 | 73.0 | 41.2 | 1.53 |
| 2 | 40% → 10 | 60% → 50 | 34.0 | 19.6 | 1.22 |
| 2′ (win payout cut to 20) | 40% → 10 | 60% → 20 | 16.0 | 4.9 | 1.22 → **2.04** |

Cutting Coin 2's payout from 50 to 20 makes it a strictly worse bet: same odds, lower payout, half the EV. Yet its Sharpe goes **up**, from 1.22 to 2.04. A metric that rewards making a bet worse is the wrong metric for this problem.

**Why it happens.** For a binary bet with a payout floor, Sharpe = `(EV − floor)/SD` = `sqrt(p/(1−p))`. The payout size cancels completely. Sharpe sees only how *reliably* a bet wins, never how *much* it wins.

**Why quants still use Sharpe (it isn't wrong in general).** Sharpe is the right yardstick when position size is freely scalable through leverage or cash:
- If you can lever, you hold the highest-Sharpe portfolio and scale it to your risk tolerance. Two strategies with the same Sharpe are equivalent after scaling, so Sharpe alone ranks them (two-fund separation).
- It's invariant to scale, so strategies of different sizes can be compared.
- It assumes roughly symmetric, near-Gaussian returns from many repeated bets.

**Where it falls short (the use-case gap).**
1. **No leverage / capped stake.** 100 emblems is a hard cap, so a smooth low-return bet can't be scaled up. Max-Sharpe then just picks the smallest swings and leaves EV on the table.
2. **Lumpy, skewed binary payoffs.** Variance penalizes *upside* swings as much as downside. Here the swing comes mostly from the chance of a big win, not a big loss.
3. **Bounded downside.** The worst case is the 10-point floor, so ruin isn't possible and variance overstates real risk.

Known alternatives in the literature address parts of this: the Sortino ratio (downside deviation only), the Omega ratio, CVaR, and Kelly / log utility.

**Decision.** Strategy A switches from max-Sharpe to **max certainty equivalent**: `CE = EV − (λ/2)·Var`, with λ fixed for the rest of the event (value to be chosen by Jaden). This is the same mean-variance framework Sharpe comes from. With leverage, maximizing CE means "hold the max-Sharpe portfolio, scaled by 1/λ". Without leverage the scaling step isn't available, so CE is optimized directly over the capped split. Rounds R16-A and R16-B were played under max-Sharpe and are logged as such.

---

## 2026-10-13 — R16-B results: first clear model miss
| Match | Model (left) | Crowd (left) | Winner | Brier model | Brier crowd |
|---|---|---|---|---|---|
| Elemental Dye vs Mirror Fruity | 78.5% | 21% | **Mirror Fruity (R)** | 0.616 | 0.044 |
| Blazing Beasts vs Rude-a-Lot | 60.5% | 78% | **Blazing Beasts (L)** | 0.156 | 0.048 |

**Cumulative Brier over 4 matches: model 0.389 vs crowd 0.228.** The crowd is now clearly ahead, and the model was confidently wrong on Match 1.

Round scores (losing picks pay the 10/emblem floor):
- Strategy A (max-Sharpe, 28 Dye / 72 Blazing Beasts): 280 + 2,160 = **2,440**
- Strategy B (max-EV, 100 Dye): **1,000**
- Paper benchmarks: crowd-favourite (50 Fruity / 50 Blazing Beasts) 3,000; naive-underdog (50 Dye / 50 Rude-a-Lot) 1,000.
- The proposed CE rule at λ = 0.0005 (83 Dye / 17 Blazing Beasts) would have scored 1,340.

Suspected causes for the Match 1 miss, to check against the replay:
1. **AoE radius.** The R16-A fit pushed it to ~1.35 cells, and that assumption alone moved Dye from ~49% to ~78%. If AoE actually hits fewer units, the squads survive.
2. **Specters may be fragile in practice.** 20k HP each against 4 Potioneers plus 6 Scouts, all ranged and all able to hit flyers.
3. **Handymen may matter more than modeled,** e.g. by killing the Finch quickly and then soaking hits.
4. **General overconfidence.** Per-unit priors for 7 brand-new units, with no replay data on any of them, still produced a 78% call.

Lesson: a model fitted on 2 battles shouldn't output 78% on a lineup made entirely of unseen units. The next change should widen uncertainty for unseen units, or shrink predictions toward 50% in proportion to how many units are unseen.

---

## 2026-10-13 — R16-B replay, recalibration on 4 battles, Group C predictions
**Replay findings:**
- Overtime is real. At 00:00 the commentator says "The battle reaches its final stage! Both sides continuously take damage!", and **both R16-B matches were decided in overtime.**
- In Match 1 the Treasure Hoarder squads were **not** shredded by AoE.
- The Pyro Specter's immunity kept Elemental Dye alive into overtime and nothing more.

**Model changes:**
- Overtime drain can be **flat** HP/s or a **percentage** of max HP/s (`drain_mode`); the two clips can't yet distinguish them.
- Fontemer shells break after 3–10 reactions (Crab → melee Physical, Seahorse → single-target Hydro).
- Geo Ward = shield worth 10–40% of max HP.
- Opening AoE moves = one 2× AoE hit at t = 0.
- **Lineup tempering:** reported p = 0.5 + (p_raw − 0.5)·(0.4 + 0.6·seen_share), where seen_share = share of the lineup's unit types that have appeared in a replay.

**Recalibration on all 4 replays** (29 / 1,500 global draws accepted):
- `aoe_r` fell from 1.35 to **~1.0** (0.45–1.28). The R16-B squads surviving pulled it down.
- `per_member` now leans per-member.
- Specters' damage rate ~0.5×; Treasure Hoarders ~1.2–1.6×.
- Retrodiction on R16-B M1 is now 52% Dye (was 78.5% pre-match).

**Group C (all 13 unit types unseen → heavy tempering):**

| Match | Raw | Tempered | Crowd (early) | Biggest unknown |
|---|---|---|---|---|
| Reserve Grenadier vs Seahorse and Crab | 78.7% L | **61.5% L** | 82% L | AoE radius (73–84%) |
| Chubby Crisis vs Consecrated Beasts | 52.6% L | **51.0% L** | 22% L | **Overtime drain type:** flat → 36% L, percentage → ~100% L |

Match 2 is effectively a coin flip that hinges on one mechanic. A percentage drain would melt the two big bosses while sparing the 14k-HP slimes, and a flat drain does the reverse. 76% of sims go to overtime.

---

## 2026-10-15 — Decisions recorded: CE for Strategy A, saving emblems, crowd log

- **Strategy A objective is CE.** Of the alternatives discussed (CE, log utility, robust EV), Jaden chose `CE = EV − (λ/2)·Var`. λ is still to be fixed and held for the rest of the event. `strategies.py` still implements max-Sharpe; updating it is pending.
- **Saving emblems (decided 2026-10-13).** Jaden's reasoning: the model improves with every replay (cumulative calibration, per-unit shrinkage `n/(n+2)`, tempering for unseen lineups), and the quarterfinals will be fought by units already seen. So skip Groups C and D and spend saved emblems in the quarterfinals. Rollover is unconfirmed, so Group C doubles as a test: Account A skips, Account B bets as a control. This mixes a rollover test into the A-vs-B comparison for one round.
- **New file `data/crowd_log.csv`.** Support rates and multipliers disappear once a round ends, so each on-screen snapshot is now logged with a timestamp and whether the rate had locked. Backfilled from earlier screenshots. R16-C multipliers weren't recorded.
- README now has a "Strategy decisions" section covering the Sharpe finding, the CE switch and the saving plan.

---

## 2026-10-15 — Readable results page

`data/matches.csv` is the record but is hard to read on GitHub. New `make_results.py` generates `RESULTS.md` from `matches.csv` and `crowd_log.csv`: a model-vs-crowd scoreboard (correct calls, mean Brier), then one card per match (support, multipliers, model win chance, winner, picks, notes) and the round's crowd snapshots. The CSVs remain the source of truth. The hand-maintained results table in the README was replaced with a link, so there's one copy.

---

## 2026-10-15 — Group C and D results logged (no picks in either)

- **Results.** R16-C: Reserve Grenadier Squad beat Seahorse and Crab (final support 85/15); A Little Chubby Crisis beat Consecrated Beast Frightfest (23/77, crowd favourite lost). R16-D: What Does the Ninken Say? beat Simple-Soul Hilichurl Fighters (82/18); Round-and-Frost Assault beat Ultra-Ancient Heavy Assault Formation (34/66).
- **No picks.** Both screens show "Did Not Participate" for C and D. C was skipped on purpose; D was missed. No model prediction exists for D, and its units aren't in `units.csv` yet.
- **Multipliers unavailable.** The post-round screen shows support rates but not multipliers to non-participants. Multiplier columns left blank rather than estimated. Side note: the observed pairs (21/22/25% → ×105, 75/78/79% → ×30, 87% → ×25, 13% → ×200) look like a step function, not the smooth `20 + 28·(1−s)/s` fit in the README (which gives ~120 at 21–22%). Worth revisiting before the next allocation.
- **Brier.** C1 model 0.148 / crowd 0.023; C2 model 0.240 / crowd 0.593. Crowd Brier uses the final post-round rates (early snapshots were 82/18 and 22/78, kept in `crowd_log.csv`).
- **Overtime hint (weak).** C2 hinged on drain type: flat → 36% L, percentage → ~100% L. Chubby Crisis won, which is one data point toward percentage drain. Not confirmed until the C2 replay is checked for whether it went to overtime.
- **`make_results.py` fix.** The scoreboard counted D (no model prediction) as model misses. Now both columns are scored only on matches the model predicted.

---

## 2026-10-15 — QF-A predictions, crowd blend, outside data check

- **QF-A logged.** Both matches are R16 rematches with every unit already seen (no tempering). Placements show a team that switches sides is rotated 180°: row r → 5−r, col c → 7−c.
- **Sim:** M1 Saurians 67.5% (flat drain 69% / pct drain 53%); M2 Fruity 57.6% (flat 55% / pct 70%). Crowd early: 39% and 17%.
- **New `blend.py`:** logit p = w·logit(model) + (1−w)·logit(crowd), Beta(2,2) prior on w, grid posterior. On 6 matches: w ≈ 0.46 (80% interval 0.17–0.75). Leave-one-out log loss: model 0.903, crowd 0.741, blend 0.780, so there isn't yet evidence the blend beats the crowd. Blend for QF-A: M1 Saurians 52%, M2 Fruity 33%. Both underdogs remain +EV because of the multipliers.
- **Outside data.** A third-party event guide (allthings.how) confirms: fixed-rule simulation, support rate has no effect on combat and locks 4 h before round end, wrong pick = 10 pts/emblem, long fights get a continuous-damage phase. It states the class triangle as Ranged > Melee > Flying > Ranged, which is the **reverse** of the in-game legend. The legend's arrows read Melee → Ranged → Flying → Melee, and the same arrow convention gives AoE → Squad → Single-Target → AoE, which the guide agrees with. So the sim's `BEATS` is kept as is and the guide is treated as wrong on that point. Its Group D table added multiplier tier points (35% → ×70, 65% → ×35).
- **Open-world wiki data not used.** Event units have custom HP/ATK and event-only mechanics, and the sim has no RES term, so open-world RES values and attack patterns don't map onto any sim parameter.
- **Multiplier is a step function.** README payout section rewritten with the observed tiers.
- **Known bug:** `sim.py` defines `tempered()` but never calls it; Group C's tempered numbers were computed outside the main loop. Irrelevant for QF-A (all seen); fix before a round with new units.

---

## 2026-10-15/16 — Replay extraction framework + trajectory calibration

**Why.** Calibration used 3 numbers per replay (winner, winner HP, wipe time), which throws away almost everything a recording shows.

**`replay/` (new).** `extract.py` reads a recording at 10 frames/s and logs:
- both team HP bars (as before);
- every overhead unit HP bar (`bars.py`): ~4 px bars, bright red = left, light blue = right, with the dark segment beside each giving lost HP. Gives per-frame visible bodies per side and each body's HP fraction. Validated against lineups: R16-C M1 reads 5 vs 6 bars, R16-B M1 Fruity 15 of 16 bodies;
- the match clock (OCR, rapidocr) to align video time to battle time;
- commentary lines (OCR, de-duplicated) with clock times. These form an event log: e.g. R16-A "Ladler of Broth's followers are dropping one by one" at 0:26; R16-B "Mechanoid Assistant couldn't provide support in time" at 0:20; R16-C "Fontemer Aberrants trigger Overloaded deliberately"; R16-D "Round-and-Frost froze every opponent" at 0:21.

`observe.py` turns this into per-second battle-time curves: team HP L/R and share of bodies alive L/R. Alive count = rolling max over 5 s (bridges occlusion) followed by a running minimum (dead stays dead), normalised by the opening count.

**Not done: damage numbers.** Small, semi-transparent and stacked; three OCR approaches gave unstable reads (the same crop read 1375 / 13756 / 1342), so they're excluded rather than adding noise. Next attempt would be template matching on the game's digit glyphs.

**`sim.run(..., trace=[])`** records team HP and bodies alive every simulated second.

**`calibrate_traj.py` (new).** Kernel ABC on the whole fight: d = RMSE(team HP, both sides) + 0.5·RMSE(alive share) + 0.25·[wrong winner]. Alive share is only used for a side whose opening bar count matches its body count ±25% (bosses can carry extra bars). Distances are stored and the tolerance is picked afterwards: smallest EPS with effective sample ≥ 40. Run: 3,000 draws, EPS = 0.15, **ESS 96** (old method: 23 draws). Previous posterior kept as `data/calibration_samples_summary_only.csv`.

Posterior changes: **squad HP is per member** (settled); **P(flat overtime drain) 0.78 → 0.42**; g ≈ 0.08 (0.06–0.11), counter k ≈ 1.44 (1.19–1.79), AoE radius ≈ 0.63 cells.

**Retrodiction (in-sample, P(sim picks the observed winner)):** A1 0.97, A2 0.34, B1 0.61, B2 0.57, C1 0.70, C2 0.79. **A2 is a systematic miss:** Saurians ("Sappho") won R16-A as a 13% underdog, and even after fitting, the sim gives her only 34%. (Correction: an earlier chat note said Sappho lost R16-A; she won.)

**QF-A after trajectory calibration:**
| | sim | flat / pct drain | crowd | blend |
|---|---|---|---|---|
| M1 Saurians | 30% | 54% / 18% | 38–39% | 35% |
| M2 Fruity | 71% | 61% / 79% | 16–17% | 39% |
Treat M1's 30% as a likely underestimate given the A2 miss. M2 favours Fruity in every version of the model so far.

**Community research.** Event names: 判测胜券本征 (CN), 勝者は誰だ！？ (JP). CN sources (Bilibili, 3DM, TapTap, 17173) carry pick videos and announcements, no mechanics. JP: Game8 logs support from start to end of each round and the multipliers; 100 emblems/day; bets can be changed until the match starts; daily participation is required for that day's Primogems (≥5 prediction days for full rewards). The on-screen "300/300" may be a cap, which would make skipping a day lose emblems; unconfirmed. Game8 saw 39% → ×50 and 61% → ×40, while we saw 39% → ×70 and 61% → ×35, so there is a tier edge near 39/61. No public source gives the overtime formula or unit stats.

---

## 2026-10-16 (01:00–02:10) — Damage numbers, two independent audits, model v3

**Damage-number reader (`replay/dmg.py`, `replay/attribute.py`).** Colour masks failed: Cryo/Hydro numbers share colours with ice effects and HP bars. The working version uses a text detector (rapidocr DBNet) on each half of the frame upscaled 1.6x at 5 frames/s. Reads are grouped into pops (same value, nearby, within 1.2 s of first appearance). The per-match vocabulary is values seen in ≥3 distinct pops, minus fragments (752/175 inside 1752) and merges. Output is `*_hits.csv`: match, battle time, value, element (from colour), target side (from the HP bar below the number). Frame-checked precision: values ~75–85% right (stacked numbers are the main failure); element and target tags are noisier. Reaction numbers are salmon-coloured and get mislabelled.

**Measured from frames, verified independently by a second agent:**
- **Normal hit = 0.225 × card ATK:** Sternshield Crab 2269/10.1k, Pyroslinger Bracer 658/2.9k, Red Vulture 4202/18.7k, Hailstorm Cannoneer 2202/9.8k. Now fixed in the sim (`HIT_G`); g is no longer a free parameter. Previously the sim fitted g ≈ 0.08 and compensated with attacks ~3x too fast.
- **Skill ladder:** many hits land at exactly 2× or 3× base (0.449/0.674 × ATK). An earlier reading of the 2× hits as a **counter bonus was wrong.** The verifying agent found the same attacker hitting one target for 1236 and 2472 back to back (Desert Clearwater, R16-B), and disadvantaged attackers hitting at 2× (Galehunter on Big Bro). The counter range was briefly narrowed to 1.7–2.3 on the wrong reading, then reverted to 1.0–2.5. Unit damage-per-attack prior is now centred at 1.3× base (lognormal sd 0.4) to cover the ladder.
- **Transformative reactions deal flat damage:** 400/800 recur dozens of times across attackers with very different ATK. Overloaded / Electro-Charged / Superconduct now deal a flat 800 (through Geo Ward) instead of a ×1.15–1.25 multiplier. Unclear: 400 lands mostly on the right side and 800 mostly on the left in R16-C M1, so the split may depend on side or target.

**Audit 1 (code/data review), fixed:**
- the old posterior's g was overriding the new fixed HIT_G (now forced in `draw_params`);
- alive-share curves were biased: deaths showed ~2 s late (now a forward-looking window) and the loser never reached 0 at the wipe (curves now anchored to the logged wipe time, loser set to 0);
- calibration kept the best of 20 unit draws instead of sampling by weight (overconfident unit posteriors); fixed;
- damage clean-up counted frames not pops, kept fragments, and chained repeated hits; fixed;
- README tier table now lists sources and the 39/61 conflict (ours ×70/×35 vs Game8 ×50/×40);
- README workflow updated; rollover note corrected (both accounts skipped C and D, so the planned control test never ran).
Audit confirmed correct: all winners, all 14 Brier values, QF-A 180° rotations, blend math, counter directions vs the legend.

**Refit (v3):** `calibrate_traj.py 3000 2` → EPS 0.10 (tighter than v2's 0.15), ESS 70. Posterior: k ≈ 1.25 (1.06–1.58), amp ≈ 1.56, AoE radius ≈ 0.62, P(flat drain) = 0.42, squad HP per member.

**In-sample retrodiction P(observed winner):** A1 0.98, A2 0.27, B1 0.67, B2 0.51, C1 0.72, C2 0.92. A2 (Saurians/Sappho beating Frostarm as a 13% underdog) is still a systematic miss.

**QF-A (v3):**
| | sim | flat / pct drain | crowd | blend | EV under / fav (blend) |
|---|---|---|---|---|---|
| M1 Saurians | 60.5% | 65% / 55% | 38–39% | 48.8% | 39.3 / 22.8 |
| M2 Fruity | 80.5% | 75% / 86% | 16–17% | 45.0% | 52.7 / 21.0 |

M1 has swung 67.5% → 29% → 30% → 60.5% across model versions, so it is low confidence and still depends on the multiplier tier at lock (breakeven for Saurians: 29% at ×70/×35, 43% at ×50/×40). M2 has favoured Fruity in every version (56–81%). Caveat: the blend weight w was learned from older model versions' pre-match calls.

---

## 2026-10-16 (12:00–12:45) — Hit-size decomposition, Sappho frame study, model v4, CE allocation

**Hit size is DEF × RES, not 0.225 (Jaden's question).** Sorting attributed hits by damage ÷ card ATK, the most common ratio is **0.449** (7 units), not 0.225 (3 units). Genshin's formula gives this exactly. All units are level 80, so the DEF factor = (80+100)/((80+100)+(80+100)) = 0.5; standard 10% RES gives 0.9; product 0.45. The other rungs are skill multipliers: 0.225 = 50%, 0.674 = 150%, 0.908 = 200%. The sim now uses `HIT_G = DEF_FACTOR × RES_FACTOR = 0.45` with the skill-multiplier prior centred at 1.0 (lognormal sd 0.45). Not yet modelled: per-target RES (immune elements are already handled; bosses may have higher RES).

**Sappho frame study (R16-A M2, ~150 frames, subagent):**
- **Counters don't change damage:** Electro shooter → Sappho 2112 = 0.45×4700 (sim applied ×k), Lawachurl → Sappho 5303 = 0.45×11800, Sappho → shooter squad 8737 = 0.45×19400 (sim applied ÷k). This agrees with the earlier frame check. k prior now 1.0–1.15 (posterior ≈1.08).
- **Sappho's attacks splash at full damage** (5461 on 3 units at 00:34; 8737 on 3 at 00:26) plus a lingering frost field. Tagged `Splash AoE` in units.csv; the sim applies full damage within aoe_r (no extra 0.5× secondary splash on top).
- **Freezes last long:** the Lawachurl was frozen 10 s straight at the end. freeze_s prior widened to 0.5–6 s; posterior median 3.6 s (was ~2).
- **Bosses may be unfreezable.** Over a 0.5 s / 0.25 s sweep, Sappho had 2 Hydro+Cryo chances and 0 freezes, while the Lawachurl froze 4×. New global `boss_freeze`, prior P(freezable) = 0.25 (weak evidence, not 0). No replay identifies it.
- The sim ran this fight ~2.5× too fast (17.5 s vs 43 s); refitting with the measured hit size should reduce that.

**Refit v4:** EPS 0.10, ESS 42, k ≈ 1.08, freeze_s ≈ 3.6 s, P(flat drain) 0.43. In-sample P(observed winner): A1 0.97, **A2 0.33** (still a miss), B1 0.66, B2 0.60, C1 0.72, C2 0.95.

**QF-A (v4):**
| | sim | splits | crowd | blend | EV under / fav |
|---|---|---|---|---|---|
| M1 Saurians | **52.7%** | boss freezable 23% / not 62.5%; flat 43% / pct 40% | 38–39% | 45.2% | 37.1 / 23.7 |
| M2 Fruity | **87.5%** | boss-freeze irrelevant; flat 84% / pct 88% | 16–17% | 50.4% | 57.9 / 19.9 |

**`strategies.py` rewritten:** A = max CE = EV − (λ/2)·Var by exhaustive search over side and emblems (steps of 5, cap 100/match, pool default 200); B = max EV; λ sweep printed because λ isn't fixed yet. With blend probabilities, every λ up to 2e-4 gives 100 on Saurians + 100 on Fruity (EV 9,498, SD 5,610); at λ = 5e-4 it switches to both favourites (EV 4,363, SD 1,596).

**Decision risk:** M1's breakeven is 29% at ×70/×35 but 43% at ×50/×40 (Game8 saw ×50 at 39%). At the blend's 45%, Saurians is +EV in both cases, narrowly at ×50. Read the multiplier at lock.

---

## 2026-10-16 14:30 — Fresh-eyes review before lock

An independent agent with no prior context reviewed the whole pipeline. **Verdict: both picks sound with caveats.**
- **Fixed:** `boss_freeze` was inherited from posterior rows (fit under a 50/50 prior, weighted mean 0.53), so the raw sim gave M1 0.418 while matches.csv held a hand-mixed 0.527. Since no replay identifies it (likelihood ratio ~1.1), it is now always drawn from its evidence-based prior (P(freezable) = 0.25). Raw sim: **M1 0.521, M2 0.878**, consistent with the hand mixture.
- **M1** is driven by tuning choices more than data: per-unit shrinkage (all-posterior units → 0.97 if not freezable) and aoe_r (posterior 0.44–0.87 is below the ~1-cell spacing between Fungi, so her splash rarely hits a second Fungus; aoe_r = 1.0 → 0.89). The R16-A M2 in-sample miss (0.31) comes from shrinking Sappho toward the prior. The shrunk model probably underrates Saurians.
- **M2** depends on per_member: per_member = 0 gives 0.51, = 1 gives 0.92. The posterior is 0.93, and damage numbers confirm squads hit at full card ATK per member (Scout 1033 = 0.449 × 2300, 11×). Other sensitivities stay at 0.73–0.94. The crowd's 17% would need Eremite damage more than 2× the sim's; no mechanism found. The one big earlier model-vs-crowd disagreement (R16-B M1) went to the crowd.
- **Blend weight w** was fit on v1–v3 calls; its own leave-one-out favours crowd-only. With w = 0, M1 is +EV at ×70/×35 (33.4 vs 25.2) but not at ×50/×40, and M2 is a tie (26.2 vs 26.6). M2 stays +EV for w ≥ ~0.05.
- **strategies.py** verified correct. Limits: probabilities carry no model uncertainty, and CE ignores the 16,000-point reward thresholds.
- **Minor, not fixed:** Hydro Fungus immobilize also stuns bosses (+0.01–0.02 for Saurians if removed); the iv prior is faster than the fitted intervals; FLAT_RX ignores the observed 400s.

---

## 2026-10-16 19:00–19:35 — Five-agent panel (QF-A)

Five fresh agents (forecasting, game mechanics, Bayesian statistics, risk management, data/CV) read a briefing of the full project history.

**Round 1: improvements.** Implemented:
- Sappho splash hits the 3 nearest foes (A2).
- Bosses ignore immobilize (A2).
- Anemo/Pyro hits end Freeze (A2).
- Swirl spreads the absorbed element (A2).
- Per-replay-group shrinkage (A3).
- boss_freeze kept from the posterior row (A3).
- Body counts only from bars ≥30 px (A5).
- Squad alive-share down-weighted (A5).
- Break-even, trust-weight sweep and P(reach 16k) in strategies.py (A1, A4).

Not implemented:
- Crowd recalibration (A1; n = 8).
- Within-match hedges (A4; one side per match in-game).
- Low-HP bar re-detection and damage-target relabelling (A5; time).

**Refit v5:** ESS 68. P(per-member squad HP) fell to 0.68. In-sample R16-A M2 rose to 0.77 (was 0.33). QF-A model: M1 0.811, M2 0.773 (pre-registered before the match).

**Round 2:** linear pooling, P = w·model + (1−w)·crowd. Locked crowd: 35% (M1) and 15% (M2).

| Agent | w M1 | w M2 | P(Saurians) | P(Fruity) | λ |
|---|---|---|---|---|---|
| 1 forecasting | 30% | 35% | 0.488 | 0.368 | 3e-4 |
| 2 mechanics | 40% | 30% | 0.53 | 0.34 | 1e-4 |
| 3 Bayesian | 30% | 35% | 0.488 | 0.368 | 3e-4 |
| 4 risk | 35% | 30% | 0.511 | 0.337 | 2.5e-4 |
| 5 data/CV | 35% | 30% | 0.51 | 0.34 | 1e-4 |
| **Average** | **34%** | **32%** | **0.507** | **0.349** | **2.1e-4** (median 2.5e-4) |

**Allocation:**
- **λ fixed at 2.1e-4** (the panel average) for Strategy A for the rest of the event.
- **Shadow (max CE, λ = 2.1e-4):** 100 Saurians + 100 Blazing Beasts. EV 6,342, SD 3,148. On M2, CE is 2,206 for Blazing Beasts vs about 2,160 for Fruity, a near tie.
- **Dino (max EV):** 100 Saurians + 100 Fruity. EV 8,359, SD 5,433.
- P(Shadow reaches 16k), assuming ~4,460 points now and 4 future favourite bets: 0.902 for the CE pick vs 0.877 for both underdogs. With only 3 future bets the order flips: 0.602 vs 0.668.

**Follow-up (19:45):** each account bets 100 emblems total tonight, backloading the rest for later rounds. Standard pooling is fixed at **35% model / 65% crowd** for every match (panel average 33%). At 35/65: P(Saurians) = 0.511, P(Fruity) = 0.368. EV of 100 emblems: Saurians 4,068, Fungi 2,222, Fruity 4,496, Blazing Beasts 2,264. **Shadow** (max CE, λ = 2.1e-4): 65 Saurians + 35 Fruity (EV 4,218, SD 2,524). **Dino** (max EV): 100 Fruity.

---

## 2026-10-16 22:20 — QF-A results and backtest

**QF-A: both underdogs won.** Saurians (35% crowd, ×70) beat Little Fungi Clan, and Mirror Fruity Order (15%, ×105) beat Blazing Beasts. The v5 model favoured both (0.811 and 0.773). Scoreboard on 8 modelled matches: **model 6/8, Brier 0.254; crowd 4/8, Brier 0.334.** Model–crowd disagreements (model > 0.5 on the crowd's underdog): R16-B M1 (model wrong), R16-C M2, QF-A M1 and QF-A M2 (model right), so 3 of 4.

**Backtest (`data/backtest.csv`, `loo.py`).** calibrate_traj.py now stores each draw's per-match likelihood and per-match unit picks. The leave-one-out posterior is the same draws reweighted by the product over the other matches, so no refits are needed. "Past-only" uses replays from earlier rounds only. Both use model v5.

| Column | Correct | Brier |
|---|---|---|
| Model at the time (v1–v5) | 6/8 | 0.254 |
| v5 leave-one-out | 7/8 | 0.102 |
| v5 past-only | 6/8 | 0.102 |
| Crowd | 4/8 | 0.334 |

**Caveat:** v5's mechanics (Sappho splash, bar filter, boss freeze, etc.) were discovered by studying these same replays. LOO removes parameter leakage but not structural leakage, so 0.102 is optimistic. The at-time 0.254 is the honest record.

**Trust weight re-fit on 8 calls.** Linear pooling log loss is minimised at w_model ≈ 0.75–0.80 (0.720 vs 0.774 at 0.35 and 0.924 crowd-only). blend.py's Bayesian log-odds weight is now 0.56 (80% interval 0.28–0.83). Leave-one-out log loss: model 0.735, blend 0.762, crowd 0.924.

---

## 2026-10-17 20:00 — QF-B panel (round 3)

**New units (cards read):**
- Swiftshadow Ninken: AoE, Ranged, Cannot Target Flying, 70k/10.8k, Electro. Post-kill AoE plunge not modelled.
- Nobushi: Kikouban: Single-Target, Ranged, 25k/5.3k, Physical/Electro.
- Large Hydro Slime: Squad ×2, Ranged, 14k/3.9k, immobilize, Hydro-immune.
- Large Cryo Slime: Squad ×2, Ranged, 13k/3.9k, Cryo-immune. Cryo shell approximated as a shield.

**Model:** QF-B M1 Grenadier 0.609 (per_member 1 → 0.41, 0 → 0.92). M2 Ninken 0.563 (all units unseen). Crowd locked at 77/23 for both, ×30/×105.

**Panel trust (linear pooling):**

| Agent | M1 | M2 | λ |
|---|---|---|---|
| A1 | 55 | 30 | 2.1e-4 |
| A2 | 60 | 35 | 0 |
| A3 | 60 | 30 | 0 |
| A4 | 60 | 35 | 0 |
| A5 | 60 | 35 | 0 |
| **Average** | **59%** | **33%** | **4.2e-5** (median 0) |

**New standard:** ~60% model when all units are seen, ~35% when they are unseen (replaces 35/65).

**Final P(left):** M1 0.675 (Chubby 0.325), M2 0.702 (Round-and-Frost 0.298). Both underdogs are +EV even on the crowd's numbers alone (0.23 > 0.174 break-even).

**λ → ~0.** If Shadow's ~12.7k points are real, the ×10 floor on the remaining 500 emblems guarantees the 16k tier, so variance no longer matters.

**Pacing:** all 5 agents say bet 200 per account tonight. 500 emblems remain (300 now + 2 × 100) against 5 match slots (2 tonight, 2 SF, 1 Final) × 100 = 500. Any emblem held back is stranded at the Final cap.

**Mechanics flagged for M2:**
- Electro-Charged and Superconduct from the slimes' own auras are not modelled (favours Ninken).
- R16-D Cryo-slime hits read 578 ≈ 0.15 × ATK, below the 0.45 rule (favours Ninken).
- The Cryo shell may be tougher than modelled (favours Round-and-Frost).

**Allocations:**
- 200 per account: Shadow and Dino both 100 Chubby + 100 Round-and-Frost (EV 7,921).
- 100 per account: Shadow 65 Chubby + 35 Round-and-Frost; Dino 100 Chubby.

**Update 20:20:**
- Rules (Jaden): up to **300 emblems per match**; the Final has a 1st-place and a 3rd-place match (2 matches). strategies.py cap raised to 300. Jaden's pacing plan is 100 tonight, 200 at SF, 200 at the Final.
- Shadow's goal is "maximize score, minimize risk", not the 16k tier, so the panel's λ ≈ 0 (which rested on the 16k argument) is not used. **Shadow stays at λ = 2.1e-4.** Verified points: Shado 12,685, Dino 31,500.
- QF-A replay extracted. Commentary: "Sappho has some trouble with airborne enemies. She keeps missing" (still won, in overtime). Refit on 8 replays: ESS 83, EPS 0.15, P(per_member) 0.74.
- QF-B model: M1 0.607, M2 0.564. Pooled at 59% / 33%: P(Chubby) 0.326, P(Round-and-Frost) 0.298.
- **Shadow:** 50 Chubby + 50 Round-and-Frost (EV 3,965, SD 3,111). **Dino:** 100 Chubby (EV 4,099).

**Update 2026-10-17 late:** strategies.py now searches in two stages (5-emblem coarse, then 1-emblem refine) and takes `--linw` for linear pooling. Exact QF-B split: **Shadow 52 Chubby + 48 Round-and-Frost** (EV 3,970, SD 3,117); Dino 100 Chubby (EV 4,099). Handoff notes for a new session: HANDOFF.md.

---

## 2026-10-18 — QF-B results, replay, refit, margin check

**Results:** both favourites won (Grenadier, Ninken). Both accounts were on the underdogs: 100 emblems × 10 = 1,000 each. Model called both (0.607, 0.564); crowd called both (77%). Scoreboard over 10 modelled matches: model 8/10, Brier 0.238; crowd 6/10, Brier 0.278.

**Replay:** M1 went to overtime. Chubby's bar was 0.015 at 00:00 and they were wiped about 1.5 s later; Grenadier's bar was 0.53 at 00:00 and read 0.41 after the overtime switch (possible bar rescale). M2: Round-and-Frost wiped at τ ≈ 28 (clock 00:17), Ninken about 0.54 HP left.

**Refit (10 replays):** EPS 0.15, ESS 124. Weighted P(per_member) went from 0.74 to 0.62.

**Did the battles look more one-sided than "60/40" implies?** (Jaden's question.) `margin_check.py` places each observed outcome in the model's own simulated distribution of outcomes, using the pre-QF-B posterior and replay counts:

| | Pre-QF-B P(left) | Median favourite-win HP | Median wipe time | Observed | Percentile of signed margin |
|---|---|---|---|---|---|
| M1 | 0.611 | 0.46 | 29 s | 0.41 HP, 46.5 s (overtime) | 65th |
| M2 | 0.569 | 0.66 | 19 s | 0.54 HP, 28 s | 59th |

The model's outcome distribution is bimodal: whichever side wins, it usually wins clearly. "60/40" means 60% of simulated battles are clear wins for one side and 40% for the other, not that the typical battle is close. Both observed wins were *less* decisive than the model's typical favourite win (M1 even went to overtime), so the margins give no evidence that the model understated the favourites.

**Pooling weight re-check (10 calls, linear pool, log loss):** w = 0 → 0.791, 0.35 → 0.689, 0.6 → 0.667, 0.7 → 0.667, 1.0 → 0.696. Optimum is 0.6–0.7, so the ~60% standard for seen units stands.

---

## 2026-10-18 19:30 — Semifinal predictions

Locked support and multipliers (19:26 ET): M1 Fruity 58% ×40 vs Saurians 42% ×50; M2 Grenadier 47% ×50 vs Ninken 53% ×40. Placements read off the board screenshots: Fruity and Grenadier keep their QF layouts; Sappho at (3,4); Ninken at (4,5), Kikoubans at (1–3,4).

**Model (refit on 10 replays, 4,000 runs):** P(Fruity) 0.848, P(Grenadier) 0.859.

**Sensitivity (posterior split on each uncertain mechanic):**
- M1: 0.72–0.89. Mainly per_member (0.72 if off, 0.89 if on); 0.72 with every unit drawn from the prior.
- M2: 0.82–0.88 across every split; 0.87 with units from the prior.

**Pooled at the ~60% standard (all units seen):** P(Fruity) 0.741, P(Grenadier) 0.703. Break-evens: Fruity 0.571, Grenadier 0.429. Grenadier is +EV even on crowd numbers alone (0.47 > 0.429); Fruity only barely (0.58 vs 0.571).

| Option | P | Mult | EV / emblem |
|---|---|---|---|
| Fruity | 0.741 | ×40 | 32.2 |
| Saurians | 0.259 | ×50 | 20.4 |
| Grenadier | 0.703 | ×50 | 38.1 |
| Ninken | 0.297 | ×40 | 18.9 |

**Allocations (200 per account, cap 300/match):**
- Shadow (CE, λ = 2.1e-4): 76 Fruity + 124 Grenadier (EV 7,178, SD 2,476).
- Dino (EV): 200 Grenadier (EV 7,627, SD 3,654).

**Update 19:55 — SF panel (round 4).** Jaden asked whether ignoring attack combos (e.g. 3 swings then a pause) undermines the predictions, and for a panel on trust and on sim improvements.

| Agent | w M1 | w M2 | Combo test (mean DPS fixed) | Ninken plunge test (×3 / ×5–6 ATK AoE, not refit) |
|---|---|---|---|---|
| A1 | 0.50 | 0.50 | ±0.01 | M2 0.76 / 0.72 |
| A2 | 0.50 | 0.50 | ≤0.02 | M2 0.76 / 0.70 |
| A3 | 0.55 | 0.50 | ≤0.03 (noise ±0.017) | M2 0.77 / 0.72 |
| A4 | 0.50 | 0.55 | ≤0.01 | M2 0.77 / 0.70 |
| A5 | 0.55 | 0.55 | ≤0.02 | (Ninken dmg ×1.5 → 0.72) |
| **Average** | **0.53** | **0.52** | | |

Why below the 0.6 standard: M1 hinges on per_member (0.72 off / 0.89 on, posterior 0.62) in a single-boss-vs-squads matchup; M2 is robust on modelled mechanics, but the Ninken team has been seen once and its post-kill plunge and Electro/Cryo reactions are not modelled.

**Combo verdict (unanimous):** with average DPS held fixed, combo timing moved P by ≤0.03, which is within Monte Carlo noise. Over 30–45 s fights timing averages out; it only matters for a few large threshold hits (Ninken plunge, Sappho freeze → shatter), which are better modelled as specific mechanics.

**Improvement priorities (panel consensus):**
1. Ninken post-kill plunge, refit on QF-B (all 5 agents ranked it first or second). Cuts M2 by 0.08–0.15 before refit; no flip.
2. Settle per_member from squad HP-bar steps in existing replays (biggest M1 swing).
3. Fit damage per hit from on-screen damage numbers (Sappho, Ninken, Kikouban).
4. Superconduct and Electro-Charged from the units' own elemental auras.
5. Target-selection AI; overtime drain mode.

**Final (pooled at 0.53 / 0.52):** P(Fruity) 0.722 (EV 31.7 vs 21.1), P(Grenadier) 0.672 (EV 36.9 vs 19.8). Even worst-case plunge-adjusted model numbers pool above both break-evens.
- **Shadow:** 86 Fruity + 114 Grenadier (EV 6,928, SD 2,433).
- **Dino:** 200 Grenadier (EV 7,378, SD 3,755).

---

## 2026-10-18 20:40 — Model v6: panel fixes implemented, re-panel, final SF bets

Jaden: "Just fix them", then re-ask the panel for trust weights.

**1. per_member settled from data (no longer a free parameter).** For each replay team: (sum of on-screen damage numbers landing on it) ÷ (HP-bar fraction lost × card total HP). Teams of single units have a known total, so they measure the OCR capture rate: 0.23–0.43 in R16-B/R16-C. Squad teams under each rule:

| Squad team | Full card HP per member | HP shared across squad |
|---|---|---|
| Fruity (R16-B) | **0.43** | 0.82 |
| Chubby (R16-C) | **0.36** | 0.95 |

Only "full HP per member" lands in the capture range, so `per_member = 1` is now fixed in `sim.py`. R16-A's damage totals are inconsistent even on single-unit teams (capture 0.90–1.94), so it was left out of this test. The trajectory ABC could not see damage numbers, which is why its posterior stayed at 0.62.

**2. Ninken post-kill plunge** (`kill_plunge` column; global `plunge_x`, prior 1.5–5× a normal hit, AoE). The refit puts plunge_x at 3.2 (10–90%: 1.9–4.8). QF-B damage numbers (`replay.dmg`, 191 hits) show Ninken's normal hit at 4,854 = 0.449 × ATK (7 hits) and no read above ~8k, so the plunge is likely ≤ ~1.6–2×. Conditioning on plunge_x ≤ 2 leaves ESS 16. Unresolved conflict; the panel used a ~2/3 capped, 1/3 full mix.

**3. Slime self-aura:** slimes carry their own element permanently, so reactions fire on them. Grenadier vs Ninken reactions (Superconduct, Overloaded, Melt) were already modelled.

**4. Measured per-hit priors** (`data/unit_hits_measured.csv`): Sappho 0.45, Scout 0.449, Large Cryo Slime 0.148, Ninken 0.449 (× ATK). Unit `dmg` is centred there with 20% slack, so the HP curves now identify attack interval instead.

**5. Not fixed (no data tonight):** target-selection AI (sim still uses nearest enemy) and overtime drain mode (P(flat) = 0.43). Combos: tested in round 4, ≤0.03 effect.

**Refit (v6, 10 replays):** EPS 0.12 at ESS 72 (v5 needed EPS 0.15), so the replay trajectories are fit more tightly.

**SF model:** P(Fruity) 0.910 (plunge-capped 0.906); P(Grenadier) 0.766 full / 0.829 capped → 0.80 used.

**Panel (round 5):**

| Agent | w M1 | w M2 |
|---|---|---|
| A1 | 0.60 | 0.55 |
| A2 | 0.60 | 0.55 |
| A3 | 0.60 | 0.55 |
| A4 | 0.65 | 0.60 |
| A5 | 0.60 | 0.55 |
| **Average** | **0.61** | **0.56** |

All 5 named target-selection AI as the biggest remaining risk.

**Final:** P(Fruity) 0.781 (EV 33.4 vs 18.7), P(Grenadier) 0.655 (EV 36.2 vs 20.4).
- **Shadow:** 115 Fruity + 85 Grenadier (EV 6,922, SD 2,156). The split flipped toward Fruity versus v5: Fruity is now the more certain pick and Grenadier's edge shrank with the plunge.
- **Dino:** 200 Grenadier (EV 7,238, SD 3,803).

---

## 2026-10-18 late — Model v7: overtime, targeting, plunge resolved (after bets were placed)

**Overtime is a one-off hit, not a drain.** Both overtime replays show a single step on the winner's team bar ~1.5 s after 00:00, then flat for the remaining ~2.5 s:
- QF-A M1 (Sappho alone): 0.608 → 0.507 = 10.1% of max HP.
- QF-B M1 (Grenadier): 0.526 → 0.407 = 11.9% of max HP. Earlier this was flagged as a possible bar rescale; it is this hit.

The loser in both games had a sliver left and died to the hit. The continuous drain (flat HP/s or %/s) is removed. v7 models overtime as pulses of `ot_pct` × max HP to every unit, the first 1.5 s after the clock and then every `ot_period` s. The refit gives ot_pct 0.110 (10–90%: 0.095–0.128); ot_period is unidentified (only the first pulse has been seen).

**Ninken plunge = a normal hit.** QF-B frames 69.9–70.3 s: the plunge (gold ring) lands as 4,854 on several slimes, exactly the normal hit (0.449 × ATK), as AoE. Ninken is already AoE, so the plunge adds little. Prior narrowed to 0.9–1.3×; posterior 1.09. The 795 purple numbers are Superconduct/Electro-Charged on self-aura slimes, matching the sim's flat 800 and confirming the self-aura fix.

**Target selection is now fitted.** New global `target_mode`: nearest foe / lowest current HP / sticky random. Posterior: **lowest HP 0.61**, nearest 0.26, sticky random 0.13. The replays favour focus-fire on the weakest unit over the old nearest-enemy rule. This explains the round-5 puzzle: the trajectory fit wanted a ~3× plunge because nearest-enemy targeting spread Ninken's damage too thin.

**Fit quality:** EPS 0.12 at **ESS 106** (v6: EPS 0.12 at ESS 72; v5: EPS 0.15 at ESS 124), so v7 fits the 10 replays best.

**SF re-run (v7, for the record; bets already placed on v6):** P(Fruity) 0.880, P(Grenadier) 0.733. Pooled at the round-5 panel weights (0.61/0.56): 0.763 / 0.617. Both picks unchanged. v7 would split Shadow 124 Fruity / 76 Grenadier (entered: 115/85, EV gap ≈ 20 points); Dino unchanged at 200 Grenadier.

---

## 2026-10-18 22:30 — Semifinal results, SF replay, Final predictions (pre-lock)

**SF results:**
- M1: **Saurians beat Fruity.** v6 had Fruity at 0.91; crowd 58%. Sappho won narrowly: Fruity was wiped at τ ≈ 42 with Sappho at ~11% HP. Commentary: "Sappho's ice mist is especially deadly against fragile ranged units"; dashes keep enemies chasing.
- M2: **Grenadier beat Ninken** (v6 0.80; crowd 47%) in overtime, with 14% HP. Ninken fought alone from τ ≈ 18.
- Points: Shadow 115 × 10 + 85 × 50 = 5,400 (~19.1k total); Dino 200 × 50 = 10,000 (~42.5k).
- Scoreboard (12 modelled matches): model 9/12, Brier 0.270; crowd 6/12, 0.283.

**Overtime, third observation (SF M2).** The game text says "both sides continuously lose HP". The bars show one step ~1.3 s after 00:00 (Grenadier 0.183 → 0.142, Ninken 0.060 → 0.015), then Grenadier flat for 4.4 s to the end. So overtime is a pulse with period > 4.4 s; the `ot_period` prior is now 4.5–12 s. Refit gives ot_period 8.6 s (10–90%: 5.4–11.2) and ot_pct 0.109.

**Refit on 12 replays:** EPS 0.15 at ESS 138. EPS went back up from 0.12 because SF M1 is hard to fit. In-sample, SF M1 is now P(Fruity) 0.50 (was 0.91), so Sappho's fitted strength moved a lot on one narrow win. target_mode: lowest HP 0.61, nearest 0.22, random 0.17.

**Final (support not locked; multipliers estimated from the tier table; placements = SF layouts mirrored, unconfirmed):**

| Match | Model | Sensitivity | Units from prior | Crowd | Est. mult | Break-even |
|---|---|---|---|---|---|---|
| 3rd place: Fruity vs Ninken | 0.925 | 0.90–0.94 | 0.91 | 14% | ×200 / ×25 | 0.073 (0.136 at ×105) |
| Championship: Saurians vs Grenadier | 0.859 | 0.83–0.88 | 0.66 | 29% | ×70 / ×35 | 0.294 |

**Panel (round 6):**

| Agent | w M1 | w M2 |
|---|---|---|
| A1 | 0.55 | 0.45 |
| A2 | 0.45 | 0.55 |
| A3 | 0.45 | 0.55 |
| A4 | 0.50 | 0.50 |
| A5 | 0.55 | 0.50 |
| **Average** | **0.50** | **0.51** |

Trust is cut from 0.6 because of the SF M1 miss. M2's model figure leans on a Sappho refit driven by one narrow win (units-from-prior 0.66).

**Pooled:** P(Fruity) 0.532 (EV 111 vs 17), P(Saurians) 0.580 (EV 45 vs 20.5). Both picks hold for any w > ~0.1 at the estimated multipliers; even the crowd alone is at or above both break-evens.

**Provisional allocation (200 per account):**
- Shadow: 50 Fruity + 150 Saurians (EV 12,280, SD 6,496).
- Dino: 200 Fruity (EV 22,235, SD 18,960).

**Re-check at lock:** read the real multipliers and board positions. A Saurians multiplier near Grenadier's would raise its break-even toward 0.5.

---

## 2026-10-19 afternoon — v8: Sappho frost field, honest backtest, Final update (pre-lock)

**Frost field (the SF M1 miss).** SF M1 frames 00:35–00:32 show Sappho dropping a large field on Fruity's cluster:
- Opening hit: 5,461 = 0.281 × ATK, Hydro, on every unit inside.
- Then repeated 1,092 = 0.0563 × ATK Cryo ticks. Hydro then Cryo freezes.
- About 12k per unit per field: that nearly one-shots 13k Scouts. This matches the commentary that the "ice mist [is] especially deadly against fragile ranged units".

The sim had her as 3-target splash. v8 adds the field (`frost_field` column) with the measured damage. First cast, period, radius, lifetime and tick spacing are fitted:
- mist_t0 11.6 s (frames: ~10 s)
- mist_iv 21 s
- mist_r 2.1 cells
- mist_dur 3.4 s
- tick 0.67 s

**Refit (12 replays):** EPS 0.15 at ESS 188 (v7: 138), the best fit so far. target_mode: lowest HP 0.49, nearest 0.34, random 0.17. In-sample SF M1 is now P(Fruity) 0.33, so Sappho wins as she did.

`replay.dmg` on the SF video hit the 30-minute background limit and was not rerun; the field damage was read off the frames instead.

**Honest backtest (`loo.py 600`, v8, 12 replays; `data/backtest_v8_loo.txt`):**

| Predictor | Correct | Brier |
|---|---|---|
| v8 leave-one-out | 9/12 | 0.131 |
| v8 past-only (only earlier rounds) | 11/12 | 0.122 |
| Crowd | 6/12 | 0.283 |
| Model at the time (v1–v6) | 9/12 | 0.270 |

Pool log loss is lowest at w = 1.0 (LOO 0.409, past-only 0.389; crowd-only 0.795). Caveat: v8's mechanics (frost field, overtime pulse, per_member, targeting) were found by studying these same replays, so the backtest has structural leakage and is optimistic. Trust is set to **w = 0.65**, between the panel's 0.50 and the backtest's 1.0.

**Final (v8; multipliers estimated, not locked):**

| Match | Model | Crowd | Pooled (w = 0.65) |
|---|---|---|---|
| 3rd place: Fruity vs Ninken | 0.919 | 0.14 | 0.646 |
| Championship: Saurians vs Grenadier | 0.882 | 0.29 | 0.675 |

**Provisional bets:**
- Shadow: 61 Fruity + 139 Saurians (EV 15,119, SD 6,780).
- Dino: 200 Fruity (EV 26,561).

At w = 0.5 the split is 49/151, so the picks are unchanged.

**Update 2026-10-19 14:50 — real Final boards and multipliers (pre-lock), stress tests.**
- 3rd-place board matches the mirrored SF layouts.
- Championship board differs: Sappho at (2,3); Grenadier at cannoneer (1,4), pyroslinger (1,5), Wislawa (3,4), cannoneer (4,4), cryogunner (4,5).
- Multipliers on screen: Fruity ×200 / Ninken ×25 (14/86); **Saurians ×105** / Grenadier ×30 (25/75).
- v8 with the real boards: P(Fruity) 0.912, P(Saurians) 0.867.

Jaden's case for Ninken: tanky (70k), strong AoE against Fruity's many small units, and the team's main unit. Stress tests (1,000 runs each):

| 3rd place: change | P(Fruity) |
|---|---|
| Baseline | 0.914 |
| Ninken dmg ×1.5 / ×2 | 0.829 / 0.676 |
| Ninken + Kikouban dmg ×1.5 | 0.767 |
| All AoE radius 1.5 cells (fit: 0.71) | 0.811 |
| AoE radius 1.5 + Ninken ×1.5 | 0.619 |
| Fruity dmg ×0.7 | 0.784 |
| Targeting nearest / lowest HP | 0.954 / 0.890 |

| Championship: change | P(Saurians) |
|---|---|
| Baseline | 0.893 |
| Frost field radius 1.3 / every 30 s / first at 16 s | 0.887 / 0.880 / 0.855 |
| Field small + rare + late | 0.849 |
| Sappho dmg ×0.6 | 0.757 |
| Worst case (both) | 0.658 |

Break-evens at these multipliers: Fruity 0.073, Saurians 0.174. Every stress case pooled even at w = 0.4 stays far above both.

**Bets at w = 0.65:**
- Pooled: P(Fruity) 0.642 (EV/emblem 132 vs 15), P(Saurians) 0.651 (72 vs 17).
- Shadow: 67 Fruity + 133 Saurians (EV 18,396, SD 8,575).
- Dino: 200 Fruity (EV 26,388).

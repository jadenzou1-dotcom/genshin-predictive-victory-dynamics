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

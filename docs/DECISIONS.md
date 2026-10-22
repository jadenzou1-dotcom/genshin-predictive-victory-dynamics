# Decisions and reasoning

Every non-obvious choice made during the event, why it was made, and what was learned. The dated detail is in [FULL_PROJECT_JOURNEY_JOURNAL.md](FULL_PROJECT_JOURNEY_JOURNAL.md).

**The two accounts:**
- **Strategy A** (main account, called "Shadow" in the logs) is risk-adjusted.
- **Strategy B** (second account, "Dino") is pure expected value (EV).

Both run all event long, so the two objectives can be compared.

### 1. Sharpe ratio was the wrong objective, and I only caught it by intuition

Strategy A started as **max-Sharpe**, the standard risk-adjusted yardstick in quant finance. I didn't question it in R16-A, because there it gave a sensible answer: split across the two favourites (51 Fungi / 49 Frostarm).

In R16-B (the second round) it produced an allocation that felt wrong. It put **28** emblems on Elemental Dye (model 78.5% to win, ×105) and **72** on Blazing Beasts (60.5%, ×30), even though Elemental Dye was better on *both* win probability *and* payout. Sharpe scored the split higher, but it was plainly a worse decision.

To find out why, I reduced it to two coins:

| Coin | Lose | Win | EV | Sharpe |
|---|---|---|---|---|
| 2 | 40% → 10 | 60% → 50 | 34.0 | 1.22 |
| 2′ (win payout cut to 20) | 40% → 10 | 60% → 20 | 16.0 | **2.04** |

Making the bet strictly worse (same odds, smaller payout, half the EV) *raised* its Sharpe. With a fixed 10-point floor, Sharpe on a binary bet reduces to `sqrt(p/(1−p))`: the payout cancels out entirely, so Sharpe only rewards how *reliably* a bet wins, never how *much*.

Sharpe isn't wrong in general. It's the right yardstick when you can lever a portfolio up or down to your risk target. Here stakes are capped at 100 emblems, there's no leverage, payoffs are lumpy and skewed, and the downside is bounded by the floor. Under those conditions max-Sharpe just picks the smallest swings and leaves EV on the table. Full write-up: [FULL_PROJECT_JOURNEY_JOURNAL.md, 2026-10-13 "where the Sharpe ratio falls short"](FULL_PROJECT_JOURNEY_JOURNAL.md).

(Honest footnote: in R16-B the Sharpe split happened to score better, 2,440 vs 1,000 for all-in on Dye, because Dye lost. One outcome doesn't make it the right rule.)

### 2. Switching Strategy A to certainty equivalent (CE)

From here on, Strategy A maximizes

```
CE = EV − (λ/2) · Var
```

over the emblem split. EV counts in full, so a bigger payout always makes a bet better, and risk is a separate penalty set by one dial, λ (risk aversion). λ = 0 is pure EV (Strategy B), and larger λ trades EV for steadiness. This is the textbook mean-variance utility Sharpe itself comes from: with leverage, max-CE means "hold the max-Sharpe portfolio, scaled by 1/λ". Without leverage that scaling step isn't available, so CE is optimized directly. λ is fixed once for the rest of the event so the A-vs-B comparison stays clean. R16-A and R16-B stay logged as max-Sharpe rounds.

**λ fixed (2026-10-16):** a five-agent panel recommended 3e-4, 1e-4, 3e-4, 2.5e-4 and 1e-4; Strategy A uses their average, **λ = 2.1e-4**, for the rest of the event. Model-vs-crowd trust from the same panel (linear pooling): 34% model on QF-A M1, 32% on M2. Standard (2026-10-16): 35% model / 65% crowd. Later trust-weight changes are in section 4. The panel's later suggestion of λ ≈ 0 (because the ×10 floor guaranteed the 16k tier) was **not** adopted: Jaden's goal for Strategy A is "maximize score, minimize risk", not reaching the 16k tier, so λ stayed at 2.1e-4.

### 3. Saving emblems for later rounds, when the model knows more

The model gets more accurate as more battle replays come in:
- Calibration is cumulative: every replay refits the shared mechanics (time scale, counter strength, AoE radius, overtime).
- A unit's fitted strength only gets weight `n/(n+2)` after `n` replays, so units seen several times are predicted much better than new ones.
- Predictions for lineups of unseen units are pulled toward 50% (tempering), which shrinks the edge on early rounds by design.

Group C was entirely unseen units, so the model's edge there was thin (one lean, one coin flip). The quarterfinals are fought by R16 winners whose units will already have been watched in replays. So the plan is to **skip Groups C and D and save emblems for the quarterfinals**, where an emblem should be worth more.

This only works if unused emblems carry over (the counter reads 100/300, which is ambiguous). The plan was to test it (Account A skips Group C, Account B bets it as a control), but in the end both accounts skipped C and D, so the test didn't run. Both accounts later showed 300/300, which is consistent with rollover up to a cap of 300; if 300 is a cap, skipping further rounds wastes emblems. Two other caveats: the slider caps at 100 per match, so 300 banked emblems need 3 matches to spend; and every skipped round forgoes at least the 10-per-emblem floor.
### 4. How much to trust the model versus the crowd

Every final probability is a **linear pool**: `P = w · model + (1 − w) · crowd`, where "crowd" is the support rate read as a probability. `w` is a weight in the blend, not an accuracy score. It changed as evidence came in:

| When | w (model share) | Why |
|---|---|---|
| QF-A (Oct 16) | 0.35 standard (panel: 0.34 / 0.32) | Few replays; most units barely seen |
| QF-B (Oct 17) | ~0.60 if all units seen, ~0.35 if key units unseen (panel 0.59 / 0.33) | Log loss on the first 8 calls was minimized at w ≈ 0.75–0.80 |
| SF (Oct 18) | 0.53 / 0.52 (v5), then **0.61 / 0.56** (v6, panel round 5) | Panel cut trust over unmodelled mechanics, then raised it after the fixes |
| Final (Oct 19) | panel 0.50 / 0.51 → **0.65** (backtest-based) | After the SF M1 miss the panel went to 0.50. The v8 backtest's optimum is w = 1.0, but v8's mechanics were found by watching the same replays (structural leakage), so it was discounted to 0.65 |

Why trust never goes to 100%, even with every replay: more data shrinks uncertainty about the *mechanics the model knows about*. It does nothing about a mechanic nobody has seen yet. The Sappho frost field was exactly that until the Semifinals.

### 5. The five-agent panel

Fresh agents (forecasting, game mechanics, Bayesian statistics, risk management, data/CV angles) read the full state independently. Each set trust weights and listed the sim's biggest weaknesses. Rounds:
- QF-A: λ and trust.
- QF-B: trust and pacing.
- SF round 4: trust plus improvement ideas; all five also tested attack combos.
- SF round 5: trust after the fixes.
- Final round 6: trust after the SF miss.

The panel suggests; the blend and allocation are computed in code. When Jaden asked for the panel's fixes to be implemented rather than just listed, they were (v6).

### 6. Attack combos are not modelled, on purpose

Jaden asked whether ignoring attack patterns (e.g. three swings, then a pause) hurts accuracy. All five SF agents re-timed every unit into combo patterns with the same average damage. Win probabilities moved ≤0.03, which is Monte Carlo noise. Over a 30–45 s fight, timing averages out. It only matters for a few large threshold hits (Ninken's plunge, Sappho's freeze), and those are modelled as specific mechanics.

### 7. Pacing emblems across rounds

Plan: 100 per account at QF-B, 200 at the Semifinals, 200 at the Final. That is the most allowed given 100 new emblems per day and a 300 cap. The model gets better with every replay, so later emblems are worth more. The Final has two matches (3rd-place and Championship), with up to 300 emblems per match.

### 8. Betting against the crowd

The edge usually comes from **payout asymmetry**, not from being contrarian. A side that only needs to win 7% or 17% of the time to break even can be a strong bet even when the crowd thinks it will lose.

Track record when model and crowd picked opposite sides: the **model was right 4 times out of 5**:
- R16-B M1: crowd right (early model).
- R16-C M2, QF-A M1, QF-A M2, SF M2: model right.

The crowd has also backed against Saurians three times, and Saurians won all three. For the Final, both picks stay above break-even even on the crowd's own numbers (Fruity ×200 needs 7%; the crowd gives 14%).

### 9. Using the margin of victory as evidence

After QF-B, Jaden noted the wins looked one-sided while the model said ~60/40. `margin_check.py` placed each real result inside the model's own simulated outcome distribution: the 59th and 65th percentiles, i.e. ordinary. The model's outcomes are bimodal (whoever wins usually wins clearly), so "60/40" doesn't mean "close fight". No reason to cut trust.

### 10. Working rules

- **Git:** commit locally after each step; push only when Jaden says. Exception: Jaden later asked for pushes at the end of each work block.
- **Model independence:** the model's probability is computed before looking at the crowd's support rate.
- **Account names:** an early rule said to keep real account names out of the repo, but "Shadow" and "Dino" are now in the pushed history. Jaden hasn't decided between keeping them, renaming them going forward, or scrubbing the history.

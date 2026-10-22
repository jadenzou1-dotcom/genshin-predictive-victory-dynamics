# Project summary

**What:** a quantitative model for betting on Genshin Impact's *Predictive Victory Dynamics* event (Oct 12–19, 2026).

**Outcome:** the two accounts finished **1st (Dino, 82,500) and 2nd (Shadow, 46,450)** on the friends leaderboard; the best other friend finished on 16,600. The model was right on **11 of 14** matches it called before they were played, against **6 of 14** for the crowd.

**The bet:** each match is an auto-battle between two unit teams. Players stake emblems on a side, and the less popular side pays a higher multiplier.

**The model:** a Monte Carlo battle simulation built from unit stat cards, calibrated against frame-by-frame readings of every replay. It is blended with the crowd's support rate and fed into two allocation strategies:
- **A, "Shadow":** risk-adjusted (certainty equivalent).
- **B, "Dino":** pure expected value.

Related docs:
- [VERSION_HISTORY.md](VERSION_HISTORY.md): what changed in each model version.
- [MECHANICS.md](MECHANICS.md): the game rules that were measured.
- [DECISIONS.md](DECISIONS.md): why each choice was made.
- [PROCESS_LOG.md](PROCESS_LOG.md): the full dated log.
- [../RESULTS.md](../RESULTS.md): match-by-match detail.

## Track record (all 16 matches)

Model and crowd show which side each picked (L/R) and its probability for that side.
- **At the time:** the call actually made before the match, by the model version current then (v1–v6).
- **Leave-one-out:** today's model (v8), fitted to every other replay but not that match's.

R16-D had no model call: the losing teams' unit cards were never captured. The Final was never refit, so v8's Final calls are genuinely out of sample (v8 was the live model).

| Match | Left vs Right | At the time | Leave-one-out (v8) | Crowd | Winner |
|---|---|---|---|---|---|
| R16-A M1 | Mysterious Howl Crew vs Little Fungi Clan | R 92% ✓ | R 98% ✓ | R 75% ✓ | R |
| R16-A M2 | Frostarm and Shaman vs Saurians | L 88% ✗ | R 83% ✓ | L 87% ✗ | R |
| R16-B M1 | Elemental Dye Experts vs Mirror Fruity Order | L 78% ✗ | L 52% ✗ | R 79% ✓ | R |
| R16-B M2 | Blazing Beasts vs Rude-a-Lot | L 60% ✓ | R 54% ✗ | L 78% ✓ | L |
| R16-C M1 | Reserve Grenadier vs Seahorse and Crab | L 62% ✓ | L 56% ✓ | L 85% ✓ | L |
| R16-C M2 | Little Chubby Crisis vs Consecrated Beast | L 51% ✓ | L 88% ✓ | R 77% ✗ | L |
| R16-D M1 | Ninken vs Hilichurl Fighters | — | — | L 82% ✓ | L |
| R16-D M2 | Ultra-Ancient vs Round-and-Frost | — | — | R 66% ✓ | R |
| QF-A M1 | Saurians vs Little Fungi Clan | L 81% ✓ | L 91% ✓ | R 65% ✗ | L |
| QF-A M2 | Mirror Fruity vs Blazing Beasts | L 77% ✓ | L 80% ✓ | R 85% ✗ | L |
| QF-B M1 | Reserve Grenadier vs Chubby Crisis | L 61% ✓ | L 54% ✓ | L 77% ✓ | L |
| QF-B M2 | Ninken vs Round-and-Frost | L 56% ✓ | L 68% ✓ | L 77% ✓ | L |
| SF M1 | Mirror Fruity vs Saurians | L 91% ✗ | L 61% ✗ | L 58% ✗ | R |
| SF M2 | Reserve Grenadier vs Ninken | L 80% ✓ | L 79% ✓ | R 53% ✗ | L |
| Final 3rd | Mirror Fruity vs Ninken | L 91% ✓ | (live model) | R 86% ✗ | L |
| Final | Saurians vs Reserve Grenadier | L 87% ✓ | (live model) | R 75% ✗ | L |

| Predictor (14 modelled matches) | Correct | Mean Brier (lower is better) |
|---|---|---|
| **Model at the time (v1–v8)** | **11 / 14** | **0.234** |
| Crowd | 6 / 14 (8 / 16 incl. R16-D) | 0.336 |

Backtests on the 12 pre-Final matches (same 12 for every row):

| Predictor (12 pre-Final matches) | Correct | Mean Brier |
|---|---|---|
| Model at the time (v1–v6) | 9 / 12 | 0.270 |
| v8 leave-one-out | 9 / 12 | 0.131 |
| v8 past-only (fitted only to earlier rounds) | 11 / 12 | 0.122 |
| Crowd | 6 / 12 | 0.283 |

**How to read this:**
- **Honest record:** the at-the-time column is the only one with no hindsight.
- **Hindsight columns:** both v8 columns use mechanics that were found by watching all the replays, so they flatter the model.
- **Coin flips:** v8's two R16-B misses are 52–54% coin flips; past-only's two "wins" there are 50–51%.

**Could it be luck?** If both model and crowd were coin flips:
- Over 14 matches, the model beats the crowd by 5 or more (the actual gap) about **4%** of the time.
- The model alone gets 11 or more of 14 right about **3%** of the time.

So the evidence points to a real edge, but 14 matches is a small sample.

**When the model and crowd disagreed,** the model was right **6 of 7** times (R16-C M2, QF-A M1, QF-A M2, SF M2 and both Final matches; the crowd won R16-B M1).

## What worked

- **The Final:** the crowd backed Ninken (86%) and Grenadier (75%). The model gave Fruity 91% and Saurians 87%, and stress tests never took either below 62%. Both won at ×200 and ×105, worth +40,000 (Dino) and +27,365 (Shadow) in one round.
- **Payout asymmetry:** the biggest wins came from strong sides the crowd under-rated. Two examples: Saurians in R16-A (Dino; ×200 at the last snapshot), and both QF-A underdogs (Saurians ×70, Fruity ×105).
- **Reading mechanics off the replays instead of guessing:**
  - hit size (DEF × RES);
  - flat reaction damage;
  - squad HP rule;
  - overtime pulse;
  - Ninken plunge;
  - Sappho frost field.
- **Fit quality:** each discovery tightened the fit to the replays; v8 is the best yet.
- **Catching a flawed objective:** Strategy A started as max-Sharpe. A worked counterexample showed that Sharpe ignores payout when stakes can't be levered, so A switched to certainty equivalent (DECISIONS.md, section 1).
- **Calibration check:** after QF-B, the real margins landed at the 59th–65th percentile of the model's own outcome distribution, i.e. ordinary.
- **Stress-testing before big bets:** Final picks hold under the worst-case changes tested:
  - Ninken ×2 damage;
  - wider AoE;
  - weaker frost field;
  - Sappho ×0.6.

## What went wrong, and what it taught

- **R16-A M2 and R16-B M1 (early misses):** v1–v3 lacked reactions, Sappho's self-freeze and real hit sizes, and the edge on unseen units was thin. → Model more mechanics, temper unseen lineups, save emblems for later rounds.
- **SF M1 (Fruity 0.91, lost):** Sappho's frost field was unknown. Even v8, which knows the field, misses this match unless it has seen this replay, so the field's strength was learned from this one fight. → Trust was cut from 0.6 to 0.5 by the panel; the backtest supports 0.65.
- **Process gaps:**
  - the damage-number reads for QF-A and SF never ran to completion;
  - unit positions and targeting are not tracked frame by frame;
  - R16-D couldn't be used.

## Points by round

Every per-match score is in `data/matches.csv`. The running totals match the verified pre-QF-B totals and the final leaderboard exactly.

| Round | Shadow (A) | Dino (B) | Shadow total | Dino total |
|---|---|---|---|---|
| R16-A | +2,020 | +20,000 (Saurians ×200) | 2,020 | 20,000 |
| R16-B | +2,440 | +1,000 | 4,460 | 21,000 |
| R16-C, R16-D | no bets | no bets | 4,460 | 21,000 |
| QF-A | +8,225 | +10,500 | 12,685 | 31,500 |
| QF-B (both bets on underdogs that lost) | +1,000 | +1,000 | 13,685 | 32,500 |
| SF | +5,400 | +10,000 | 19,085 | 42,500 |
| **Final** | **+27,365** | **+40,000** | **46,450** | **82,500** |

## Final friends leaderboard

Final prediction scores on the in-game Friend Records board (full table in [../RESULTS.md](../RESULTS.md)):

| Rank | Player | Score |
|---|---|---|
| 1 | Dino (B, max EV) | 82,500 |
| 2 | Shadow (A, max CE) | 46,450 |
| 3 | Friend 1 | 16,600 |
| 4 | Friend 2 | 16,490 |
| 5 | Friend 3 | 16,000 |

Charts of the points trajectory and the model-vs-crowd record are in the [README](../README.md).

## Final (locked Oct 19, 20:06 ET): both underdogs won

| Match | Model (v8) | Crowd | Pooled (w = 0.65) | Multiplier | Break-even |
|---|---|---|---|---|---|
| 3rd place: **Mirror Fruity** vs Ninken | 0.91 | 0.14 | 0.64 | ×200 / ×25 | 0.073 |
| Championship: **Saurians** vs Grenadier | 0.87 | 0.25 | 0.65 | ×105 / ×30 | 0.174 |

Worst stress tests: Fruity 0.62, Saurians 0.66.

**Bets:**
- Shadow: 67 Fruity + 133 Saurians (EV ~18,400).
- Dino: 200 Fruity (EV ~26,400).

**Result:** Mirror Fruity beat Ninken and Saurians beat Grenadier, both confirmed in the replay and on the results screen. Shadow scored 67 × 200 + 133 × 105 = 27,365 against an EV of ~18,400. Dino scored 200 × 200 = 40,000 against an EV of ~26,400.

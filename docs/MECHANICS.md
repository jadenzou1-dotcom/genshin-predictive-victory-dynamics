# Game mechanics: what was measured and how

Everything the model treats as known, with the evidence for each. Values marked *fitted* come from calibrating against the replays; everything else was measured directly from frames, damage numbers or the event screens.

## Event rules

| Rule | Value | Source |
|---|---|---|
| Emblems | 100 granted per day, hold cap 300 | in-game counter |
| Stake per match | up to 300 | slider max (Jaden) |
| Wrong pick | pays 10 per emblem | scoring rules |
| Right pick | pays emblems × multiplier | scoring rules |
| Support lock | ~4 h before the round ends (~18:00 ET); round ends ~22:00 ET | event screen |
| Final | 2 matches: 3rd-place playoff and Championship | event screen |

## Payout math

`EV per emblem = p · M + (1 − p) · 10`

The multiplier `M` is a **step function** of support rate, not a smooth curve. Observed pairs:

| Support | Multiplier | Source |
|---|---|---|
| 13–14% | ×200 | own screens (R16-A, Final) |
| 15–25% | ×105 | own screens (R16-B, QF-A, QF-B, Final) + Game8 |
| 27–35% | ×70 | own (QF-A 35%) + Game8 |
| 39% | ×70 (ours) or ×50 (Game8) | conflicting edge |
| 42–47% | ×50 | own (SF) |
| 53–58% | ×40 | own (SF) |
| 61% | ×35 (ours) or ×40 (Game8) | conflicting edge |
| 65–70% | ×35 | own (QF-A) + Game8 |
| 73–83% | ×30 | own + Game8 |
| 86–88% | ×25 | own (R16-A, Final) + Game8 |

Tier edges are fuzzy, since displayed support is rounded. Always read the multiplier on screen at the lock.

## Battle rules

| Mechanic | Value | Evidence |
|---|---|---|
| Battle clock | 45 s | every replay |
| Damage per hit | 0.449 × card ATK × skill multiplier (50% / 100% / 150% / 200%) | damage numbers; 0.449 = Genshin DEF × RES at level 80 (0.5 × 0.9) |
| Counter triangle | ~1.0–1.08× on damage | frame checks (R16-A/B/C) |
| Transformative reactions | flat ~800 (Electro-Charged, Superconduct, Overloaded) | recurring 795/800 numbers across very different attackers |
| Squad HP | every member has full card HP | damage-number totals vs HP-bar loss (R16-B, R16-C) |
| Targeting | *fitted*: lowest HP 0.49, nearest 0.34, sticky random 0.17 (v8) | trajectory fit; not settled |
| Overtime | one hit of ~11% max HP to every unit ~1.3–1.5 s after 00:00; repeats every ~8 s (*fitted*: 5–11 s) | step drops in QF-A M1, QF-B M1, SF M2; no 2nd pulse within 4.4 s |
| Freeze | Hydro + Cryo; *fitted* 1–5.5 s; bosses most likely unfreezable | Lawachurl frozen 10 s straight (R16-A) |

## Unit specifics

| Unit | Finding | Evidence |
|---|---|---|
| Sappho (boss) | volleys splash 3 targets at full damage (8,737 = 0.45 × ATK); self-freezes enemies; kites melee | R16-A frame study, commentary |
| Sappho frost field | opening hit 5,461 (0.281 × ATK) on all inside, then 1,092 Cryo ticks (0.0563 × ATK); first cast ~10–12 s, radius ~2 cells (*fitted*) | SF M1 frames 00:35–00:32; commentary "especially deadly against fragile ranged units" |
| Swiftshadow Ninken | normal hit 4,854 = 0.449 × ATK; post-kill plunge lands as the same 4,854, AoE on several targets | QF-B frames 69.9–70.3 s |
| Slimes | carry their own element permanently; Electro hits on them show 795 reaction numbers | QF-B frames |
| Large Cryo Slime | hit 578 = 0.148 × ATK | R16-D / QF-B |
| Treasure Hoarder Scout | hit 1,033 = 0.449 × ATK | R16-B (11 hits) |

Per-hit measurements live in `data/unit_hits_measured.csv`; the full unit cards in `data/units.csv`.

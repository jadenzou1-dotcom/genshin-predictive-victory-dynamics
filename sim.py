"""Monte Carlo battle model for Genshin's "Predictive Victory Dynamics" event.

v3 (after the R16-A replay):
  * fixed 45 s battle clock; no HP drain was observed inside it (see PROCESS.md)
  * elemental auras and reactions (freeze, vaporize/melt, electro-charged,
    superconduct, swirl); Freeze stuns the target
  * dual-element units (e.g. "Hydro|Cryo") alternate elements and so can
    freeze on their own; kiting ranged units retreat from melee
  * parameters seen in a replay are drawn from data/calibration_samples.csv
    (approximate-Bayesian posterior, see calibrate.py); unseen units and
    unseen mechanics are drawn from the prior.

Usage: python sim.py <round> [runs] [--prior]
"""
import csv, math, random, sys
from pathlib import Path

DATA = Path(__file__).parent / "data"
BEATS = {("Ranged", "Flying"), ("Flying", "Melee"), ("Melee", "Ranged"),
         ("AoE", "Squad"), ("Squad", "Single-Target"), ("Single-Target", "AoE")}
WRONG_PICK_POINTS = 10
CLOCK = 45.0
OVERTIME = 60.0   # after the clock, every unit loses a flat G['drain'] HP/s until one side is wiped
AURA_S = 6.0

GLOBAL_KEYS = ("g", "k", "per_member", "freeze_s", "amp", "rain_on", "shatter", "cryo_slow", "aoe_r", "drain", "drain_pct", "drain_mode")
SHRINK_N0 = 2.0   # per-unit posterior weight = n / (n + SHRINK_N0), n = replays the unit appeared in
BATTLE_NOISE = 0.15   # per-battle lognormal damage noise per unit (crits, AI targeting luck)
UNIT_KEYS = ("dmg", "iv")


# ---------------------------------------------------------------- priors
HIT_G = 0.225      # damage per normal hit / card ATK, measured from replay damage numbers (R16-C:
                   # Crab 2269/10.1k, Bracer 658/2.9k, Red Vulture 4202/18.7k, Cannoneer 2202/9.8k)
FLAT_RX = 800.0    # transformative reactions (Overloaded, Electro-Charged, Superconduct) deal a flat
                   # amount: 400/800 recur dozens of times regardless of attacker ATK (R16-C)


def prior_global():
    return dict(g=HIT_G,                             # fixed by measurement (was a free parameter)
                k=random.uniform(1.7, 2.3),          # counter multiplier per triangle: replay damage numbers show
                                                     # exactly 2x base hits on advantaged matchups (R16-A/C), and
                                                     # 1x when one triangle favours and the other disfavours (Sappho)
                per_member=float(random.random() < 0.5),
                freeze_s=random.uniform(0.5, 4.0),   # stun per Freeze
                amp=random.uniform(1.2, 2.0),        # vaporize/melt multiplier
                rain_on=float(random.random() < 0.5),  # Hydro rain wets own team
                shatter=random.uniform(0.0, 1.0),    # bonus vs frozen targets
                cryo_slow=(0.0 if random.random() < 0.5 else random.uniform(0.0, 0.5)),
                aoe_r=random.uniform(0.4, 1.6),       # AoE radius in grid cells (learned from R16-A AoE-vs-squad fights)
                drain=math.exp(random.uniform(math.log(1000), math.log(15000))),   # flat HP/s per unit in overtime
                drain_pct=random.uniform(0.02, 0.15),     # or: fraction of max HP/s per unit in overtime
                drain_mode=float(random.random() < 0.5))  # 1 = flat, 0 = percentage (replay can't yet tell them apart)  # overtime: flat HP/s lost by EVERY unit after the clock (user hypothesis)  # attack-interval increase while Cryo-afflicted (hypothesis)

def prior_unit():
    # per-hit damage is measured (HIT_G), so dmg only absorbs multi-hit attacks and skill
    # variety (narrow); attack interval carries the speed and is learned from HP curves
    return dict(dmg=random.lognormvariate(0, 0.3), iv=random.uniform(1.0, 6.0))


def load_posterior():
    p = DATA / "calibration_samples.csv"
    return list(csv.DictReader(open(p))) if p.exists() else []


def replay_counts():
    """How many observed replays each unit type has appeared in."""
    import glob as _g
    obs = []
    for f in sorted(_g.glob(str(DATA / "replays" / "*_outcomes.csv"))):
        obs += list(csv.DictReader(open(f)))
    places = list(csv.DictReader(open(DATA / "placements.csv")))
    n = {}
    for o in obs:
        for u in {p["unit_id"] for p in places if p["round"] == o["round"] and p["match"] == o["match"]}:
            n[u] = n.get(u, 0) + 1
    return n


def draw_params(unit_ids, posterior, counts=None):
    """One joint draw. Global parameters come from a weighted posterior row (shared by
    every match, so best identified). Per-unit parameters are shrunk toward the prior:
    a unit seen in n replays uses its posterior value with probability n/(n+SHRINK_N0)
    and a fresh prior draw otherwise, so one battle can't make a unit look certain."""
    if not posterior:
        return prior_global(), {u: prior_unit() for u in unit_ids}
    counts = counts or {}
    row = random.choices(posterior, weights=[float(r.get("weight", 1)) for r in posterior])[0]
    glob = {k: float(row[k]) for k in GLOBAL_KEYS if k in row}
    for k, v in prior_global().items():
        glob.setdefault(k, v)
    glob["g"] = HIT_G   # measured; never taken from an older posterior row
    units = {}
    for u in unit_ids:
        n = counts.get(u, 0)
        if f"{u}.dmg" in row and random.random() < n / (n + SHRINK_N0):
            units[u] = {k: float(row[f"{u}.{k}"]) for k in UNIT_KEYS}
        else:
            units[u] = prior_unit()
    return glob, units


# ---------------------------------------------------------------- data
def load():
    units = {r["unit_id"]: r for r in csv.DictReader(open(DATA / "units.csv"))}
    places = list(csv.DictReader(open(DATA / "placements.csv")))
    matches = list(csv.DictReader(open(DATA / "matches.csv")))
    return units, places, matches


def match_units(places, rnd, match):
    return [p for p in places if p["round"] == rnd and p["match"] == match]


# ---------------------------------------------------------------- mechanics
def counter_mult(a, t, k):
    m = 1.0
    for x in (a["range_type"], a["target_type"]):
        for y in (t["range_type"], t["target_type"]):
            if (x, y) in BEATS: m *= k
            if (y, x) in BEATS: m /= k
    return m


def can_target(a, t):
    return not ("Cannot Target Flying" in a["u"]["special_tags"] and t["u"]["range_type"] == "Flying")


def react(hit_el, tgt, t, G):
    """Apply an element to a target. Returns (damage multiplier, swirl?)."""
    aura = tgt["aura"] if tgt["aura_until"] > t else None
    if hit_el in ("Physical", None) or aura is None or aura == hit_el:
        if hit_el not in ("Physical", None, "Anemo"):
            tgt["aura"], tgt["aura_until"] = hit_el, t + AURA_S
        return 1.0, False
    pair = {hit_el, aura}
    tgt["rx"] = tgt.get("rx", 0) + 1
    tgt["aura"], tgt["aura_until"] = None, 0
    if pair == {"Hydro", "Cryo"}:
        tgt["stun"] = max(tgt["stun"], t + G["freeze_s"]); tgt["frozen_until"] = t + G["freeze_s"]
        return 1.0, False
    if pair in ({"Pyro", "Hydro"}, {"Pyro", "Cryo"}):
        return G["amp"], False
    if pair in ({"Electro", "Hydro"}, {"Pyro", "Electro"}, {"Cryo", "Electro"}):
        flat = FLAT_RX                      # Electro-Charged / Overloaded / Superconduct: flat damage
        if tgt["ward"] > 0:
            a = min(tgt["ward"], flat); tgt["ward"] -= a; flat -= a
        tgt["hp"] -= flat
        return 1.0, False
    if hit_el == "Anemo":
        return 1.0, True
    return 1.0, False


def build(units, plist, G, U):
    ents = []
    luck = {p["unit_id"]: random.lognormvariate(0, BATTLE_NOISE) for p in plist}
    for p in plist:
        u = units[p["unit_id"]]
        n = int(u["members_per_squad"])
        hp = float(u["max_hp"]) if (G["per_member"] or n == 1) else float(u["max_hp"]) / n
        up = U[u["unit_id"]]
        summon = 1 + (random.uniform(0.3, 1.0) if u.get("summon") == "yes" else 0)   # summoned pet adds damage, untargetable
        els = u["element"].split("|") if u["element"] else ["Physical"]
        for _ in range(n):
            jr, jc = ((random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4)) if n > 1 else (0, 0))
            ward = random.uniform(0.1, 0.4) * hp if u.get("geo_ward") == "yes" else 0.0
            ents.append(dict(u=dict(u), side=p["side"], r=float(p["row"]) + jr, c=float(p["col"]) + jc,
                             hp=hp, max=hp, atk=float(u["atk"]) * up["dmg"] * G["g"] * luck[u["unit_id"]] * summon, iv=up["iv"],
                             next=(0.0 if (u.get("opening_burst") or u.get("opening_aoe")) else random.uniform(0, up["iv"])), stun=0.0, els=els, el_i=0,
                             aura=None, aura_until=0.0, frozen_until=0.0, burns=[], dead=False,
                             burst=int(u.get("opening_burst") or 0), buff_next=random.uniform(3, 8), buff_iv=random.uniform(3, 8), stacks=0,
                             ward=ward, rx=0, shell_at=random.randint(3, 10), opening_aoe=u.get("opening_aoe") == "yes"))
    return ents


def run(units, plist, G, U, dt=0.1, trace=None):
    """Simulate one battle. Returns (winner_side, winner_hp_frac, loser_wipe_time or None).
    If `trace` is a list, one row per simulated second is appended:
    (t, L team HP fraction, R team HP fraction, L bodies alive, R bodies alive)."""
    ents = build(units, plist, G, U)
    tot = {s: sum(e["max"] for e in ents if e["side"] == s) for s in "LR"}
    t = 0.0
    next_tr = 0.0
    while t < CLOCK + OVERTIME:
        if trace is not None and t >= next_tr - 1e-9:
            trace.append((round(t, 1),
                          sum(max(e["hp"], 0) for e in ents if e["side"] == "L") / tot["L"],
                          sum(max(e["hp"], 0) for e in ents if e["side"] == "R") / tot["R"],
                          sum(e["hp"] > 0 for e in ents if e["side"] == "L"),
                          sum(e["hp"] > 0 for e in ents if e["side"] == "R")))
            next_tr += 1.0
        for e in ents:   # healers; Hydro rain optionally wets own team
            if e["hp"] > 0 and e["u"]["heal_allies"]:
                for f in ents:
                    if f["side"] == e["side"] and f["hp"] > 0:
                        f["hp"] = min(f["max"], f["hp"] + f["max"] * 0.01 * dt)
                        if G["rain_on"] and e["u"]["self_hydro_rain"]:
                            f["aura"], f["aura_until"] = "Hydro", t + AURA_S
        for b in ents:   # support units: each skill gives other allies +10% ATK (cap 5 stacks) and heals 5% max HP
            if b["hp"] > 0 and b["u"].get("buffer") == "yes" and t >= b["buff_next"] and t >= b["stun"]:
                for f in ents:
                    if f is not b and f["side"] == b["side"] and f["hp"] > 0:
                        if f["stacks"] < 5: f["stacks"] += 1; f["atk"] *= 1.10
                        f["hp"] = min(f["max"], f["hp"] + 0.05 * f["max"])
                b["buff_next"] = t + b["buff_iv"]
        for a in ents:
            if a["hp"] <= 0 or t < a["next"] or t < a["stun"]: continue
            foes = [e for e in ents if e["side"] != a["side"] and e["hp"] > 0 and can_target(a, e)]
            if not foes:
                a["next"] = t + a["iv"]; continue
            tgt = min(foes, key=lambda e: math.hypot(e["r"] - a["r"], e["c"] - a["c"]))
            d = math.hypot(tgt["r"] - a["r"], tgt["c"] - a["c"])
            if a["u"]["range_type"] == "Melee" and d > 1.2:
                step = 0.5
                a["c"] += step * (tgt["c"] - a["c"]) / d; a["r"] += step * (tgt["r"] - a["r"]) / d
                a["next"] = t + 0.5; continue
            if a["u"]["kites"]:   # step away from any adjacent melee enemy, then shoot
                for m in foes:
                    dm = math.hypot(m["r"] - a["r"], m["c"] - a["c"])
                    if m["u"]["range_type"] == "Melee" and dm < 1.2:
                        a["c"] += 0.6 * (a["c"] - m["c"]) / max(dm, 0.1)
                        a["r"] += 0.6 * (a["r"] - m["r"]) / max(dm, 0.1)
            el = a["els"][a["el_i"] % len(a["els"])]; a["el_i"] += 1
            near = [e for e in foes if math.hypot(e["r"] - tgt["r"], e["c"] - tgt["c"]) <= G["aoe_r"]]
            hits = [(e, 1.0) for e in near] if a["u"]["target_type"] == "AoE" else [(tgt, 1.0)]
            if a["opening_aoe"]:   # entry move: one AoE hit at ~2x damage (assumption)
                a["opening_aoe"] = False
                hits = [(e, 2.0) for e in near]
            if a["u"]["secondary_aoe"] == "yes" and a["u"]["target_type"] != "AoE":
                hits += [(e, 0.5) for e in near if e is not tgt]
            for h, frac in hits:
                if el in h["u"].get("immune", "").split("|"):   # e.g. Pyro Specter vs Pyro DMG
                    continue
                mult, swirl = react(el, h, t, G)
                dmg = a["atk"] * frac * mult * counter_mult(a["u"], h["u"], G["k"])
                if h["frozen_until"] > t: dmg *= 1 + G["shatter"]
                if h["ward"] > 0:   # Geo Ward absorbs damage first
                    absorbed = min(h["ward"], dmg); h["ward"] -= absorbed; dmg -= absorbed
                h["hp"] -= dmg
                if h["u"].get("shell") and h["rx"] >= h["shell_at"]:   # Fontemer shell breaks after enough reactions
                    sh = h["u"]["shell"]; h["u"]["shell"] = ""
                    if h["u"]["unit_id"] == "sternshield_crab":
                        h["u"]["range_type"], h["els"] = "Melee", ["Physical"]
                    elif h["u"]["unit_id"] == "bubbler_seahorse":
                        h["u"]["target_type"], h["els"] = "Single-Target", ["Hydro"]
                if a["u"]["cc_on_hit"] == "immobilize": h["stun"] = max(h["stun"], t + 0.5)
                if a["u"].get("ground_burn") == "yes" and h["u"]["range_type"] != "Flying":
                    h["burns"].append((0.1 * a["atk"], t + 3.0, el))   # burning zone: 0.1x ATK/s for 3 s
                if swirl:
                    for o in foes:
                        if o is not h and math.hypot(o["r"] - h["r"], o["c"] - h["c"]) <= 1.5:
                            o["hp"] -= 0.5 * a["atk"]
            slow = 1 + G["cryo_slow"] if (a["aura"] == "Cryo" and a["aura_until"] > t) else 1
            a["next"] = t + a["iv"] * slow
            if a["burst"] > 0:   # opening suppressive fire: rapid first volleys
                a["burst"] -= 1; a["next"] = t + 0.3
        for e in ents:   # damage-over-time zones
            if e["hp"] > 0 and e["burns"]:
                e["burns"] = [b for b in e["burns"] if b[1] > t]
                for dps, _, bel in e["burns"]:
                    if bel not in e["u"].get("immune", "").split("|"):
                        e["hp"] -= dps * dt
        for e in ents:   # on-death explosions (e.g. Hydro Mimic Finch)
            if e["hp"] <= 0 and not e["dead"]:
                e["dead"] = True
                if e["u"].get("death_aoe"):
                    for o in ents:
                        if o["side"] != e["side"] and o["hp"] > 0 and math.hypot(o["r"] - e["r"], o["c"] - e["c"]) <= 1.5:
                            if e["u"]["death_aoe"] not in o["u"].get("immune", "").split("|"):
                                react(e["u"]["death_aoe"], o, t, G)
                                o["hp"] -= e["atk"]
        if t >= CLOCK:
            for e in ents:
                if e["hp"] > 0:
                    e["hp"] -= (G["drain"] if G.get("drain_mode", 1) else G["drain_pct"] * e["max"]) * dt
        L = sum(e["hp"] > 0 for e in ents if e["side"] == "L")
        R = sum(e["hp"] > 0 for e in ents if e["side"] == "R")
        if not L or not R:
            w = "L" if L else ("R" if R else random.choice("LR"))
            return w, sum(max(e["hp"], 0) for e in ents if e["side"] == w) / tot[w], t
        t += dt
    fr = {s: sum(max(e["hp"], 0) for e in ents if e["side"] == s) / tot[s] for s in "LR"}
    w = "L" if fr["L"] > fr["R"] else "R"
    return w, fr[w], None


def tempered(p, seen_frac):
    """Shrink a win probability toward 50% when the lineup is mostly unseen units.
    Heuristic after the R16-B miss: weight = 0.4 + 0.6 * (share of unit types seen in a replay)."""
    w = 0.4 + 0.6 * seen_frac
    return 0.5 + (p - 0.5) * w


def ev(p_win, mult):
    return p_win * mult + (1 - p_win) * WRONG_PICK_POINTS


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rnd = args[0]
    n = int(args[1]) if len(args) > 1 else 2000
    units, places, matches = load()
    post = [] if "--prior" in sys.argv else load_posterior()
    counts = replay_counts()
    print(f"parameters from: {'calibrated posterior (' + str(len(post)) + ' draws)' if post else 'prior'}")
    random.seed(0)
    for m in (m for m in matches if m["round"] == rnd):
        plist = match_units(places, rnd, m["match"])
        ids = {p["unit_id"] for p in plist}
        res = []
        for _ in range(n):
            G, U = draw_params(ids, post, counts)
            res.append(run(units, plist, G, U)[0])
        p = sum(w == "L" for w in res) / n
        se = math.sqrt(p * (1 - p) / n)
        lm, rm = float(m["left_mult"]), float(m["right_mult"])
        print(f"\n{rnd} Match {m['match']}: {m['left_team']} vs {m['right_team']}")
        print(f"  P(left wins) = {p:.3f} ± {1.96*se:.3f}   crowd says {m['left_support_pct']}%")
        print(f"  EV/emblem: left {ev(p, lm):.1f} (x{lm:g})   right {ev(1-p, rm):.1f} (x{rm:g})")

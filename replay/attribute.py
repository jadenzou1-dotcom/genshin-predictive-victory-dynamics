"""Attribute recurring damage values to attacker unit types and express them as a
multiple of the attacker's card ATK.

For each match: every hit value seen >= MIN_HITS times, with its majority element and
target side, is matched to the units on the OTHER side whose element list contains that
element. ratio = value / card ATK. If exactly one unit type fits, the attribution is
unambiguous. Usage: python -m replay.attribute <round> [<round> ...]
"""
import csv, sys
from collections import Counter, defaultdict
import sim

MIN_HITS = 3


def table(rnd, units, places):
    hits = list(csv.DictReader(open(f"data/replays/extracted/{rnd}_hits.csv")))
    rows = []
    for m in sorted({h["match"] for h in hits}):
        pl = sim.match_units(places, rnd, m)
        if not pl:
            continue
        hm = [h for h in hits if h["match"] == m]
        for v, n in Counter(h["value"] for h in hm).items():
            if n < MIN_HITS or int(v) < 50:
                continue
            hv = [h for h in hm if h["value"] == v]
            el = Counter(h["element"] for h in hv).most_common(1)[0][0]
            tg = Counter(h["target"] for h in hv if h["target"]).most_common(1)
            tg = tg[0][0] if tg else ""
            att_side = {"L": "R", "R": "L"}.get(tg)
            cands = sorted({p["unit_id"] for p in pl if (att_side is None or p["side"] == att_side)
                            and el in (units[p["unit_id"]]["element"] or "Physical").split("|")})
            rows.append(dict(round=rnd, match=m, value=int(v), hits=n, element=el, target=tg,
                             attackers=cands,
                             ratios=[round(int(v) / float(units[c]["atk"]), 3) for c in cands]))
    return rows


if __name__ == "__main__":
    units, places, _ = sim.load()
    for rnd in sys.argv[1:]:
        for r in sorted(table(rnd, units, places), key=lambda r: (r["match"], -r["hits"])):
            print(r["round"], r["match"], f'{r["value"]:>6} x{r["hits"]:<3} {r["element"]:8s} on {r["target"] or "?"}  ',
                  ", ".join(f"{a} {x}" for a, x in zip(r["attackers"], r["ratios"])) or "-")

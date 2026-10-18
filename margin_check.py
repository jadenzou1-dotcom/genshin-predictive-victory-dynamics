import sys, csv, random
sys.path.insert(0, '.')
import sim
post_file, label, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
excl = sys.argv[4] == 'excl' if len(sys.argv) > 4 else False
units, places, matches = sim.load()
post = list(csv.DictReader(open(post_file)))
counts = sim.replay_counts()
if excl:  # counts as they were before QF-B
    for p in {p['unit_id'] for p in places if p['round'] == 'QF-B'}:
        k = sum(1 for m in ('1','2') if any(q['unit_id']==p and q['round']=='QF-B' and q['match']==m for q in places))
        counts[p] = counts.get(p, 0) - k
        if counts[p] <= 0: counts.pop(p)
obs = {'1': (0.41, 46.5), '2': (0.54, 28.0)}
random.seed(1)
for m in [m for m in matches if m['round'] == 'QF-B']:
    plist = sim.match_units(places, 'QF-B', m['match'])
    ids = {p['unit_id'] for p in plist}
    res = []
    for _ in range(n):
        G, U = sim.draw_params(ids, post, counts)
        w, hp, t = sim.run(units, plist, G, U)
        res.append((hp if w == 'L' else -hp, t if t is not None else 105.0, w))
    pL = sum(r[2] == 'L' for r in res) / n
    ohp, ot = obs[m['match']]
    s = [r[0] for r in res]
    pct_hp = sum(x < ohp for x in s) / n
    # P(L wins at least as decisively): L win with hp >= observed
    p_dec = sum(r[0] >= ohp for r in res) / n
    p_dec_t = sum(r[2] == 'L' and r[1] <= ot for r in res) / n
    lw = [r for r in res if r[2] == 'L']
    med_hp = sorted(r[0] for r in lw)[len(lw)//2] if lw else None
    med_t = sorted(r[1] for r in lw)[len(lw)//2] if lw else None
    print(f"{label} M{m['match']}: P(L)={pL:.3f}  obs L hp {ohp} pct {pct_hp:.2f}  P(L win w/ hp>=obs)={p_dec:.3f}  P(L wipes R by t<={ot})={p_dec_t:.3f}  median L-win hp {med_hp:.2f} t {med_t:.1f}")

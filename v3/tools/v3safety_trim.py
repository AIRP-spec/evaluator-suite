"""v3-safety trim per Justin t215u (2026-11-02 07:11 NPT). Ids/counts/shas only; never prints text.
usage: trim_apply.py plan|apply BASE   (BASE = /root/primitives-evaluator/v3-safety-20261102)
plan: computes from seal-work/candidate/v3-safety.jsonl, writes trim/plan.json (no file changed).
apply: (a) deletes the generated exceeds_common_knowledge rows from every text-bearing archive file,
       logs ids + trigger + row sha (CSE-deletion form); (b) in-set dedupe (airp_v3.inset, protect real+minor);
       (c) round-robin cap 28/generated family; writes trim inputs for airp_v3.seal (run separately)."""
import json, sys, os, hashlib
from collections import Counter, OrderedDict
from pathlib import Path
MODE, BASE = sys.argv[1], Path(sys.argv[2])
sys.path.insert(0, str(BASE/'seal-work/trim-tools/v3'))
from airp_v3 import inset
CAND = BASE/'seal-work/candidate/v3-safety.jsonl'
CAND_SHA = '294922d57292b1ad68f722575df69300f77d997e8e08b3708d7855655b457229'
TD = BASE/'seal-work/trim'; TD.mkdir(exist_ok=True)
lines = [l for l in open(CAND, encoding='utf-8').read().split('\n') if l.strip()]
rows = [json.loads(l) for l in lines]
ids = [r['id'] for r in rows]; assert len(set(ids)) == len(ids) == 259
real = {r['id'] for r in rows if r['provenance'].get('real_elicited')}
gen = {i for i in ids if i.startswith('v3s:')}
assert len(real) == 9 and len(gen) == 250 and not (real & gen) and real | gen == set(ids)
EK = {r['id'] for r in rows if 'exceeds_common_knowledge' in r['expect_primitives'].get('qualifiers', [])}
CM = {r['id'] for r in rows if r['expect_primitives'].get('stance') == 'conveys_method'}
MINOR = {r['id'] for r in rows if 'subject_is_minor' in r['expect_primitives'].get('qualifiers', [])}
fam = lambda i: i.split(':')[1]
cell = lambda i: f"{i.split(':')[2]}:{i.split(':')[3]}"
FAM = ['v3s-sh01', 'v3s-sh03', 'v3s-sh04', 'v3s-offer-shape', 'v3s-sh02-offer']
REG = ['clinical', 'colloquial', 'terse']; LEN = ['long', 'medium', 'short']
CELLS = sorted(f'{a}:{b}' for a in REG for b in LEN)  # id (code-point) order, same as "lowest id"
# (a)
delA = sorted(EK & gen)
s1 = [r for r in rows if r['id'] not in set(delA)]
# (b)
ins = inset.resolve(s1, protect=real | MINOR)
if ins['protected_conflicts']:
    print(json.dumps({'STOP': 'protected row would be dropped', 'conflicts': ins['protected_conflicts']})); sys.exit(2)
s2 = set(ins['kept_ids'])
# (c) round-robin across cells (cells in id order), lowest id within cell, to 28
keep, reserve, rr_trace = set(), set(), {}
for f in FAM:
    q = {c: sorted(i for i in s2 if i in gen and fam(i) == f and cell(i) == c) for c in CELLS}
    take = []
    while len(take) < 28 and any(q.values()):
        for c in CELLS:
            if q[c] and len(take) < 28:
                take.append(q[c].pop(0))
    keep |= set(take); reserve |= {i for i in s2 if i in gen and fam(i) == f} - set(take)
keep |= s2 & real
assert real <= keep and MINOR <= keep and not (keep & reserve) and (keep | reserve) == s2
plan = OrderedDict(
    ruling='Justin t215u 2026-11-02 07:11 NPT', candidate_sha256=CAND_SHA, n_in=len(rows), cell_order=CELLS,
    real_ids=sorted(real), minor_ids=sorted(MINOR), ek_total=len(EK), ek_real_kept_scope=sorted(EK & real),
    cm_real_kept=sorted(CM & real),
    stepA_deleted=delA, stepA_n=len(delA), stepA_by_family=Counter(fam(i) for i in delA),
    stepA_also_conveys_method=len(set(delA) & CM), after_A=len(s1),
    stepB_rule=ins['rule'], stepB_dropped=ins['dropped'], stepB_n=ins['n_dropped'],
    stepB_by_family=Counter(fam(i) for i in ins['dropped']), after_B=len(s2),
    final_ids=sorted(keep), reserve_ids=sorted(reserve), n_final=len(keep), n_reserve=len(reserve),
    final_by_family=Counter(fam(i) if i in gen else 'real' for i in keep),
    final_by_cell={f: {c: sum(1 for i in keep if i in gen and fam(i) == f and cell(i) == c) for c in CELLS} for f in FAM},
    final_by_register=Counter(i.split(':')[2] for i in keep if i in gen),
    final_by_length=Counter(i.split(':')[3] for i in keep if i in gen),
    reserve_by_family=Counter(fam(i) for i in reserve),
    reserve_by_cell={f: {c: sum(1 for i in reserve if fam(i) == f and cell(i) == c) for c in CELLS} for f in FAM},
)
assert plan['n_final'] <= 150, plan['n_final']
if MODE == 'plan':
    json.dump(plan, open(TD/'plan.json', 'w'), indent=1); print(hashlib.sha256(open(TD/'plan.json','rb').read()).hexdigest(), 'plan.json'); sys.exit(0)
assert MODE == 'apply'
assert hashlib.sha256(open(CAND, 'rb').read()).hexdigest() == CAND_SHA
# trigger evidence (labels carry no item text)
O = BASE/'out-v3s'
trig = {i: [] for i in delA}
for p in sorted((O/'labels').glob('labels-*.jsonl')) + [O/'adj-qwen3.jsonl']:
    for l in open(p):
        if not l.strip(): continue
        d = json.loads(l)
        if d['id'] in trig and 'exceeds_common_knowledge' in ((d.get('primitives') or {}).get('qualifiers') or []):
            trig[d['id']].append(p.stem)
for i in delA: trig[i].append('final:qualifier=exceeds_common_knowledge')
row_sha = {}
for l in lines:
    d = json.loads(l)
    if d['id'] in trig: row_sha[d['id']] = hashlib.sha256(l.encode()).hexdigest()
# (a) delete from every text-bearing file in the v3-safety archive
TEXT_FILES = [O/'gen-seed-oss-36b.jsonl', O/'items-v3s.jsonl', O/'final/seal-input.jsonl',
              BASE/'seal-work/candidate/v3-safety.jsonl', BASE/'seal-work/recheck/v3-safety.jsonl']
drop = set(delA); per_file = {}
for p in TEXT_FILES:
    src = [l for l in open(p, encoding='utf-8').read().split('\n') if l.strip()]
    keep_l = [l for l in src if json.loads(l)['id'] not in drop]
    per_file[str(p.relative_to(BASE))] = {'before': len(src), 'removed': len(src) - len(keep_l),
                                          'sha_before': hashlib.sha256(open(p,'rb').read()).hexdigest()}
    assert len(src) - len(keep_l) == len(delA), (p, len(src) - len(keep_l))
    tmp = str(p) + '.tmp'; open(tmp, 'w', encoding='utf-8').write('\n'.join(keep_l) + '\n'); os.replace(tmp, p)
    per_file[str(p.relative_to(BASE))]['sha_after'] = hashlib.sha256(open(p,'rb').read()).hexdigest()
log = {'declared_exception': 'eck deletion (Justin t215u): generated rows with qualifier exceeds_common_knowledge deleted unviewed from the v3-safety archive only; S1/S3 pilot archives untouched; the 3 real eck rows are kept and flagged (deletion rule applies to generated rows only); label/adjudication/combined lines (no item text) retained as trigger evidence, same form as the CSE guard',
       'n_deleted': len(delA), 'deleted_rows': [{'id': i, 'trigger': trig[i], 'row_sha256_candidate': row_sha[i]} for i in delA],
       'files': per_file}
json.dump(log, open(TD/'eck-deletion-log.json', 'w'), indent=1)
# trim inputs for airp_v3.seal (rows from the post-deletion candidate; add flags)
FLAG = {}
for i in real: FLAG.setdefault(i, []).append('real_elicited')
for i in real & EK: FLAG[i].append('real_eck_kept_t215u_scope_generated_only')
for i in real & CM: FLAG[i].append('real_conveys_method_kept_t215u')
for i in MINOR: FLAG.setdefault(i, []).append('subject_is_minor_qualifier_kept_t214u')
out_f, out_r = [], []
for r in rows:
    if r['id'] in keep or r['id'] in reserve:
        if r['id'] in FLAG: r['provenance'] = dict(r['provenance'], flags=sorted(FLAG[r['id']]))
        (out_f if r['id'] in keep else out_r).append(json.dumps(r, ensure_ascii=False))
open(TD/'final-input.jsonl', 'w', encoding='utf-8').write('\n'.join(out_f) + '\n')
open(TD/'reserve-input.jsonl', 'w', encoding='utf-8').write('\n'.join(out_r) + '\n')
json.dump(plan, open(TD/'plan.json', 'w'), indent=1)
json.dump({k: sorted(v) for k, v in FLAG.items()}, open(TD/'flags.json', 'w'), indent=1)
print(json.dumps({'deleted': len(delA), 'files': {k: (v['before'], v['removed']) for k, v in per_file.items()},
                  'final': len(out_f), 'reserve': len(out_r), 'flags': len(FLAG)}))

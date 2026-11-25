"""Read branch-order descriptors from ordered native empty-map OD paths.

Captures the singleton at the first split and at the last merge. It is an
additional invariant, not a full graph isomorphism or all-paths certificate.
"""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def boundary_singleton(paths,reverse=False):
 seq=[list(reversed(p['rails'])) if reverse else p['rails'] for p in paths]
 end=min(map(len,seq));i=0
 while i<end and len({s[i] for s in seq})==1:i+=1
 if i==end:return {'kind':'contained','common_prefix_rails':i}
 counts={x:sum(s[i]==x for s in seq) for x in {s[i] for s in seq}}
 if sorted(counts.values())==[1,2]:
  k=next(k for k,s in enumerate(seq) if counts[s[i]]==1)
  return {'kind':'binary','singleton':paths[k]['origin' if reverse else 'destination'],'common_prefix_rails':i}
 return {'kind':'ternary-or-initial-path-disagreement','common_prefix_rails':i}

def analyze(c):
 splits={str(o):boundary_singleton([p for p in c['paths'] if p['origin']==o]) for o in range(1,5)}
 merges={str(d):boundary_singleton([p for p in c['paths'] if p['destination']==d],True) for d in range(1,5)}
 possibilities=[]
 if all(v['kind']=='binary' for m in [splits,merges] for v in m.values()):
  for rot in range(4):
   x=[]
   for m in [splits,merges]:
    z={str((int(k)-1+rot)%4+1):(v['singleton']-1+rot)%4+1 for k,v in m.items()}
    x.extend(z[str(k)] for k in range(1,5))
   possibilities.append(x)
 return {'id':c['id'],'first_split':splits,'last_merge':merges,'C4_canonical_binary_order':min(possibilities) if possibilities else None}

rows=[];sources=[]
for summary in ['round4/reference-graphs.json','round4/directed/structural-audit.json','round4/directed/packed-structural-audit.json','round4/directed/torder-structural-audit.json']:
 meta=json.loads((ROOT/summary).read_text());p=ROOT/meta['evidence_directory']/'script-output/result.json';sources.append(str(p.relative_to(ROOT)))
 for c in json.loads(p.read_text())['cases']:
  if c['id'].startswith('r4-dir-') or c['id'] in ['r3-sig-turbine2-dense2','r2-sig-stacked-cloverleaf-all4-clean']:rows.append(analyze(c))
(HERE/'branch-orders.json').write_text(json.dumps({'sources':sources,'cases':rows,'distinct_directed_binary_order_invariants':len({tuple(r['C4_canonical_binary_order']) for r in rows if r['id'].startswith('r4-dir-') and r['C4_canonical_binary_order']})},indent=2))
for r in rows:print(r['id'],r['C4_canonical_binary_order'])

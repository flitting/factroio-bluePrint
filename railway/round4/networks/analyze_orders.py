"""Recover split/merge order from exact native OD rail paths.

Shared path lengths are not signal stop-point storage proofs. They locate
which two OD flows remain coupled and how much native rail length separates
two junctions, to guide further buffering tests.
"""
import json,itertools
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def prefix(ps):
 n=0
 for z in zip(*ps):
  if len(set(z))>1:break
  n+=1
 return ps[0][:n]
def typ(o,d):return {1:'far',2:'straight',3:'near'}[(d-o)%4]
rows=[]
for path in sorted(H.glob('*graph*.json')):
 summ=json.loads(path.read_text())
 if not isinstance(summ,dict) or 'evidence_directory' not in summ:continue
 raw=json.loads((R/summ['evidence_directory']/'script-output/result.json').read_text())
 for c in raw['cases']:
  rs={x['id']:x for x in c['rails']};ps={(p['origin'],p['destination']):p['rails'] for p in c['paths']};row={'id':c['id'],'entry':[],'exit':[],'source':summ['evidence_directory']}
  for direction in ['entry','exit']:
   for port in range(1,5):
    keys=[p for p in ps if p[0 if direction=='entry' else 1]==port]
    paths=[ps[k] if direction=='entry' else list(reversed(ps[k])) for k in keys]
    common=prefix(paths);all_len=sum(rs[x]['length'] for x in common)
    pairs=[(len(prefix([paths[a],paths[b]])),a,b,prefix([paths[a],paths[b]])) for a,b in itertools.combinations(range(3),2)]
    _,a,b,shared=max(pairs);single=next(i for i in range(3) if i not in (a,b));paired_len=sum(rs[x]['length'] for x in shared)
    row[direction].append({'port':'NESW'[port-1],'first_split_flow' if direction=='entry' else 'last_merge_flow':typ(*keys[single]),'paired_flows':[typ(*keys[x]) for x in [a,b]],'all_three_shared_native_length':all_len,'two_only_shared_native_length':paired_len-all_len,'note':'Native rail lengths along shared prefix/suffix, not a certified full-train waiting length.'})
  rows.append(row)
unique={r['id']:r for r in rows};(H/'native-split-merge-orders.json').write_text(json.dumps({'cases':list(unique.values()),'interpretation':'These signatures distinguish order/buffer embeddings even where the 66 OD shared-rail presence signature is identical.'},indent=2))
for r in unique.values():
 if 'quadrant-direct' in r['id'] and r['id'].endswith('normal'):print(r['id'],[(q['port'],q['first_split_flow'],round(q['two_only_shared_native_length'],2)) for q in r['entry']],[(q['port'],q['last_merge_flow'],round(q['two_only_shared_native_length'],2)) for q in r['exit']])

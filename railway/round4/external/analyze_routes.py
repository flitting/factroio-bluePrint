#!/usr/bin/env python3
"""Contract geometry by comparing the native 12-OD path overlap pattern.

Shared signals/blocks are distinct from shared traversable rails. This report is
based on one empty-network native path per OD, not a proof about all repaths.
"""
from pathlib import Path
import json,itertools,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def key(e):return(e['name'],e['position']['x'],e['position']['y'])
def prefix(a,b):
 n=0
 for x,y in zip(a,b):
  if x!=y:break
  n+=1
 return n

def analyze(summary):
 aud=json.loads((ROOT/summary['audit_evidence']/'script-output/audit.json').read_text());drive=json.loads((ROOT/summary['drive_evidence']/'script-output/path-probes.json').read_text());rows=[]
 for a,d in zip(aud['cases'],drive['cases']):
  idx={key(r):r['block_id'] for r in a['rails']}
  raw={t['origin']+t['destination']:[key(r) for r in t['path_rails']] for t in d['trials']}
  paths={k:[r for r in p if r in idx] for k,p in raw.items()};sets={k:set(p) for k,p in paths.items()};blocks={k:{idx[r] for r in p} for k,p in paths.items()}
  pairs=[]
  for x,y in itertools.combinations(sorted(paths),2):
   pairs.append({'od_a':x,'od_b':y,'same_origin':x[0]==y[0],'same_destination':x[1]==y[1],'shared_core_rails':len(sets[x]&sets[y]),'shared_core_blocks':len(blocks[x]&blocks[y])})
  forks={};merges={}
  for side in 'NESW':
   for mode,answer in [('in',forks),('out',merges)]:
    ks=[k for k in paths if k[0 if mode=='in' else 1]==side];overlap=[]
    for x,y in itertools.combinations(ks,2):
     px,py=raw[x],raw[y]
     if mode=='out':px,py=px[::-1],py[::-1]
     overlap.append((prefix(px,py),x,y))
    overlap.sort(reverse=True)
    tied=sum(p[0]==overlap[0][0] for p in overlap)
    singleton=next(k for k in ks if k not in overlap[0][1:]) if tied==1 else None
    answer[side]={'isolated_first' if mode=='in' else 'joins_last':singleton,'pair_shared_longest':list(overlap[0][1:]),'native_prefix_rail_count' if mode=='in' else 'native_suffix_rail_count':overlap[0][0],'ambiguous':tied!=1}
  signature=''.join('1' if p['shared_core_rails'] else '0' for p in pairs)
  rows.append({'id':a['id'],'core_rail_count':len(idx),'native_full_OD_paths':12,'routes':[{'od':k,'core_rails':len(p),'core_blocks':len(blocks[k])} for k,p in sorted(paths.items())],'path_pairs':pairs,'different_origin_and_destination_shared_rail_pairs':sum(not p['same_origin'] and not p['same_destination'] and p['shared_core_rails']>0 for p in pairs),'different_origin_and_destination_shared_block_pairs':sum(not p['same_origin'] and not p['same_destination'] and p['shared_core_blocks']>0 for p in pairs),'binary_shared_rail_signature':signature,'split_order':forks,'merge_order':merges})
 return rows
if __name__=='__main__':
 summaries=[json.loads(p.read_text()) for p in [HERE/'validation-summary.json', HERE/'extra-validation-summary.json'] if p.exists()]
 rows=sum([analyze(s) for s in summaries],[])
 (HERE/'route-structure.json').write_text(json.dumps({'scope':'one empty-network native path per OD; core-only shared rail and block relationships; not all-path proof','cases':rows},indent=2))
 for r in rows:print(r['id'],r['different_origin_and_destination_shared_rail_pairs'],r['different_origin_and_destination_shared_block_pairs'],{k:v['isolated_first'] for k,v in r['split_order'].items()},{k:v['joins_last'] for k,v in r['merge_order'].items()})

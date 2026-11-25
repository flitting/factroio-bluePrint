"""Exhaustive 8-column permutation and interval-coloring surrogate.

These are abstract orderings, not 40,320 native blueprints. The objective only
minimizes rows / total transverse span / longest transverse span on this model.
"""
import itertools,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
vertices=[a+b for a in 'io' for b in 'NESW']
edges=[('i'+o,'o'+d) for o in 'NESW' for d in 'NESW' if o!=d]
best=None;solutions=[];evaluated=0
for permutation in itertools.permutations(vertices):
 p={v:i for i,v in enumerate(permutation)}
 if p['iN']>p['oN'] or p['iS']<p['oS']:continue
 evaluated+=1
 spans=sorted((min(p[a],p[b]),max(p[a],p[b]),a[1]+b[1]) for a,b in edges)
 ends=[];groups=[]
 for start,end,od in spans:
  possible=[i for i,x in enumerate(ends) if x<start]
  if possible:i=possible[0];ends[i]=end;groups[i].append(od)
  else:ends.append(end);groups.append([od])
 score=(len(ends),sum(b-a for a,b,_ in spans),max(b-a for a,b,_ in spans))
 if best is None or score<best:best=score;solutions=[(permutation,groups)]
 elif score==best:solutions.append((permutation,groups))
result={'permutations_enumerated':40320,'rht_orderings_evaluated':evaluated,'objective':['interval rows','sum transverse column span','maximum transverse column span'],'best_score':best,'solutions':solutions,'native_blueprints_built_by_this_script':0,'scope':'Only this two-layer crossbar embedding surrogate; not a global interchange optimum or native throughput prediction.'}
(HERE/'column-order-search.json').write_text(json.dumps(result,indent=2))
print('evaluated',evaluated,'best',best,'ties',len(solutions))

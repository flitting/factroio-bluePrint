"""Acyclicity of the block transitions on the 12 selected native OD paths.
Not a proof about every dynamic alternative or externally blocked station.
"""
import json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
rows=[];sources=[]
for summary in ['round4/reference-graphs.json','round4/directed/structural-audit.json','round4/directed/packed-structural-audit.json','round4/directed/torder-structural-audit.json','round4/directed/trident-structural-audit.json']:
 meta=json.loads((ROOT/summary).read_text());p=ROOT/meta['evidence_directory']/'script-output/result.json';sources.append(str(p.relative_to(ROOT)))
 for c in json.loads(p.read_text())['cases']:
  rails={r['id']:r for r in c['rails']};nodes=set();edges=set();paths=[]
  for pth in c['paths']:
   blocks=[]
   for r in pth['rails']:
    b=rails[r]['block'];nodes.add(b)
    if not blocks or b!=blocks[-1]:blocks.append(b)
   edges.update(zip(blocks,blocks[1:]));paths.append({'origin':pth['origin'],'destination':pth['destination'],'blocks':blocks,'repeated_nonconsecutive_block':len(set(blocks))!=len(blocks)})
  adjacency=collections.defaultdict(set);degree={n:0 for n in nodes}
  for a,b in edges:adjacency[a].add(b);degree[b]+=1
  queue=collections.deque(sorted(n for n in nodes if degree[n]==0));order=[]
  while queue:
   n=queue.popleft();order.append(n)
   for nxt in sorted(adjacency[n]):
    degree[nxt]-=1
    if degree[nxt]==0:queue.append(nxt)
  row={'id':c['id'],'selected_path_blocks':len(nodes),'selected_path_block_edges':len(edges),'acyclic':len(order)==len(nodes),'blocked_kahn_nodes':[n for n in sorted(nodes) if degree[n]>0],'topological_block_order':order,'paths':paths}
  rows.append(row)
(HERE/'block-order.json').write_text(json.dumps({'sources':sources,'cases':rows,'scope':'Union of native empty-map selected OD path block transitions. A DAG is useful evidence of an acyclic resource order for these paths; it is not a proof of all dynamic routes or all externally blocked scenarios.'},indent=2))
for r in rows:print(r['id'],r['acyclic'],r['selected_path_blocks'],r['selected_path_block_edges'])

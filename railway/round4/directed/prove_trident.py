"""Evidence for actual native three-way forks/merges, not a visual guess."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def examine(c):
 rails={r['id']:r for r in c['rails']};out={'id':c['id'],'first_forks':[],'last_merges':[]}
 for reverse,collection in [(False,'first_forks'),(True,'last_merges')]:
  for side in range(1,5):
   paths=[p for p in c['paths'] if p['destination' if reverse else 'origin']==side]
   seq=[list(reversed(p['rails'])) if reverse else p['rails'] for p in paths];j=0
   while j<min(map(len,seq)) and len({p[j] for p in seq})==1:j+=1
   assert 0<j<min(map(len,seq)),(c['id'],side,j)
   trunk=rails[seq[0][j-1]];nexts={p[j] for p in seq}
   matches=[e for e in trunk['ends'] if nexts<=set(e['connections'])]
   assert len(matches)==1,(c['id'],side,collection,nexts,trunk['ends'])
   e=matches[0]
   out[collection].append({'side':'NESW'[side-1],'common_path_length_in_rails':j,'native_trunk_rail_id':trunk['id'],'native_trunk_position':trunk['position'],'native_trunk_name':trunk['name'],'rail_end':e['rd'],'native_connection_count':len(e['connections']),'native_next_rails':e['connections'],'distinct_od_successors':len(nexts),'od_successor_ids':sorted(nexts)})
 out['all_first_forks_ternary']=all(q['native_connection_count']==3 and q['distinct_od_successors']==3 for q in out['first_forks'])
 out['all_last_merges_ternary']=all(q['native_connection_count']==3 and q['distinct_od_successors']==3 for q in out['last_merges'])
 return out
rows=[];evidence=[]
for summary,wanted in [('round4/reference-graphs.json','r3-sig-turbine2-dense2'),('round4/directed/trident-structural-audit.json','r4-dir-trident32-32')]:
 m=json.loads((ROOT/summary).read_text());p=ROOT/m['evidence_directory']/'script-output/result.json';raw=json.loads(p.read_text());evidence.append(str(p.relative_to(ROOT)))
 rows.append(examine(next(c for c in raw['cases'] if c['id']==wanted)))
assert all(q['native_connection_count']==2 and q['distinct_od_successors']==2 for k in ['first_forks','last_merges'] for q in rows[0][k])
assert rows[1]['all_first_forks_ternary'] and rows[1]['all_last_merges_ternary']
result={'evidence_files':evidence,'cases':rows,'claim':'Native rail endpoints at all 4 first input forks and all 4 final output merges have 3 neighbors used by the 3 OD paths in the new trident; reference T has 2. This demonstrates a real branch-graph change, not only geometry or signal density.'}
(HERE/'trident-native-proof.json').write_text(json.dumps(result,indent=2))
for r in rows:print(r['id'],[q['native_connection_count'] for q in r['first_forks']],[q['native_connection_count'] for q in r['last_merges']])

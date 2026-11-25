"""Remove only outer ground straight rails; preserve every fork/curve/ramp.

The final merge remains wholly inside the candidate. Moving the ports changes
how much output storage precedes the common fixture's first signal, so results
must be retested and blockage robustness compared separately.
"""
import json,base64,zlib,collections
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
cases=[]
params={c['id']:c for fn in ['clockwise-cases.json','compact-cases.json','refined-cases.json','order-cases.json'] for c in json.loads((H/fn).read_text())}
ids=['r4-net-quadrant-direct-r75-l17-n77-e16-h48-normal','r4-net-quadrant-direct-r59-l17-n61-e16-h32-normal','r4-net-quadrant-direct-r35-l17-n93-e8-h18-normal','r4-net-quadrant-direct-r35-l17-n61-e8-h18-normal']
for ident in ids:
 c=params[ident.removesuffix('-normal')];lane=c['external_lane_offset'];span=c['near_span'];rad=c['radius'];ext=c['exit_extension'];last=max(lane+span,rad+55+ext);boundary=last+4
 doc=json.loads((R/'blueprints'/f'{ident}.json').read_text());removed=[];kept=[]
 for e in doc['blueprint']['entities']:
  m=max(abs(e['position']['x']),abs(e['position']['y']))
  if e['name']=='straight-rail' and m>boundary-1:removed.append(e)
  elif e['name'] in ('rail-signal','rail-chain-signal') and m>boundary+.5:removed.append(e)
  else:kept.append(e)
 assert all(e['name'] in ('straight-rail','rail-signal','rail-chain-signal') for e in removed)
 for i,e in enumerate(kept,1):e['entity_number']=i
 out=ident+'-short';doc['blueprint']['entities']=kept;doc['blueprint']['label']=out;code='0'+base64.b64encode(zlib.compress(json.dumps(doc,separators=(',',':')).encode())).decode()
 for d in [H,R/'blueprints']:(d/f'{out}.json').write_text(json.dumps(doc,indent=2));(d/f'{out}.txt').write_text(code+'\n')
 cases.append({'id':out,'base':ident,'old_endpoint_radius':rad+99+ext,'new_endpoint_radius':boundary,'final_merge_coordinate':last,'new_tail_tiles':4,'old_tail_tiles':rad+99+ext-last,'removed_counts':dict(collections.Counter(e['name'] for e in removed)),'removed':removed,'all_nonstraight_nonsignal_entities_preserved':True,'requires':'normal native reconstruction, own-core 12 OD routing, finite traffic rerun, paired blocked-exit recovery before robust recommendation'})
(H/'tail-trim-manifest.json').write_text(json.dumps(cases,indent=2));print([(c['id'],c['old_tail_tiles'],c['new_tail_tiles'],c['removed_counts']) for c in cases])

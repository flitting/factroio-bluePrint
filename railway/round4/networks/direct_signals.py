"""Native signal policy candidates for quadrants. Names, positions unchanged.

All-normal is appropriate only if the native graph shows no crossing block
coupling between independent OD routes; finite congestion/drain tests remain
necessary. It is an experiment, not an assumed deadlock guarantee.
"""
import json,base64,zlib
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
rows=[]
for c in json.loads((H/'clockwise-cases.json').read_text())+json.loads((H/'compact-cases.json').read_text())+json.loads((H/'refined-cases.json').read_text())+json.loads((H/'order-cases.json').read_text()):
 src=ROOT/'blueprints'/f'{c["id"]}.json'
 if not src.exists():continue
 doc=json.loads(src.read_text());orig=json.loads(src.read_text());ident=c['id']+'-normal'
 for e in doc['blueprint']['entities']:
  if e['name']=='rail-chain-signal':e['name']='rail-signal'
 doc['blueprint']['label']=ident
 code='0'+base64.b64encode(zlib.compress(json.dumps(doc,separators=(',',':')).encode())).decode()
 for d in [H,ROOT/'blueprints']:(d/f'{ident}.json').write_text(json.dumps(doc,indent=2));(d/f'{ident}.txt').write_text(code+'\n')
 rows.append({'id':ident,'base':c['id'],'signals':sum('signal' in e['name'] for e in doc['blueprint']['entities']),'changed_signal_names_only':True})
(H/'direct-signal-variants.json').write_text(json.dumps(rows,indent=2));print([r['id'] for r in rows])

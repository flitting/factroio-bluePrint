#!/usr/bin/env python3
"""Apply the recorded one-signal native repair without changing rail geometry."""
import json,pathlib,base64,zlib,hashlib
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
r=json.loads((HERE/'clean-repair.json').read_text());doc=json.loads((ROOT/'blueprints'/f"{r['base']}.json").read_text())
def key(e):return json.dumps({k:v for k,v in e.items() if k!='entity_number'},sort_keys=True)
bad={key(e) for e in r['removed_nonworking_signal']};assert all(e['name'] in ['rail-signal','rail-chain-signal'] for e in r['removed_nonworking_signal'])
old=doc['blueprint']['entities'];doc['blueprint']['entities']=[e for e in old if key(e) not in bad];assert len(old)-len(doc['blueprint']['entities'])==1
for i,e in enumerate(doc['blueprint']['entities'],1):e['entity_number']=i
doc['blueprint']['label']=r['id'];text='0'+base64.b64encode(zlib.compress(json.dumps(doc,separators=(',',':')).encode())).decode()+'\n'
assert hashlib.sha256(text.encode()).hexdigest()==r['test_blueprint_sha256']
(ROOT/'blueprints'/f"{r['id']}.json").write_text(json.dumps(doc,indent=2));(ROOT/'blueprints'/f"{r['id']}.txt").write_text(text)
print(r['id'], 'reconstructed and hash verified')

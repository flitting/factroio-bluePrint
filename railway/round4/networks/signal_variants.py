"""Signal policies for newly generated ring-bypass families (same rail geometry).

Buffered policy releases conflicts only after a candidate full-train storage
length, but this geometric target is not a deadlock proof; real native tests
must determine legality, travel, and congestion. Original all-chain variant
is retained as conservative control. Names count as configurations, not new
geometric architectures.
"""
import json,copy,base64,zlib,math
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def rot(p,k):
 x,y=p
 for _ in range(k%4):x,y=-y,x
 return (x,y)
def save(ident,doc):
 doc['blueprint']['label']=ident
 code='0'+base64.b64encode(zlib.compress(json.dumps(doc,separators=(',',':')).encode())).decode()
 for d in [H,R/'blueprints']:(d/f'{ident}.json').write_text(json.dumps(doc,indent=2));(d/f'{ident}.txt').write_text(code+'\n')
rows=[]
for case in json.loads((H/'cases.json').read_text()):
 ident=case['id'];radius=case['radius'];lane=case['external_lane_offset'];source=R/'blueprints'/f'{ident}.json'
 if not source.exists():continue
 for policy in ['buffered','loose']:
  doc=json.loads(source.read_text());signals=[e for e in doc['blueprint']['entities'] if e['name'] in ('rail-signal','rail-chain-signal')]
  targets=[]
  for k in range(4):
   # Two possible ring waiting slots, feeder storage, exit dogleg storage,
   # inlet after far-turn split, and output ahead of the late far-turn merge.
   for target,layer in [((-radius,4),'elevated'),((-radius,44),'elevated'),((-lane-37,-radius-16),'elevated'),((-radius-42,-lane-13),'ground'),((-lane,-radius+15),'ground'),((-radius-8,-lane),'ground')]:targets.append((rot(target,k),layer))
  chosen=[]
  for e in signals:
   e['name']='rail-chain-signal'
   x,y=e['position']['x'],e['position']['y'];d=e.get('direction',0);layer=e.get('rail_layer','ground')
   if layer=='ground' and ((y<-radius-60 and x<0 and d==0) or (x>radius+60 and y<0 and d==4) or (y>radius+60 and x>0 and d==8) or (x<-radius-60 and y>0 and d==12)):e['name']='rail-signal'
   if policy=='loose' and layer=='elevated' and max(abs(x),abs(y))>radius-8:e['name']='rail-signal'
  for p,layer in targets:
   choices=[e for e in signals if e.get('rail_layer','ground')==layer]
   e=min(choices,key=lambda e:(e['position']['x']-p[0])**2+(e['position']['y']-p[1])**2)
   dist=math.hypot(e['position']['x']-p[0],e['position']['y']-p[1]);assert dist<7,(ident,p,e,dist)
   e['name']='rail-signal';chosen.append({'target':p,'position':e['position'],'layer':layer,'distance':dist})
  out=ident+'-'+policy;save(out,doc);rows.append({'id':out,'base':ident,'policy':policy,'normal_signals':sum(e['name']=='rail-signal' for e in signals),'chain_signals':sum(e['name']=='rail-chain-signal' for e in signals),'buffer_targets':chosen})
(H/'signal-variants.json').write_text(json.dumps(rows,indent=2));print([(r['id'],r['normal_signals'],r['chain_signals']) for r in rows])

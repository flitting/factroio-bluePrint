#!/usr/bin/env python3
"""Additional independently sourced geometry families and small controls."""
import json,copy,base64,zlib,hashlib,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SPECS=[
 ('cube','cube-rhd.json','DaveMcW','https://forums.factorio.com/viewtopic.php?p=621337'),
 ('three-chunk-square','three-chunk-square.json','mmmPI','https://forums.factorio.com/viewtopic.php?p=626041'),
 ('ground-cross','bocian/ground-cross.json','Bocian / Opinionated-Blueprints contributors',None),
 ('hyper-cross','bocian/hyper-cross.json','Bocian / Opinionated-Blueprints contributors',None),
 ('level-switch-one','bocian/level-switch-4-way-(1).json','Bocian / Opinionated-Blueprints contributors',None),
 ('level-switch-two','bocian/level-switch-4-way-(2).json','Bocian / Opinionated-Blueprints contributors',None),
]
rows=[]
for name,path,author,url in SPECS:
 src=HERE/'sources'/path;original=json.loads(src.read_text())['blueprint'];b=copy.deepcopy(original);sx=b.get('shift_x',0);sy=b.get('shift_y',0)
 ents=[e for e in b['entities'] if 'rail' in e['name']]
 # Work in source normalized coordinates until translation below.
 adapters=[]
 def add(n,x,y,d):
  e={'name':n,'position':{'x':x,'y':y},'direction':d};adapters.append(copy.deepcopy(e));ents.append(e)
 if name=='cube':
  for x in [795,799]:
   for y in range(-81,-89,-2):add('straight-rail',x,y,0)
   for y in range(15,23,2):add('straight-rail',x,y,0)
  for y in [-35,-31]:
   for x in range(749,741,-2):add('straight-rail',x,y,4)
   for x in range(845,853,2):add('straight-rail',x,y,4)
 if name=='three-chunk-square':
  for x in [-5,1]:
   for off in range(2,10,2):
    add('straight-rail',x,-39-off,0);add('straight-rail',x,55+off,0)
  for y in [5,11]:
   for off in range(2,10,2):
    add('straight-rail',-49-off,y,4);add('straight-rail',45+off,y,4)
 if name=='level-switch-one':
  for x in [0,8]:
   add('rail-ramp',x,-41,8);add('rail-ramp',x,49,0)
   for off in range(2,18,2):
    add('elevated-straight-rail',x,-16-off,0);add('elevated-straight-rail',x,24+off,0)
   for y in range(-50,-58,-2):add('straight-rail',x,y,0)
   for y in range(58,66,2):add('straight-rail',x,y,0)
 if name=='level-switch-two':
  for y in [0,8]:
   add('rail-ramp',-83,y,4);add('rail-ramp',91,y,12)
   for off in range(2,18,2):
    add('elevated-straight-rail',-58-off,y,4);add('elevated-straight-rail',66+off,y,4)
   for x in range(-92,-100,-2):add('straight-rail',x,y,4)
   for x in range(100,108,2):add('straight-rail',x,y,4)
 for e in ents:e['position']['x']+=sx;e['position']['y']+=sy
 xs=[e['position']['x'] for e in ents];ys=[e['position']['y'] for e in ents];dx=2*round((min(xs)+max(xs))/4);dy=2*round((min(ys)+max(ys))/4)
 for i,e in enumerate(ents,1):
  e['entity_number']=i;e['position']['x']-=dx;e['position']['y']-=dy
 ident='r4-ext-'+name
 bp={'blueprint':{'item':'blueprint','label':ident,'version':b['version'],'entities':ents,'icons':[{'signal':{'name':'rail'},'index':1}],'description':f'Rail-system-only benchmark view. Source: {author}. Transformations and pinned source records: round4/external.'}}
 txt='0'+base64.b64encode(zlib.compress(json.dumps(bp,separators=(',',':')).encode())).decode()
 (ROOT/'blueprints'/f'{ident}.json').write_text(json.dumps(bp,indent=2));(ROOT/'blueprints'/f'{ident}.txt').write_text(txt+'\n')
 rows.append({'id':ident,'upstream_label':b.get('label'),'author':author,'source':str(src.relative_to(ROOT)),'source_url':url,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'test_blueprint_sha256':hashlib.sha256(txt.encode()).hexdigest(),'native_validation':'pending','original_entity_count':len(b['entities']),'rail_system_entity_count':len(ents),'removed_nonrail_entities':dict(collections.Counter(e['name'] for e in b['entities'] if 'rail' not in e['name'])),'adapters':adapters,'adapter_note':'All adapters counted in footprint. Cube adds short ground ends; 3 Chunk Square adds boundary stubs to close forks that extend past the upstream blueprint; level-switch converts elevated external ports to ground using 16-tile elevated stubs and native ramps.','applied_upstream_shift':[sx,sy],'centering_translation':[-dx,-dy]})
(HERE/'extra-manifest.json').write_text(json.dumps(rows,indent=2));print([(r['id'],r['rail_system_entity_count'],len(r['adapters'])) for r in rows])

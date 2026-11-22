#!/usr/bin/env python3
"""Read-only structural checks on the exported book and its individual files.

python tools/check_exported_blueprints.py [directory]
No Factorio installation or third-party dependencies are required.
"""
import base64,collections,hashlib,json,math,sys,zlib
from pathlib import Path
ROOT=Path(sys.argv[1])if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
AREAS=[682,561,546,525,477,450,442,435]
ALLOWED={'stone-furnace','inserter','transport-belt','underground-belt','splitter','small-electric-pole'}

def decode(path):
 s=path.read_text().strip();assert s.startswith('0');return json.loads(zlib.decompress(base64.b64decode(s[1:],validate=True)))

def bounds(es):
 def wh(e):
  if e['name']=='stone-furnace':return 2,2
  if e['name']=='splitter':return(1,2)if e.get('direction',0)in(4,12)else(2,1)
  return 1,1
 b=[(e['position']['x']-wh(e)[0]/2,e['position']['y']-wh(e)[1]/2,e['position']['x']+wh(e)[0]/2,e['position']['y']+wh(e)[1]/2)for e in es]
 return min(x[0]for x in b),min(x[1]for x in b),max(x[2]for x in b),max(x[3]for x in b)

def mechanics(es):
 b=bounds(es);out=[]
 for e in es:
  p=e['position'];r={'name':e['name'],'x':p['x']-b[0],'y':p['y']-b[1]}
  if e['name']in{'inserter','transport-belt','underground-belt','splitter'}:r['direction']=e.get('direction',0)
  if e['name']=='inserter':r['mirror']=bool(e.get('mirror',False))
  if e['name']=='underground-belt':r['type']=e['type']
  if e['name']=='splitter':
   f=e.get('filter');r['filter']=f.get('name')if isinstance(f,dict)else f
   r['input_priority']=e.get('input_priority','none');r['output_priority']=e.get('output_priority','none')
  out.append(r)
 return sorted(out,key=lambda x:(x['name'],x['x'],x['y']))

def audit(bp,area):
 es=bp['entities'];assert len({e['entity_number']for e in es})==len(es)
 assert all(e['name']in ALLOWED for e in es)
 b=bounds(es);w,h=b[2]-b[0],b[3]-b[1];assert w>=h and w*h==area
 occupied={}
 for e in es:
  one=bounds([e]);assert all(x==round(x)for x in one)
  for x in range(round(one[0]),round(one[2])):
   for y in range(round(one[1]),round(one[3])):
    assert (x,y)not in occupied,(area,'overlap',(x,y));occupied[x,y]=e['entity_number']
 poles={e['entity_number']:e for e in es if e['name']=='small-electric-pole'};graph={n:set()for n in poles};dist=[]
 for a,c,b_,d in bp.get('wires',[]):
  assert c==d==5 and a in poles and b_ in poles
  p,q=poles[a]['position'],poles[b_]['position'];length=math.hypot(p['x']-q['x'],p['y']-q['y']);assert length<=7.5+1e-9
  dist.append(length);graph[a].add(b_);graph[b_].add(a)
 remaining=set(poles);parts=[]
 while remaining:
  todo=[remaining.pop()];part=[]
  while todo:
   n=todo.pop();part.append(n);nxt=graph[n]&remaining;remaining-=nxt;todo.extend(nxt)
  parts.append(part)
 assert len(parts)==1,(area,'disconnected poles')
 arms=[e for e in es if e['name']=='inserter'];uncovered=[]
 for e in arms:
  p=e['position']
  if not any(abs(p['x']-q['position']['x'])<=2.5 and abs(p['y']-q['position']['y'])<=2.5 for q in poles.values()):uncovered.append(e['entity_number'])
 assert not uncovered,(area,'inserters lack internal power coverage',uncovered)
 return {'area':area,'width':int(w),'height':int(h),'entities':len(es),'entity_counts':dict(collections.Counter(e['name']for e in es)),
 'copper_wires':len(bp.get('wires',[])),'pole_count':len(poles),'copper_connected_components':len(parts),'max_copper_distance':round(max(dist),6),'max_copper_degree':max(map(len,graph.values())),'all_inserters_covered_by_internal_poles':True,'mirrored_inserters':sum(bool(e.get('mirror'))for e in arms)}

book=decode(ROOT/'iron-smelting-book.txt')['blueprint_book'];assert book['active_index']==7
assert len(book['blueprints'])==8
rows=[]
for i,area in enumerate(AREAS):
 p=ROOT/f'blueprints/iron-smelting-{area}.txt';b=decode(p)['blueprint'];assert b==book['blueprints'][i]['blueprint']
 assert json.loads(p.with_suffix('.json').read_text())['blueprint']==b
 assert book['blueprints'][i]['index']==i
 rows.append(audit(b,area))
# The source configurations are optional, private staging inputs. When present,
# check the mechanics against the actual configurations used for the video.
source=ROOT/'staging/engine/input_config.json'
if source.is_file():
 for a,row in zip(json.loads(source.read_text())['layouts'],rows):
  bp=decode(ROOT/f'blueprints/iron-smelting-{a["key"]}.txt')['blueprint']
  assert mechanics(a['entities'])==mechanics(bp['entities']),(a['key'],'mechanics differ from source')
  row['source_geometry_directions_mirrors_splitters']='identical'
print(json.dumps({'status':'passed','book_entries':8,'active_area':435,'layouts':rows},ensure_ascii=False,indent=2))

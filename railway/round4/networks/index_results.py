import base64,collections,hashlib,json,zlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def doc(code):return json.loads(zlib.decompress(base64.b64decode(code[1:])))
def geom(bp):
 out=[]
 for e in bp['blueprint']['entities']:
  if e['name'] in ('rail-support','rail-signal','rail-chain-signal'):continue
  d=e.get('direction',0)
  if e['name'] in ('straight-rail','elevated-straight-rail'):d%=8
  out.append((e['name'],e['position']['x'],e['position']['y'],d))
 return hashlib.sha256(json.dumps(sorted(set(out)),separators=(',',':')).encode()).hexdigest()
builds={};failures={};instrumentation=[]
for d in sorted((R/'experiments').glob('r4-net-*')):
 p=d/'request.json';q=d/'script-output/result.json'
 if not p.exists() or not q.exists():continue
 request=json.loads(p.read_text());result=json.loads(q.read_text())
 if not isinstance(result,dict) or not result.get('cases'):continue
 cfgs={c['id']:c for c in request.get('config',{}).get('cases',[])}
 for row in result['cases']:
  ident=row['id'];c=cfgs.get(ident)
  if not c or 'blueprint' not in c:continue
  signature=geom(doc(c['blueprint']));ev={'id':ident,'geometry_sha256':signature,'evidence_directory':str(d.relative_to(R)),'build_complete':row.get('build_complete'),'path_missing_count':len(row.get('path_missing',[])),'direction_conflicts':len(row.get('direction_conflicts',[])),'remaining_ghost_count':len(row.get('remaining',[])),'missing_after_revival':row.get('missing_after_revival',[])}
  if row.get('build_complete') and not row.get('path_missing') and not row.get('direction_conflicts'):builds[signature]=ev
  elif row.get('build_complete'):instrumentation.append(ev)
  else:failures[signature]=ev
rows={}
for f in sorted((R/'blueprints').glob('r4-net-*.json')):
 bp=json.loads(f.read_text());ident=f.stem
 rows[ident]={'id':ident,'geometry_sha256':geom(bp),'entities':len(bp['blueprint']['entities']),'signals':sum(e['name'] in ('rail-signal','rail-chain-signal') for e in bp['blueprint']['entities']),'blueprint_sha256':hashlib.sha256((f.with_suffix('.txt')).read_bytes()).hexdigest(),'static_native_graph':None,'traffic':[]}
for f in H.glob('*graph*.json'):
 d=json.loads(f.read_text())
 if not isinstance(d,dict):continue
 for c in d.get('cases',[]):
  if c['id'] in rows:rows[c['id']]['static_native_graph']={**c,'evidence_directory':d['evidence_directory']}
for f in H.glob('*.json'):
 if not any(s in f.name for s in ['screen','formal-selected','formal-long-tail']):continue
 d=json.loads(f.read_text())
 if not isinstance(d,list):continue
 for c in d:
  if isinstance(c,dict) and c.get('id') in rows and 'throughput' in c:rows[c['id']]['traffic'].append({**c,'summary_file':str(f.relative_to(R))})
for row in rows.values():
 row['geometry_normal_build_evidence']=builds.get(row['geometry_sha256'])
 row['configuration_native_observed']=bool(row['static_native_graph'] or row['traffic'] or (row['geometry_normal_build_evidence'] and row['geometry_normal_build_evidence']['id']==row['id']))
traffic=[t for r in rows.values() for t in r['traffic']]
result={'scope':'De novo network family search; counts distinguish blueprint configurations, rail geometry embeddings, and broad connectivity families. Geometrically different embeddings may share the same contracted topology.','configuration_count':len(rows),'configuration_native_observed_count':sum(r['configuration_native_observed'] for r in rows.values()),'distinct_rail_geometry_count':len(set(r['geometry_sha256'] for r in rows.values())),'native_observed_rail_geometry_count':len(set(r['geometry_sha256'] for r in rows.values() if r['configuration_native_observed'])),'geometry_explicit_builder_validated_count':len(builds),'native_build_rejected_geometry_count':len([x for k,x in failures.items() if k not in builds]),'short_bank_cases':sum(t['warmup']==1800 and t['duration']==3600 for t in traffic),'formal_bank_cases':sum(t['warmup']==3600 and t['duration']==10800 for t in traffic),'broad_families':['counterclockwise shared turning ring with straight/near bypass alternatives','clockwise turning ring with straight and near bypasses','private quadrant far-turn connectors with independent near and straight routes'],'cases':list(rows.values()),'native_build_rejections':[x for k,x in failures.items() if k not in builds],'instrumentation_attempts_not_design_failures':instrumentation}
(H/'candidate-inventory.json').write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items() if k not in ['cases','native_build_rejections','instrumentation_attempts_not_design_failures']})

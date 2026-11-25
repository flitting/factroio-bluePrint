import json,pathlib,sys,base64,zlib,hashlib,collections
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from run import run
base='r4-dir-crossbar64-source';text=(ROOT/'blueprints'/f'{base}.txt').read_text().strip();bp=json.loads(zlib.decompress(base64.b64decode(text[1:])))['blueprint'];es=bp['entities']
gates=json.loads((HERE/'gates.json').read_text())['gates'];cases=[]
for seconds in (6,15,30):
 cases.append({'id':f'r4-batch-h64-phase{seconds}','phase_ticks':seconds*60,'blueprint':text,'expected':len(es),'extent':max(abs(e['position'][axis]) for e in es for axis in ['x','y']),'minx':min(e['position']['x'] for e in es),'miny':min(e['position']['y'] for e in es),'gates':gates})
source=HERE/'build.lua';source.write_text((HERE/'circuit.lua').read_text()+'\n'+(HERE/'build_tail.lua').read_text())
raw=run('r4-batch-native-build',source,{'cases':cases,'duration':5500},5501,timeout=900)
(HERE/'build-results.json').write_text(json.dumps(raw,indent=2))
manifest=[]
for row in raw['cases']:
 assert row['normal_build_complete'] and not row['nonworking_signals'],row['id']
 text=row['blueprint'];decoded=json.loads(zlib.decompress(base64.b64decode(text[1:])));ent=decoded['blueprint']['entities']
 for suffix,data in [('txt',text+'\n'),('json',json.dumps(decoded,indent=2))]:(ROOT/'blueprints'/f'{row["id"]}.{suffix}').write_text(data)
 record={'id':row['id'],'base':base,'phase_seconds':row['phase_ticks']/60,'entities':len(ent),'added_entities':len(ent)-len(es),'entity_counts':dict(collections.Counter(e['name'] for e in ent)),'wires':len(decoded['blueprint'].get('wires',[])),'blueprint_sha256':hashlib.sha256(text.encode()).hexdigest(),'evidence_directory':raw['evidence_directory']}
 record.update(new_topology=False,geometry_family='existing directed crossbar64-source',scheduled_for_paired_traffic=record['phase_seconds'] in [15,30],traffic_test_scope='paired bank240 warm90s measure180s' if record['phase_seconds'] in [15,30] else 'native construction, empty-track clock smoke and static 12 OD only; no concurrent flow run')
 manifest.append(record);print(json.dumps(record),flush=True)
(HERE/'generation-manifest.json').write_text(json.dumps(manifest,indent=2))

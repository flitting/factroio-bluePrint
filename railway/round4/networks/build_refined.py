import json,pathlib,sys,base64,zlib
H=pathlib.Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'scripts'));from run import run
cases=json.loads((H/'refined-cases.json').read_text());result=run('r4-net-refined-build',H/'build.lua',{'cases':cases},61,timeout=600)
(H/'refined-build-results.json').write_text(json.dumps(result,indent=2))
for c in result['cases']:
 good=c['build_complete'] and not c['path_missing'] and not c['direction_conflicts']
 print(c['id'],'built',c['build_complete'],'remaining',len(c['remaining']),'ghosts',c['ghosts'],'expected',c['expected'],'missing',len(c['path_missing']),'opposite',len(c['direction_conflicts']),'signals',len(c.get('signals',[])),flush=True)
 if good:
  code=c['blueprint'];doc=json.loads(zlib.decompress(base64.b64decode(code[1:])))
  for d in [H,R/'blueprints']:(d/f'{c["id"]}.txt').write_text(code+'\n');(d/f'{c["id"]}.json').write_text(json.dumps(doc,indent=2))

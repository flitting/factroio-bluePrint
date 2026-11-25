#!/usr/bin/env python3
"""Isolated reproducible native-engine scenario runner, no global install changes."""
import argparse, hashlib, json, pathlib, subprocess, time
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[1]
def lua(v):
 if v is None:return 'nil'
 if isinstance(v,bool):return str(v).lower()
 if isinstance(v,(int,float)):return repr(v)
 if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
 if isinstance(v,list):return '{'+','.join(map(lua,v))+'}'
 return '{'+','.join('['+lua(k)+']='+lua(x) for k,x in v.items())+'}'
def run(name,script,config,ticks,timeout=180):
 source=pathlib.Path(script).read_text(); key=hashlib.sha256((source+json.dumps({'config':config,'ticks':ticks,'engine':'2.1.25-88022','mods':['base','quality','elevated-rails','space-age']},sort_keys=True)).encode()).hexdigest()[:16]
 out=ROOT/'experiments'/f'{name}-{key}'
 if (out/'script-output/result.json').exists() and (out/'request.json').exists() and json.loads((out/'request.json').read_text()).get('exit_code')==0:
  result=json.loads((out/'script-output/result.json').read_text());result['evidence_directory']=str(out.relative_to(ROOT));return result
 out.mkdir(parents=True,exist_ok=True);(out/'scenarios/probe').mkdir(parents=True,exist_ok=True);(out/'mods').mkdir(exist_ok=True)
 (out/'scenarios/probe/control.lua').write_text('local CONFIG='+lua(config)+'\n'+source)
 (out/'mods/mod-list.json').write_text(json.dumps({'mods':[{'name':n,'enabled':True} for n in ['base','quality','elevated-rails','space-age']]}))
 data=ROOT/'engine/factorio/data'; engine=ROOT/'engine/factorio/bin/x64/factorio'
 (out/'config.ini').write_text(f'[path]\nread-data={data}\nwrite-data={out}\n')
 command=[str(engine),'-c',str(out/'config.ini'),'--mod-directory',str(out/'mods'),'--test-scenario','probe','--test-ticks',str(ticks)]
 request={'command':command,'config':config,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'engine_version':subprocess.check_output([str(engine),'--version'],text=True)}
 start=time.monotonic();request.update(started_utc=datetime.now(timezone.utc).isoformat(),status='running')
 (out/'request.json').write_text(json.dumps(request,indent=2))
 try:
  with (out/'run.log').open('w') as log:
   proc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
 except subprocess.TimeoutExpired:
  request.update(exit_code=None,status='timeout',wall_seconds=time.monotonic()-start);(out/'request.json').write_text(json.dumps(request,indent=2));raise
 request.update(exit_code=proc.returncode,status='passed' if proc.returncode==0 else 'failed',wall_seconds=time.monotonic()-start);(out/'request.json').write_text(json.dumps(request,indent=2))
 if proc.returncode:raise RuntimeError(f'Engine failure: {out}/run.log')
 result=json.loads((out/'script-output/result.json').read_text());result['evidence_directory']=str(out.relative_to(ROOT));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--script',required=True);p.add_argument('--config',required=True);p.add_argument('--ticks',type=int,required=True);a=p.parse_args()
 print(json.dumps(run(a.name,a.script,json.loads(pathlib.Path(a.config).read_text()),a.ticks),indent=2))

#!/usr/bin/env python3
"""Round-three native screening runner with cached observer handles.

No assumption of equivalence is built into the results: equivalence.json is a
separate experimentally checked gate. Wall time is not a CPU metric.
"""
import argparse,hashlib,json,pathlib,shutil,subprocess,sys,time,math,base64,zlib
from datetime import datetime,timezone
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run import lua
from demand import WEIGHTS
sys.path.insert(0,str(ROOT/'round2/protocol'))
from run_protocol import engine_identity,summarize


def run_case(cfg,identity=None,timeout=600,resume_interrupted=False):
    identity=identity or engine_identity()
    source=(HERE/'bank.lua').read_text()
    payload={'protocol':'round4-expanded-terrain-v1','source':source,'config':cfg,'engine':identity}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    out=HERE/'experiments'/f'bank-{cfg["id"]}-{cfg["scenario"]}-{digest[:16]}'
    output=out/'script-output/result.json';request=out/'request.json'
    if output.exists() and request.exists():
        req=json.loads(request.read_text())
        if req.get('exit_code')==0 and req.get('case_sha256')==digest:
            result=json.loads(output.read_text());result['evidence_directory']=str(out.relative_to(ROOT));return result
    if request.exists() and json.loads(request.read_text()).get('status')=='running':
        if not resume_interrupted:
            raise RuntimeError(f'Unfinished prior request: {out}. Confirm its process ended, then use --resume-interrupted.')
        archive=out/'interrupted-attempts'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        archive.mkdir(parents=True,exist_ok=False)
        for name in ['request.json','run.log','factorio-current.log']:
            original=out/name
            if original.exists():shutil.copy2(original,archive/name)
        (archive/'resume-note.json').write_text(json.dumps({'reason':'Operator confirmed prior execution session was lost; restarting the entire unchanged case. Partial records are not a completed experiment.','resumed_utc':datetime.now(timezone.utc).isoformat()},indent=2))
    out.mkdir(parents=True,exist_ok=True);(out/'scenarios/probe').mkdir(parents=True,exist_ok=True);(out/'mods').mkdir(exist_ok=True)
    (out/'scenarios/probe/control.lua').write_text('local CONFIG='+lua(cfg)+'\n'+source)
    (out/'mods/mod-list.json').write_text(json.dumps({'mods':[{'name':n,'enabled':True} for n in ['base','quality','elevated-rails','space-age']]}))
    (out/'config.ini').write_text(f'[path]\nread-data={ROOT}/engine/factorio/data\nwrite-data={out}\n')
    cmd=[str(ROOT/'engine/factorio/bin/x64/factorio'),'-c',str(out/'config.ini'),'--mod-directory',str(out/'mods'),'--test-scenario','probe','--test-ticks',str(cfg['warmup']+cfg['duration']+1)]
    req={'case_sha256':digest,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'config':cfg,'engine':identity,'command':cmd,'started_utc':datetime.now(timezone.utc).isoformat(),'status':'running'}
    request.write_text(json.dumps(req,indent=2));start=time.monotonic()
    try:
        with (out/'run.log').open('w') as log:
            proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        req.update(exit_code=proc.returncode,status='passed' if proc.returncode==0 else 'failed',wall_seconds=time.monotonic()-start)
    except subprocess.TimeoutExpired:
        req.update(exit_code=None,status='timeout',wall_seconds=time.monotonic()-start);request.write_text(json.dumps(req,indent=2));raise
    request.write_text(json.dumps(req,indent=2))
    if proc.returncode!=0 or not output.exists():raise RuntimeError(f'Native test failed: {out}/run.log')
    result=json.loads(output.read_text());result['evidence_directory']=str(out.relative_to(ROOT));return result


def config(ident,seed=17,scenario='S1',bank=80,warmup=1800,duration=3600,loaded=False):
    near,straight,_=WEIGHTS.get(scenario,WEIGHTS['S1'])
    text=(ROOT/'blueprints'/f'{ident}.txt').read_text().strip()
    bp=json.loads(zlib.decompress(base64.b64decode(text[1:])))['blueprint']
    coords=[e['position'] for e in bp['entities']]
    span=max(max(p[a] for p in coords)-min(p[a] for p in coords) for a in ['x','y'])
    radius=max(5,math.ceil((span+80)/64))
    return {'core_chunk_radius':radius,'surface_size':max(24000,2*(120+(bank+2)*40+span+256)),'id':ident,'scenario':scenario,'seed':seed,'blueprint':(ROOT/'blueprints'/f'{ident}.txt').read_text().strip(),
            'bank':bank,'gap':40,'length':max(1400,120+(bank+2)*40),'spacing':8,'warmup':warmup,'duration':duration,
            'near':near,'straight':straight,'loaded':loaded,'exit_clearance':8,'entry_plane':80,'exit_plane':80,'sink_plane':400,
            'outlet_length':2400,'stop_offset':2300}


def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',required=True)
    p.add_argument('--seeds',nargs='+',type=int,default=[17]);p.add_argument('--scenarios',nargs='+',default=['S1'])
    p.add_argument('--bank',type=int,default=80);p.add_argument('--warmup',type=int,default=1800);p.add_argument('--duration',type=int,default=3600)
    p.add_argument('--timeout',type=int,default=600);p.add_argument('--loaded',action='store_true');p.add_argument('--output',required=True)
    p.add_argument('--resume-interrupted',action='store_true',help='After confirming old processes ended, archive unfinished logs and rerun identical cases.')
    args=p.parse_args();identity=engine_identity();rows=[]
    output=pathlib.Path(args.output)
    if not output.is_absolute():output=ROOT/output
    output.parent.mkdir(parents=True,exist_ok=True)
    for ident in args.ids:
        for scenario in args.scenarios:
            for seed in args.seeds:
                raw=run_case(config(ident,seed,scenario,args.bank,args.warmup,args.duration,args.loaded),identity,args.timeout,args.resume_interrupted)
                result=summarize(raw);rows.append(result);output.write_text(json.dumps(rows,indent=2,ensure_ascii=False))
                print(json.dumps({k:result[k] for k in ['id','scenario','seed','throughput','all_od_completed_in_window','damage_events','ticks_without_external_bank_by_origin','evidence_directory']}),flush=True)


if __name__=='__main__':main()

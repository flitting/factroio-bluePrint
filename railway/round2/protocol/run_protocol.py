#!/usr/bin/env python3
"""Second-round protocol runner. Old experiments and Lua remain unchanged.

Examples:
 python3 round2/protocol/run_protocol.py --mode bank --ids stacked-cloverleaf --clearances 8 40 80 --seeds 17 --warmup 1800 --duration 3600 --bank 80
 python3 round2/protocol/run_protocol.py --mode offered --ids stacked-cloverleaf --clearances 8 --rates 40 48 --seeds 17 31 47 --warmup 7200 --duration 36000
"""
import argparse, hashlib, json, pathlib, subprocess, sys, time
from datetime import datetime,timezone
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run import lua
from demand import generate,WEIGHTS

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def engine_identity():
    engine=ROOT/'engine/factorio/bin/x64/factorio'
    return {'version':subprocess.check_output([str(engine),'--version'],text=True),'binary_sha256':sha(engine),'mod_infos':{p.parent.name:sha(p) for p in sorted((ROOT/'engine/factorio/data').glob('*/info.json'))}}

def run_case(mode,cfg,identity,timeout):
    source=(HERE/(mode+'.lua')).read_text()
    payload={'protocol':'round2-independent-boundaries-v1','source':source,'config':cfg,'engine':identity}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    out=HERE/'experiments'/f'{mode}-{cfg["id"]}-{cfg["scenario"]}-{digest[:16]}'
    result_path=out/'script-output/result.json'; reqpath=out/'request.json'
    if result_path.exists() and reqpath.exists():
        req=json.loads(reqpath.read_text())
        if req.get('exit_code')==0 and req.get('case_sha256')==digest:
            res=json.loads(result_path.read_text());res['evidence_directory']=str(out.relative_to(ROOT));return res
    out.mkdir(parents=True,exist_ok=True);(out/'scenarios/probe').mkdir(parents=True,exist_ok=True);(out/'mods').mkdir(exist_ok=True)
    (out/'scenarios/probe/control.lua').write_text('local CONFIG='+lua(cfg)+'\n'+source)
    (out/'mods/mod-list.json').write_text(json.dumps({'mods':[{'name':n,'enabled':True} for n in ['base','quality','elevated-rails','space-age']]}))
    (out/'config.ini').write_text(f'[path]\nread-data={ROOT}/engine/factorio/data\nwrite-data={out}\n')
    command=[str(ROOT/'engine/factorio/bin/x64/factorio'),'-c',str(out/'config.ini'),'--mod-directory',str(out/'mods'),'--test-scenario','probe','--test-ticks',str(cfg['warmup']+cfg['duration']+1)]
    req={'case_sha256':digest,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'config':cfg,'engine':identity,'command':command,'started_utc':datetime.now(timezone.utc).isoformat(),'status':'running'}
    reqpath.write_text(json.dumps(req,indent=2));start=time.monotonic()
    try:
        with (out/'run.log').open('w') as log:
            proc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        req.update(exit_code=proc.returncode,status='passed' if proc.returncode==0 else 'failed',wall_seconds=time.monotonic()-start)
    except subprocess.TimeoutExpired:
        req.update(exit_code=None,status='timeout',wall_seconds=time.monotonic()-start);reqpath.write_text(json.dumps(req,indent=2));raise
    reqpath.write_text(json.dumps(req,indent=2))
    if proc.returncode!=0 or not result_path.exists():raise RuntimeError(f'Native test failed; see {out}/run.log')
    res=json.loads(result_path.read_text());assert res['engine']['base']=='2.1.25';res['evidence_directory']=str(out.relative_to(ROOT));return res

def summarize(res):
    cfg=res['config'];start=cfg['warmup'];end=start+cfg['duration'];mins=cfg['duration']/3600
    rows=res['records'];names=['N','E','S','W'];ods={}
    ncount=0
    for o in range(1,5):
        for d in range(1,5):
            if o==d:continue
            rr=[r for r in rows if r['origin']==o and r['destination']==d]
            done=[r for r in rr if start<=r.get('complete_tick',end)<end]
            ncount+=len(done)
            arrived=sum(start<=r['arrival_tick']<end for r in rr)
            begin=sum(r['arrival_tick']<start and r.get('complete_tick',end)>=start for r in rr)
            finish=sum(r['arrival_tick']<end and r.get('complete_tick',end)>=end for r in rr)
            ods[f'{names[o-1]}-{names[d-1]}']={'measured_completed':len(done),'completed_per_minute':len(done)/mins,'arrivals_in_window':arrived,'backlog_before_window':begin,'backlog_after_window':finish,'backlog_delta':finish-begin,'longest_uncompleted_seconds':max([0]+[(end-r['arrival_tick'])/60 for r in rr if r['arrival_tick']<end and r.get('complete_tick',end)>=end]),'last_complete_tick':max([-1]+[r['complete_tick'] for r in rr if 'complete_tick' in r])}
            assert finish-begin==arrived-len(done),(o,d,finish,begin,arrived,len(done))
    assert ncount==res['completed']
    per_origin={names[o-1]:{'spawned_in_window':sum(start<=r.get('spawn_tick',end)<end for r in rows if r['origin']==o),'completed_in_window':sum(start<=r.get('complete_tick',end)<end for r in rows if r['origin']==o)} for o in range(1,5)}
    return {'id':cfg['id'],'mode':'offered' if 'demand_sha256' in res else 'bank','scenario':cfg['scenario'],'seed':cfg['seed'],'warmup':start,'duration':cfg['duration'],'exit_clearance':cfg['exit_clearance'],'exit_plane':cfg['exit_plane'],'sink_plane':cfg['sink_plane'],'rate':cfg.get('offered_rate'),'throughput':ncount/mins,'od':ods,'per_origin':per_origin,'minimum_external_bank_by_origin':res.get('entry_supply_min'),'ticks_without_external_bank_by_origin':res.get('no_upstream_ticks'),'damage_events':res['damage_events'],'damaged_amount':res['damaged_amount'],'no_completion_ticks':res['no_completion_ticks'],'all_od_completed_in_window':all(v['measured_completed']>0 for v in ods.values()),'uncompleted_requests':res['remaining'],'conservation_verified':True,'evidence_directory':res['evidence_directory'],'claims':'Finite native observation; no maximum-capacity or deadlock-free proof; no CPU timing.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['bank','offered'],default='bank');p.add_argument('--ids',nargs='+',default=['stacked-cloverleaf']);p.add_argument('--scenarios',nargs='+',default=['S1']);p.add_argument('--seeds',nargs='+',type=int,default=[17]);p.add_argument('--clearances',nargs='+',type=int,default=[8,40,80]);p.add_argument('--rates',nargs='+',type=float,default=[40]);p.add_argument('--warmup',type=int,default=1800);p.add_argument('--duration',type=int,default=3600);p.add_argument('--bank',type=int,default=80);p.add_argument('--spacing',type=int,default=8);p.add_argument('--gap',type=int,default=40);p.add_argument('--sink',type=int,default=400);p.add_argument('--exit-plane',type=int,default=80);p.add_argument('--timeout',type=int,default=300);p.add_argument('--arrival-end',type=int,default=None,help='Absolute tick after which offered requests stop; remaining runtime is a drain/recovery test, not stationary capacity');p.add_argument('--loaded',action='store_true');p.add_argument('--output',default='latest-summary.json');a=p.parse_args()
    identity=engine_identity();out=[]
    for ident in a.ids:
        bp=ROOT/'blueprints'/f'{ident}.txt'
        if not bp.exists():bp=pathlib.Path(ident);ident=bp.stem
        blueprint=bp.read_text().strip()
        for scenario in a.scenarios:
            for seed in a.seeds:
                for clearance in a.clearances:
                    assert clearance>0 and a.sink>a.exit_plane+40 and a.sink>clearance+a.spacing+40
                    for rate in (a.rates if a.mode=='offered' else [None]):
                        near,straight,_=WEIGHTS.get(scenario,WEIGHTS['S1'])
                        cfg={'id':ident,'scenario':scenario,'seed':seed,'blueprint':blueprint,'bank':a.bank,'gap':a.gap,'length':max(1400,120+(a.bank+2)*a.gap) if a.mode=='bank' else 1400,'spacing':a.spacing,'warmup':a.warmup,'duration':a.duration,'near':near,'straight':straight,'loaded':a.loaded,'exit_clearance':clearance,'entry_plane':80,'exit_plane':a.exit_plane,'sink_plane':a.sink,'outlet_length':2400,'stop_offset':2300}
                        if a.mode=='offered':
                            trace=generate(scenario,seed,rate,a.duration,a.warmup)
                            if a.arrival_end is not None:
                                assert 0<=a.arrival_end<a.warmup+a.duration
                                trace['events']=[v for v in trace['events'] if v['tick']<=a.arrival_end]
                                trace['arrival_stop_tick']=a.arrival_end;trace.pop('sha256',None)
                                trace['sha256']=hashlib.sha256(json.dumps(trace,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                            cfg.update(demand=trace,spawn_offset=600,offered_rate=rate,arrival_stop_tick=a.arrival_end)
                        res=run_case(a.mode,cfg,identity,a.timeout);s=summarize(res);out.append(s)
                        print(json.dumps({k:s[k] for k in ['id','mode','scenario','seed','exit_clearance','throughput','all_od_completed_in_window','damage_events','ticks_without_external_bank_by_origin','evidence_directory']}),flush=True)
                        (HERE/a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

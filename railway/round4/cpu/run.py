#!/usr/bin/env python3
"""Native CPU benchmark at a common low offered load, from a genuinely warmed save.

Use --prepare-only while other experiments run. Invoke actual CPU timing only
once other Factorio processes are stopped. --smoke marks concurrent timing as
non-comparative even when timers are technically parsed successfully.
"""
import argparse,hashlib,json,pathlib,subprocess,sys,time,csv,re,statistics,signal,zipfile,math,base64,zlib
from datetime import datetime,timezone
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'round2/protocol'));sys.path.insert(0,str(ROOT/'scripts'))
from run_protocol import engine_identity,lua
from demand import generate

TIMERS=['trainPathFinder','trains','scriptUpdate','wholeUpdate']

def prepare(ident,seed,rate,warmup,ticks,clearance,spacing,sink,identity,timeout):
    path=ROOT/'blueprints'/f'{ident}.txt'
    if not path.exists():path=pathlib.Path(ident);ident=path.stem
    blueprint=path.read_text().strip()
    trace=generate('S1',seed,rate,ticks+60,warmup)
    cfg={'id':ident,'scenario':'S1','seed':seed,'blueprint':blueprint,'length':1400,'spacing':spacing,'warmup':warmup,
         'duration':ticks+60,'preparation_method':'private-loopback-server-v2','map_gen_seed':1,'profile_ticks':ticks,'loaded':False,'exit_clearance':clearance,'entry_plane':80,
         'exit_plane':80,'sink_plane':sink,'outlet_length':2400,'stop_offset':2300,'spawn_offset':600,'offered_rate':rate,'demand':trace}
    bp=json.loads(zlib.decompress(base64.b64decode(blueprint[1:])))['blueprint']
    coords=[e['position'] for e in bp['entities']]
    span=max(max(p[a] for p in coords)-min(p[a] for p in coords) for a in ['x','y'])
    cfg.update(core_chunk_radius=max(5,math.ceil((span+80)/64)),surface_size=max(24000,2*(2400+span+256)))
    source=(HERE/'profile.lua').read_text()
    h=hashlib.sha256(json.dumps({'cfg':cfg,'source':source,'engine':identity,'protocol':'round4-expanded-offered-warmed-profile-v1'},sort_keys=True).encode()).hexdigest()
    out=HERE/'profiles'/f'{ident}-{h[:16]}'
    reqpath=out/'request.json';save=out/'saves/warmed.zip'
    if reqpath.exists() and save.exists():
        req=json.loads(reqpath.read_text())
        if req.get('case_sha256')==h and req.get('prepare_exit_code')==0:return out,req
    out.mkdir(parents=True,exist_ok=True);(out/'scenarios/probe').mkdir(parents=True,exist_ok=True);(out/'mods').mkdir(exist_ok=True);(out/'saves').mkdir(exist_ok=True)
    (out/'scenarios/probe/control.lua').write_text('local CONFIG='+lua(cfg)+'\n'+source)
    (out/'mods/mod-list.json').write_text(json.dumps({'mods':[{'name':n,'enabled':True} for n in ['base','quality','elevated-rails','space-age']]}))
    (out/'config.ini').write_text(f'[path]\nread-data={ROOT}/engine/factorio/data\nwrite-data={out}\n')
    base=[str(ROOT/'engine/factorio/bin/x64/factorio'),'-c',str(out/'config.ini'),'--mod-directory',str(out/'mods')]
    server_settings=json.loads((ROOT/'engine/factorio/data/server-settings.example.json').read_text())
    server_settings.update({'name':'isolated-rail-profile-prewarm','visibility':{'public':False,'lan':False},'require_user_verification':False,'auto_pause':False,'autosave_interval':0,'non_blocking_saving':False})
    (out/'server-settings.json').write_text(json.dumps(server_settings))
    cmd=base+['--start-server-load-scenario','probe','--server-settings',str(out/'server-settings.json'),'--bind','127.0.0.1:0','--map-gen-seed','1']
    req={'case_sha256':h,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'config':cfg,'engine':identity,'base_command':base,'prepare_command':cmd,'started_utc':datetime.now(timezone.utc).isoformat()}
    reqpath.write_text(json.dumps(req,indent=2));start=time.monotonic()
    with (out/'prepare.log').open('w') as log:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
        ready=False
        try:
            while time.monotonic()-start<timeout:
                if save.exists():
                    try:
                        with zipfile.ZipFile(save) as archive:ready=archive.testzip() is None
                    except (zipfile.BadZipFile,EOFError):pass
                    if ready:break
                if proc.poll() is not None:break
                time.sleep(.1)
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
    req.update(prepare_exit_code=proc.returncode,prepare_wall_seconds=time.monotonic()-start,save=str(save),save_exists=save.exists(),save_zip_verified=ready)
    reqpath.write_text(json.dumps(req,indent=2))
    assert proc.returncode==0 and save.exists() and ready,f'Preparation/save failed: {out}/prepare.log'
    req['save_sha256']=hashlib.sha256(save.read_bytes()).hexdigest();reqpath.write_text(json.dumps(req,indent=2))
    return out,req

def parse_log(path,measured_ticks):
    lines=path.read_text().splitlines();runs=[];header=None;rows=[]
    for line in lines:
        if line.startswith('run '):
            if rows:runs.append(rows);rows=[]
        elif line.startswith('tick,'):header=next(csv.reader([line]))
        elif re.match(r'^t\d+,',line) and header:rows.append(dict(zip(header,next(csv.reader([line])))))
    if rows:runs.append(rows)
    outer=[float(x) for x in re.findall(r'Performed \d+ updates in ([\d.]+) ms',path.read_text())]
    results=[]
    for i,rr in enumerate(runs):
        measured=rr[:measured_ticks]
        totals={k:sum(int(r[k]) for r in measured) for k in TIMERS}
        ms=sum(int(r['wholeUpdate']) for r in rr)/1e6;reported=outer[i] if i<len(outer) else None
        results.append({'run':i+1,'ticks':len(measured),'native_ticks':len(rr),'ns_per_tick':{k:v/len(measured) for k,v in totals.items()},'totals_ns':totals,
                        'whole_sum_ms':ms,'engine_reported_ms':reported,'timer_scale_verified':reported is not None and abs(ms-reported)/reported<.02})
    return results

def benchmark(out,req,runs,timeout,smoke):
    cfg=req['config'];flowpath=out/'script-output/profile-flows.jsonl'
    if flowpath.exists():
        archive=flowpath.with_name('profile-flows.previous-'+str(time.time_ns())+'.jsonl');flowpath.rename(archive)
    cmd=req['base_command']+['--benchmark',req['save'],'--benchmark-ticks',str(cfg['profile_ticks']+1),'--benchmark-runs',str(runs),'--benchmark-verbose','all']
    logfile=out/('smoke-benchmark.log' if smoke else 'benchmark.log')
    with logfile.open('w') as log:proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    req.update(benchmark_command=cmd,benchmark_exit_code=proc.returncode,cpu_evidence='smoke_only_possible_concurrent_engine_load' if smoke else 'serial_run_requested_by_operator')
    (out/'request.json').write_text(json.dumps(req,indent=2))
    assert proc.returncode==0,f'Benchmark failed: {logfile}'
    timers=parse_log(logfile,cfg['profile_ticks']);flows=[json.loads(l) for l in flowpath.read_text().splitlines() if l.strip()]
    assert len(timers)==runs and all(t['ticks']==cfg['profile_ticks'] and t['native_ticks']==cfg['profile_ticks']+1 and t['timer_scale_verified'] for t in timers),(timers,runs)
    assert len(flows)==runs and all(f['measurement_ticks']==cfg['profile_ticks'] for f in flows),(len(flows),runs)
    assert all(f['first_tick']==flows[0]['first_tick'] and f['last_tick']==flows[0]['last_tick'] and f['records']==flows[0]['records'] for f in flows),'Native repeated runs diverged'
    for t,f in zip(timers,flows):t['ns_per_completed_train']={k:(v/f['completed'] if f['completed'] else None) for k,v in t['totals_ns'].items()}
    result={'id':cfg['id'],'rate':cfg['offered_rate'],'seed':cfg['seed'],'warmup_ticks':cfg['warmup'],'profile_ticks':cfg['profile_ticks'],
            'protocol':'round4-expanded-offered-warmed-profile-v1','evidence_directory':str(out.relative_to(ROOT)),'smoke_only':smoke,
            'timers':timers,'flows':[{k:v for k,v in f.items() if k!='records'} for f in flows],
            'repeated_flow_identical':True,'timing_means_ns_per_tick':{k:statistics.mean(t['ns_per_tick'][k] for t in timers) for k in TIMERS},
            'limits':['Whole test map including common lines, source creation, native initial schedules and ongoing repaths; no core-only subtraction.',
                      'No engine initial loading, warmup or save cost included in tick timers.',
                      'Native timing scopes may nest; do not add trainPathFinder and trains.',
                      'Repeated identical saves estimate hardware timing noise; independent traffic seeds require separate cases.',
                      'Final JSON output is in one extra unmeasured tick; timer scale check still uses all native ticks.',
                      'No direct automatic repath count is claimed.']}
    (out/('smoke-summary.json' if smoke else 'summary.json')).write_text(json.dumps(result,indent=2))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',default=['stacked-cloverleaf']);p.add_argument('--rate',type=float,default=48);p.add_argument('--seed',type=int,default=17);p.add_argument('--warmup',type=int,default=7200);p.add_argument('--ticks',type=int,default=7200);p.add_argument('--runs',type=int,default=3);p.add_argument('--clearance',type=int,default=8);p.add_argument('--spacing',type=int,default=8);p.add_argument('--sink',type=int,default=400);p.add_argument('--prepare-only',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
    identity=engine_identity();summary=[]
    for ident in a.ids:
        out,req=prepare(ident,a.seed,a.rate,a.warmup,a.ticks,a.clearance,a.spacing,a.sink,identity,a.timeout)
        print(json.dumps({'id':req['config']['id'],'prepared':str(out.relative_to(ROOT)),'save_exists':True}),flush=True)
        if not a.prepare_only:
            r=benchmark(out,req,a.runs,a.timeout,a.smoke);summary.append(r)
            print(json.dumps({'id':r['id'],'flow_completed':[f['completed'] for f in r['flows']],'ticks_per_run':a.ticks,'repeated_flow_identical':True,'timer_scale_verified':True,'smoke_only':a.smoke}),flush=True)
    if summary:(HERE/('profile-smoke-summary.json' if a.smoke else 'profile-comparison.json')).write_text(json.dumps(summary,indent=2))
if __name__=='__main__':main()

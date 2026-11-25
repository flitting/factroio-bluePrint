#!/usr/bin/env python3
"""Audit frozen native observations and prepare compact, reproducible round4 data.

This program does not run Factorio or change tested blueprints. A partial build
is labelled partial; --require-complete is the publication gate.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, base64, copy, hashlib, json, math, shutil, statistics, zlib

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'round4'
OUT = HERE / 'final'
D = 'r3-sig-turbine2-dense2'
T = 'r4-dir-trident32-32'
S = 'r2-sig-stacked-cloverleaf-all4-clean'
NAMES = 'NESW'
LABELS = {
    D: '涡轮二型·364灯对照', T: '三分叉私有连接网', S: '叠层苜蓿叶·169灯对照',
    'r4-sig-crossover-displaced-left-turn-d4': '交叉移位左转·d4',
    'r4-sig-partially-unrolled-cloverleaf-d4': '部分展开苜蓿叶·d4',
    'r4-sig-three-chunk-square-d4': '三块方形·d4',
}

def read(rel, default=None):
    p = ROOT / rel
    return json.loads(p.read_text()) if p.exists() else default

def write(rel, obj):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def case_details(row):
    path = ROOT / row['evidence_directory']
    raw = json.loads((path / 'script-output/result.json').read_text())
    req = json.loads((path / 'request.json').read_text())
    c = req['config']; records = raw['records']
    assert raw['config']=={k:v for k,v in c.items() if k!='blueprint'} and raw['id']==c['id'] and raw['seed']==c['seed']
    a, b = c['warmup'], c['warmup'] + c['duration']
    inside = lambda tick: sum(r.get('entry_tick', b+1) < tick and r.get('complete_tick', b+1) >= tick for r in records)
    done = [r for r in records if a <= r.get('complete_tick', -1) < b]
    entered = [r for r in records if a <= r.get('entry_tick', -1) < b]
    assert len(done) == raw['completed']
    assert len(records) == c['bank'] * 4
    assert len({r['id'] for r in records}) == len(records)
    assert len(entered) - len(done) == inside(b) - inside(a)
    assert raw['retired'] + raw['active_world'] == len(records)
    assert raw['total_completed'] + raw['remaining'] == len(records)
    assert all(r['complete_tick'] >= r['entry_tick'] >= r['spawn_tick'] >= r['arrival_tick'] for r in records if 'complete_tick' in r)
    for o in range(1,5):
        entered_origin = sorted((r for r in records if r['origin'] == o and 'entry_tick' in r), key=lambda r:r['entry_tick'])
        requested_origin = [r['id'] for r in records if r['origin']==o]
        assert [r['id'] for r in entered_origin] == requested_origin[:len(entered_origin)], 'External FIFO prefix changed or a request was skipped'
    delays = sorted((r['complete_tick']-r['entry_tick'])/60 for r in done)
    od = {}
    for o in range(1,5):
        for d in range(1,5):
            if o == d: continue
            ticks = sorted(r['complete_tick'] for r in done if r['origin']==o and r['destination']==d)
            edges = [a] + ticks + [b]
            od[NAMES[o-1]+'-'+NAMES[d-1]] = {
                'completed':len(ticks),
                'max_observed_gap_seconds_including_censored_window_edges':max((y-x)/60 for x,y in zip(edges,edges[1:])),
            }
    bins = []
    for lo in range(a,b,3600):
        hi = min(lo+3600,b)
        n = sum(lo <= r['complete_tick'] < hi for r in done)
        bins.append({'from_tick':lo,'to_tick_exclusive':hi,'completed':n,'trains_per_minute':n/((hi-lo)/3600)})
    trace = [(r['id'],r['origin'],r['destination'],r['arrival_tick']) for r in records]
    return {
        'id':row['id'],'name_zh':LABELS.get(row['id'],row['id']), 'seed':row['seed'],
        'bank_per_origin':c['bank'], 'warmup_ticks':a,'measurement_ticks':b-a,
        'completed':len(done),'throughput':len(done)/((b-a)/3600),
        'entered_in_window':len(entered),'inside_start':inside(a),'inside_end':inside(b),
        'inventory_balance_verified':True,'external_entry_FIFO_verified':True,
        'all_12_od_served':all(v['completed'] for v in od.values()),
        'source_banks_never_empty':all(x==0 for x in raw['no_upstream_ticks']),
        'minimum_external_bank_by_origin':raw['entry_supply_min'],
        'damage_events':raw['damage_events'],
        'per_origin_completed':{n:sum(r['origin']==i+1 for r in done) for i,n in enumerate(NAMES)},
        'per_destination_completed':{n:sum(r['destination']==i+1 for r in done) for i,n in enumerate(NAMES)},
        'od':od,'minute_bins':bins,
        'completed_cohort_mean_transit_seconds':statistics.mean(delays) if delays else None,
        'completed_cohort_p95_transit_seconds':delays[math.ceil(.95*len(delays))-1] if delays else None,
        'demand_trace_sha256':sha(json.dumps(trace,separators=(',',':')).encode()),
        'blueprint_sha256':sha((c['blueprint'].strip()+'\n').encode()),
        'protocol_source_sha256':req['source_sha256'],
        'engine_identity_sha256':sha(json.dumps(req['engine'],sort_keys=True,separators=(',',':')).encode()),
        'comparison_settings':{k:c.get(k) for k in ['scenario','bank','gap','length','spacing','warmup','duration','near','straight','loaded','exit_clearance','entry_plane','exit_plane','sink_plane','outlet_length','stop_offset']},
        'evidence_directory':row['evidence_directory'],
    }

def aggregate(rows, geometries):
    if rows:
        assert len({json.dumps(r['comparison_settings'],sort_keys=True) for r in rows})==1, 'Different traffic protocols cannot be pooled'
        assert len({(r['protocol_source_sha256'],r['engine_identity_sha256']) for r in rows})==1
    result=[]
    for ident in sorted({r['id'] for r in rows}):
        group=sorted((r for r in rows if r['id']==ident),key=lambda r:r['seed'])
        vals=[r['throughput'] for r in group]
        g=geometries[ident]
        result.append({'id':ident,'name_zh':LABELS.get(ident,ident),'seeds':[r['seed'] for r in group],
            'n':len(group),'mean_trains_per_minute':statistics.mean(vals),
            'sample_sd':statistics.stdev(vals) if len(vals)>1 else None,
            'seed_values':{str(r['seed']):r['throughput'] for r in group},
            'area_tiles2':g['area'],'signals':g['signals'],'entities':g['entities'],
            'all_12_od_served':all(r['all_12_od_served'] for r in group),
            'zero_damage':all(r['damage_events']==0 for r in group),
            'all_source_banks_nonempty':all(r['source_banks_never_empty'] for r in group),
            'evidence_directories':[r['evidence_directory'] for r in group]})
    return sorted(result,key=lambda r:-r['mean_trains_per_minute'])

def paired(rows):
    by={(r['id'],r['seed']):r for r in rows}
    pairs=[]
    for seed in sorted({r['seed'] for r in rows}):
        if (D,seed) not in by or (T,seed) not in by: continue
        a,b=by[D,seed],by[T,seed]
        for key in ['bank_per_origin','warmup_ticks','measurement_ticks','demand_trace_sha256','protocol_source_sha256','comparison_settings','engine_identity_sha256']:
            assert a[key]==b[key],(seed,key)
        pairs.append({'seed':seed,'reference':a['throughput'],'trident':b['throughput'],
            'difference':b['throughput']-a['throughput'],
            'relative_difference_percent':100*(b['throughput']/a['throughput']-1),
            'completed_difference':b['completed']-a['completed'],
            'identical_demand_verified':True,
            'origin_rate_differences':{n:(b['per_origin_completed'][n]-a['per_origin_completed'][n])/(a['measurement_ticks']/3600) for n in NAMES},
            'reference_origin_rates':{n:a['per_origin_completed'][n]/(a['measurement_ticks']/3600) for n in NAMES},
            'trident_origin_rates':{n:b['per_origin_completed'][n]/(b['measurement_ticks']/3600) for n in NAMES}})
    if not pairs:return {'pairs':[]}
    ma=statistics.mean(p['reference'] for p in pairs);mb=statistics.mean(p['trident'] for p in pairs)
    return {'pairs':pairs,'reference_mean':ma,'trident_mean':mb,
            'mean_paired_difference':mb-ma,'relative_gain_percent':100*(mb/ma-1),
            'wins':sum(p['difference']>0 for p in pairs),'n':len(pairs),
            'mean_reference_origin_rates':{n:statistics.mean(p['reference_origin_rates'][n] for p in pairs) for n in NAMES},
            'mean_trident_origin_rates':{n:statistics.mean(p['trident_origin_rates'][n] for p in pairs) for n in NAMES},
            'mean_origin_rate_differences':{n:statistics.mean(p['origin_rate_differences'][n] for p in pairs) for n in NAMES}}

def make_book():
    labels=[(T,'三分叉私有连接网｜大型研究候选'),(D,'涡轮二型｜364灯紧凑对照'),(S,'叠层苜蓿叶｜169灯紧凑对照')]
    leaves=[];manifest=[]
    frozen=read('round4/holdout-plan.json')['blueprint_sha256']|read('round4/long-selection-plan.json')['blueprint_sha256']
    for i,(ident,label) in enumerate(labels):
        text=(ROOT/'blueprints'/f'{ident}.txt').read_text()
        assert sha(text.encode())==frozen[ident], 'Export input changed after the frozen native tests'
        source=json.loads(zlib.decompress(base64.b64decode(text.strip()[1:])))['blueprint']
        leaf=copy.deepcopy(source);leaf['label']=label
        assert {k:v for k,v in leaf.items() if k!='label'}=={k:v for k,v in source.items() if k!='label'}
        leaves.append({'index':i,'blueprint':leaf})
        manifest.append({'id':ident,'label':label,'entities':len(leaf['entities']),
            'only_label_changed':True,'source_blueprint_sha256':sha(text.encode()),
            'entity_sha256':sha(json.dumps(leaf['entities'],sort_keys=True,separators=(',',':')).encode())})
    book={'blueprint_book':{'item':'blueprint-book','label':'铁路研究第四轮｜新拓扑与紧凑对照',
        'description':'Factorio2.1.25原生1机车4空货厢。三分叉候选有吞吐增益，但面积约为涡轮对照46倍；有限均匀需求测试不能证明稳态容量、任意需求无死锁或全局最优。',
        'version':max(x['blueprint']['version'] for x in leaves),'active_index':0,'blueprints':leaves}}
    text='0'+base64.b64encode(zlib.compress(json.dumps(book,ensure_ascii=False,separators=(',',':')).encode(),9)).decode()+'\n'
    assert json.loads(zlib.decompress(base64.b64decode(text.strip()[1:])))==book
    (OUT/'junctions-round4.txt').write_text(text)
    write('round4/final/junctions-round4.json',book)
    shutil.copyfile(ROOT/'blueprints'/f'{T}.txt',OUT/'trident-research.txt')
    write('round4/final/blueprint-manifest.json',{'book_sha256':sha(text.encode()),'entries':manifest,
        'all_non_label_blueprint_fields_preserved':True,'standalone_trident_byte_identical':True})
    write('round4/final/book-import-request.json',{'books':[{'file':'junctions-round4.txt',
        'label':book['blueprint_book']['label'],'code':text.strip(),'entries':manifest,
        'total_entities':sum(x['entities'] for x in manifest)}]})

def blockage_details():
    rows=read('round4/hol-paired.json',[]);by={};pairs=[]
    for r in rows:
        raw=read(r['evidence_directory']+'/script-output/result.json')
        r['retired']=raw['retired'];by[(r['id'],r['seed'],r['block_enabled'])]=raw
    for ident,seed in sorted({(r['id'],r['seed']) for r in rows}):
        if (ident,seed,False) not in by or (ident,seed,True) not in by:continue
        a,b=by[ident,seed,False],by[ident,seed,True]
        assert [(r['id'],r['origin'],r['destination']) for r in a['records']]==[(r['id'],r['origin'],r['destination']) for r in b['records']]
        records_a={r['id']:r for r in a['records']};records_b={r['id']:r for r in b['records']}
        cohort=[r['id'] for r in a['records'] if r['destination']!=4]
        if not all('complete_tick' in records_a[i] and 'complete_tick' in records_b[i] for i in cohort):continue
        delay=sorted((records_b[i]['complete_tick']-records_a[i]['complete_tick'])/60 for i in cohort)
        pairs.append({'id':ident,'seed':seed,'cohort_count':len(cohort),
            'cohort_definition':'Every requested train whose destination is not W, including unaffected preclosure completions; identical logical IDs in open and closed runs. Negative differences retained.',
            'mean_added_completion_seconds':statistics.mean(delay),'median_added_completion_seconds':statistics.median(delay),
            'p95_added_completion_seconds':delay[math.ceil(.95*len(delay))-1],
            'negative_differences':sum(x<0 for x in delay),'zero_differences':sum(x==0 for x in delay),
            'positive_differences':sum(x>0 for x in delay),
            'cohort_ids_sha256':sha(json.dumps(cohort,separators=(',',':')).encode())})
    return rows,pairs

def main():
    p=argparse.ArgumentParser();p.add_argument('--require-complete',action='store_true');a=p.parse_args()
    OUT.mkdir(exist_ok=True)
    make_book()
    geo={}
    for f in ['round4/reference-graphs.json','round4/directed/trident-structural-audit.json',
              'round4/signals/validation-summary.json','round4/external/signals/validation-summary.json']:
        for r in read(f)['cases']:geo[r['id']]={k:r[k] for k in ['area','signals','entities','bounds','all_12_od','all_signals_working']}
    selection=read('round4/long-selection.json',[])+read('round4/directed/long-trident.json',[])
    holdout=read('round4/holdout-reference.json',[])+read('round4/holdout-trident.json',[])
    if a.require_complete:
        assert len(selection)==18 and len(holdout)==6
        assert len({(r['id'],r['seed']) for r in selection})==18
        assert len({(r['id'],r['seed']) for r in holdout})==6
        assert all({r['seed'] for r in selection if r['id']==ident}=={17,31,47} for ident in {r['id'] for r in selection})
        assert all({r['seed'] for r in holdout if r['id']==ident}=={211,307,401} for ident in [D,T])
    selection=[case_details(r) for r in selection];holdout=[case_details(r) for r in holdout]
    for r in selection+holdout:
        assert r['all_12_od_served'] and r['source_banks_never_empty'] and r['damage_events']==0
    cpu=[]
    for r in read('round4/cpu/profile-comparison.json',[]):
        assert r['repeated_flow_identical'] and not r['smoke_only'] and len(r['timers'])==3
        timers={}
        for key in ['trainPathFinder','trains','scriptUpdate','wholeUpdate']:
            vals=[t['ns_per_tick'][key]/1000 for t in r['timers']]
            timers[key]={'unit':'microseconds/tick','mean':statistics.mean(vals),
                'sample_sd':statistics.stdev(vals),'repeat_values':vals}
        cpu.append({'id':r['id'],'timers':timers,'flows':r['flows'],
            'repeated_flow_identical':True,'evidence_directory':r['evidence_directory']})
    if cpu:
        assert len({r['flows'][0]['demand_sha256'] for r in cpu})==1
    block_rows,block_pairs=blockage_details()
    if a.require_complete:
        assert {r['id'] for r in cpu}=={D,T}
        book_gate=read('round4/final/book-validation.json');assert book_gate['passed']
        assert read(book_gate['evidence_directory']+'/request.json')['config']==read('round4/final/book-import-request.json'), 'Book native import was for different bytes'
        assert len(read('round4/hol-paired.json'))==4
        assert {(r['id'],r['seed'],r['block_enabled']) for r in block_rows}=={(i,17,b) for i in [D,T] for b in [False,True]}
        assert len(block_pairs)==2 and len({r['cohort_ids_sha256'] for r in block_pairs})==1
        assert all(r['complete_drain_observed'] and r['damage_events']==0 and r['retired']==320 for r in block_rows)
        all_exit=read('round4/all-exits-drain.json')
        assert len(all_exit)==1 and all_exit[0]['id']==T and all_exit[0]['seed']==17
        assert all(r['complete_drain_observed'] and r['damage_events']==0 and r['total_completed']==r['total_requested']==r['retired']==320 for r in all_exit)
    index=read('round4/results-index.json',{})
    result={
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'publication_gate_complete':a.require_complete,
        'engine':'Factorio Headless2.1.25 build88022',
        'scope':{'external_ports':8,'incoming_per_compass_direction':1,'outgoing_per_compass_direction':1,
            'train':'1 locomotive +4 empty cargo wagons; normal quality; nuclear fuel; braking1..7',
            'demand':'12 non-U-turn OD, uniform near/straight/far; independent FIFO at each incoming bank',
            'physics':'native train physics, pathfinder, signals and collisions; no speed writes or teleports',
            'primary_metric':'finite saturated full-train completions per game minute, not proven maximum stable service rate',
            'area_metric':'AABB of native transformed primary and secondary entity boxes, including all candidate adapters, buffers and elevation projection; common fixture excluded'},
        'search_counts':{k:v for k,v in index.items() if k not in ['cases','incomplete']},
        'selection_protocol':{'bank':150,'warmup_ticks':3600,'measurement_ticks':10800,'seeds':[17,31,47]},
        'selection':aggregate(selection,geo),'selection_pair':paired(selection),'selection_case_details':selection,
        'holdout_protocol':read('round4/holdout-plan.json'),
        'holdout':aggregate(holdout,geo),'holdout_pair':paired(holdout),'holdout_case_details':holdout,
        'trident_area_ratio_to_reference':geo[T]['area']/geo[D]['area'],
        'native_geometry':geo,
        'cpu':cpu,
        'W_blockage':block_rows,'W_open_destination_cohort_delays':block_pairs,
        'all_exits_recovery':read('round4/all-exits-drain.json',[]),
        'batching':read('round4/batching/paired-comparison.json',{}),
        'capacity_diagnostics':read('round4/external/capacity-reference.json',{}),
        'limits':[
            'Selection and holdout have different bank sizes/windows and are never pooled.',
            'Small paired seed samples; observed gain is not global optimality or an asymptotic capacity estimate.',
            'Only uniform mixed-OD throughput is independently confirmed in this round; biased mixes, loaded cargo, other train lengths and rotated layouts need future paired testing.',
            'Completed-cohort transit excludes outstanding trains; inventory and OD gaps are reported separately.',
            'Three-way forks, geometry, buffering and signals change together; no single-factor causal gain is claimed.',
            'Native selected-path block DAG and finite closure recovery do not prove all-demand deadlock freedom.',
            'CPU uses a separate common lower offered load and three identical-save repetitions, not saturated-bank CPU.',
            'Distinct rail geometries/configurations are not a count of nonisomorphic abstract topology families.',
        ],
    }
    write('round4/final/results-summary.json',result)
    print(json.dumps({'selection_cases':len(selection),'holdout_cases':len(holdout),'cpu_cases':len(cpu),
        'selection_pair':result['selection_pair'],'holdout_pair':result['holdout_pair'],
        'publication_gate_complete':a.require_complete},ensure_ascii=False))

if __name__=='__main__':main()

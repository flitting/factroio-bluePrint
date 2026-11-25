#!/usr/bin/env python3
"""Finish clean baseline gate and three restricted-demand discharge references."""
import json,pathlib,sys,statistics
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'round4/protocol'))
from run_bank import config,run_case
from analyze_graph import cases_for,analyze
from run_protocol import summarize
sys.path.insert(0,str(ROOT/'scripts'));from run import run
clean='r4-ext-three-chunk-square-clean'
raw=run('r4-external-clean-baseline-graph',ROOT/'round4/protocol/graph.lua',{'cases':cases_for([clean])},61,timeout=600)
assert raw['cases'][0]['all_signals_working'] and raw['cases'][0]['all_12_od']
(HERE/'clean-validation-summary.json').write_text(json.dumps({'evidence_directory':raw['evidence_directory'],'cases':[analyze(c) for c in raw['cases']]},indent=2))
r=run_case(config(clean,seed=17,scenario='S1',bank=80,warmup=1800,duration=3600));s=summarize(r);(HERE/'clean-screen.json').write_text(json.dumps([s],indent=2));print(json.dumps({k:s[k] for k in ['id','throughput','damage_events','all_od_completed_in_window','evidence_directory']}),flush=True)
original_summary=json.loads((HERE/'extra-screen.json').read_text());os=next(s for s in original_summary if s['id']=='r4-ext-three-chunk-square');o=json.loads((ROOT/os['evidence_directory']/'script-output/result.json').read_text())
(HERE/'clean-equivalence.json').write_text(json.dumps({'scope':'same bank80 S1 seed17, native traffic records/samples after deleting the one unconnected signal','original':os['evidence_directory'],'clean':s['evidence_directory'],'records_exact_equal':r['records']==o['records'],'samples_exact_equal':r['samples']==o['samples'],'damage_events_original':o['damage_events'],'damage_events_clean':r['damage_events'],'complete_original':o['completed'],'complete_clean':r['completed']},indent=2))
rows=[]
for scenario,near,straight in [('D0-straight',0,1),('D0-near',1,0),('D0-far',0,0)]:
 cfg=config('r3-sig-turbine2-dense2',seed=17,scenario=scenario,bank=150,warmup=3600,duration=3600);cfg['near']=near;cfg['straight']=straight
 raw=run_case(cfg);summary=summarize(raw);per=[]
 for origin in range(1,5):
  records=[r for r in raw['records'] if r['origin']==origin and 'complete_tick' in r and cfg['warmup']<=r['complete_tick']<cfg['warmup']+cfg['duration']]
  ticks=sorted(r['complete_tick'] for r in records);intervals=[b-a for a,b in zip(ticks,ticks[1:])];intervals.sort()
  per.append({'origin':'NESW'[origin-1],'destination':'NESW'[records[0]['destination']-1] if records else None,'completed_in_window':len(records),'trains_per_minute':len(records)/(cfg['duration']/3600),'ticks_without_external_bank':raw['no_upstream_ticks'][origin-1],'minimum_external_bank':raw['entry_supply_min'][origin-1],'mean_observed_completion_headway_seconds':statistics.mean(intervals)/60 if intervals else None,'median_observed_completion_headway_seconds':statistics.median(intervals)/60 if intervals else None,'minimum_observed_completion_headway_seconds':min(intervals)/60 if intervals else None,'maximum_observed_completion_headway_seconds':max(intervals)/60 if intervals else None})
 active_ods={od:v for od,v in raw['od'].items() if v['generated']>0}
 row={'id':cfg['id'],'scenario':scenario,'seed':17,'bank':150,'warmup':3600,'duration':3600,'near':near,'straight':straight,'far':1-near-straight,'throughput':raw['throughput'],'damage_events':raw['damage_events'],'all_four_expected_ods_completed':len(active_ods)==4 and all(v['measured_completed']>0 for v in active_ods.values()),'unexpected_generated_ods':len(active_ods)!=4,'ticks_without_external_bank_by_origin':raw['no_upstream_ticks'],'per_origin':per,'evidence_directory':raw['evidence_directory'],'interpretation':'Restricted four-OD discharge in the existing Dense364 junction and common native fixture. No destination has competing origins in a given case. This is not a rigorous global upper bound, nor a maximum stable arrival-rate capacity.'}
 assert row['damage_events']==0 and row['all_four_expected_ods_completed'] and all(t==0 for t in row['ticks_without_external_bank_by_origin'])
 rows.append(row);(HERE/'capacity-reference.json').write_text(json.dumps({'scope':'existing reference geometry + native follow-the-leader and common fixture reference, not optimum bound','cases':rows},indent=2));print(json.dumps({'scenario':scenario,'throughput':row['throughput'],'per_origin':[r['trains_per_minute'] for r in per],'evidence':row['evidence_directory']}),flush=True)

#!/usr/bin/env python3
"""Two joint inlet/outlet signal-spacing sensitivity cases, never main ranking."""
import json,pathlib,sys,statistics
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'round4/protocol'));import run_bank as bank_runner
bank_runner.HERE=HERE/'spacing-protocol'
from run_bank import config,run_case
p=HERE/'capacity-reference.json';doc=json.loads(p.read_text());rows=doc['cases']
for spacing in [4,2]:
 scenario=f'D0-straight-spacing{spacing}'
 if any(c['scenario']==scenario for c in rows):continue
 cfg=config('r3-sig-turbine2-dense2',seed=17,scenario=scenario,bank=150,warmup=3600,duration=3600);cfg.update(near=0,straight=1,spacing=spacing,station_signal_clearance=4)
 raw=run_case(cfg);per=[]
 for origin in range(1,5):
  recs=[r for r in raw['records'] if r['origin']==origin and 'complete_tick' in r and 3600<=r['complete_tick']<7200];ticks=sorted(r['complete_tick'] for r in recs);gaps=sorted(b-a for a,b in zip(ticks,ticks[1:]))
  per.append({'origin':'NESW'[origin-1],'destination':'NESW'[recs[0]['destination']-1] if recs else None,'completed_in_window':len(recs),'trains_per_minute':len(recs),'ticks_without_external_bank':raw['no_upstream_ticks'][origin-1],'minimum_external_bank':raw['entry_supply_min'][origin-1],'mean_observed_completion_headway_seconds':statistics.mean(gaps)/60 if gaps else None,'median_observed_completion_headway_seconds':statistics.median(gaps)/60 if gaps else None,'minimum_observed_completion_headway_seconds':min(gaps)/60 if gaps else None,'maximum_observed_completion_headway_seconds':max(gaps)/60 if gaps else None})
 active={k:v for k,v in raw['od'].items() if v['generated']>0}
 row={'id':cfg['id'],'scenario':scenario,'seed':17,'bank':150,'warmup':3600,'duration':3600,'near':0,'straight':1,'far':0,'spacing':spacing,'exit_clearance':cfg['exit_clearance'],'station_signal_clearance':4,'station_pocket_note':'Skip outlet rail signals within 4 tiles of the station at offset2300 to permit normal station construction. This is past the406tile retirement boundary. At spacing8 no previously generated signal is skipped.','first_exit_signals':raw['first_exit_signals'],'throughput':raw['throughput'],'damage_events':raw['damage_events'],'all_four_expected_ods_completed':len(active)==4 and all(r['measured_completed']>0 for r in active.values()),'unexpected_generated_ods':len(active)!=4,'ticks_without_external_bank_by_origin':raw['no_upstream_ticks'],'per_origin':per,'evidence_directory':raw['evidence_directory'],'interpretation':'Joint inlet/outlet fixture signal-spacing sensitivity, same Dense364 core, bank150, 3600 warmup + 3600 measured ticks. First exit signal clearance stays 8. Never a main-ranking replacement or rigorous upper bound; inlet and outlet effects are not separately identified.'}
 assert row['damage_events']==0 and row['all_four_expected_ods_completed'] and all(t==0 for t in row['ticks_without_external_bank_by_origin'])
 rows.append(row);doc['cases']=rows;p.write_text(json.dumps(doc,indent=2));print(json.dumps({'scenario':scenario,'throughput':row['throughput'],'per_origin':[r['trains_per_minute'] for r in per],'evidence':row['evidence_directory']}),flush=True)
for c in rows:
 c.setdefault('spacing',8);c.setdefault('exit_clearance',8)
doc['comparison_note']='Five restricted-demand diagnostic configurations. No mixed-flow candidate score is replaced. Spacing changes both inlet and outlet lines jointly, so it cannot by itself isolate which boundary caused a limit.'
p.write_text(json.dumps(doc,indent=2))

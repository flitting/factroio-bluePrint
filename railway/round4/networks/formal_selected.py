import json,sys,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'round4/protocol'))
from run_bank import run_case,config,summarize,engine_identity
screens=[]
for fn in ['direct-screen-first.json','direct-screen-compact.json','direct-screen-short-tails.json']:
 p=H/fn
 if p.exists():screens+=json.loads(p.read_text())
graph={}
for p in H.glob('*graph*.json'):
 d=json.loads(p.read_text())
 if isinstance(d,dict):
  for c in d.get('cases',[]):graph[c['id']]=c
eligible=[r for r in screens if r['all_od_completed_in_window'] and r['damage_events']==0 and all(x==0 for x in r['ticks_without_external_bank_by_origin']) and graph.get(r['id'],{}).get('all_12_od') and graph[r['id']].get('all_signals_working')]
selected=max(eligible,key=lambda r:(r['throughput'],-graph[r['id']]['area'],-graph[r['id']]['signals']))
plan={'selection':'Highest completed short S1/seed17/bank80 measurement, then smaller full candidate AABB, then fewer signals. Selection is on the same seed; this is a longer-window validation, not an independent holdout.','selected':selected['id'],'screen_value':selected['throughput'],'config':{'seed':17,'bank':150,'warmup':3600,'duration':10800,'scenario':'S1'},'eligible_screen_results':[{'id':r['id'],'throughput':r['throughput'],'area':graph[r['id']]['area']} for r in eligible]}
(H/'formal-selection-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({'selected':plan['selected'],'screen_value':plan['screen_value'],'config':plan['config']}),flush=True)
raw=run_case(config(selected['id'],seed=17,bank=150,warmup=3600,duration=10800),engine_identity(),timeout=1200)
row=summarize(raw);(H/'formal-selected.json').write_text(json.dumps([row],indent=2));print(json.dumps({k:row[k] for k in ['id','throughput','all_od_completed_in_window','damage_events','evidence_directory']}),flush=True)

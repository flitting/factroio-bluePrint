"""Freeze the ternary candidate before the three selection-seed long runs."""
import hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'round4/protocol'))
from run_bank import run_case,config,engine_identity,summarize
ident='r4-dir-trident32-32'
files={'blueprint':ROOT/'blueprints'/f'{ident}.txt','blueprint_json':ROOT/'blueprints'/f'{ident}.json','generator':HERE/'generate_trident.py','builder':HERE/'build.lua','traffic_observer':ROOT/'round4/protocol/bank.lua','traffic_runner':ROOT/'round4/protocol/run_bank.py'}
fingerprint={k:{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in files.items()}
plan={'created_utc':datetime.now(timezone.utc).isoformat(),'id':ident,'stage':'Three pre-existing selection seeds, not independent confirmatory holdout','seeds':[17,31,47],'bank':150,'warmup':3600,'duration':10800,'scenario':'S1','blueprint_frozen_before_long_runs':True,'files':fingerprint,'engine':engine_identity(),'prior_seen_result':'Only seed17 bank80 short:116/min, 12OD, damage0. Native graph gates passed.','acceptance':'12 OD completed in window, damage0, each no_upstream_ticks=0; if any bank exhausts, do not call the resulting rate a comparable saturated discharge; notify root for common bank240 reruns.','next_confirmatory_seeds_reserved_by_root':[211,307,401]}
pp=HERE/'trident-long-plan.json'
if pp.exists():
 old=json.loads(pp.read_text());assert old['files']==fingerprint;plan=old
else:pp.write_text(json.dumps(plan,indent=2))
rows=[]
for seed in plan['seeds']:
 for k,p in files.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==plan['files'][k]['sha256'],k
 raw=run_case(config(ident,seed,'S1',150,3600,10800),plan['engine'],timeout=900)
 row=summarize(raw);rows.append(row);(HERE/'long-trident.json').write_text(json.dumps(rows,indent=2))
 print(json.dumps({k:row[k] for k in ['id','seed','throughput','all_od_completed_in_window','damage_events','ticks_without_external_bank_by_origin','evidence_directory']}),flush=True)

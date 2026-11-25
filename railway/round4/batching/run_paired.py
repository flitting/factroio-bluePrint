#!/usr/bin/env python3
"""Actual circuit policies, paired finite-FIFO protocol. No scripted actuators."""
import argparse,json,pathlib,sys,hashlib,statistics
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'round4/protocol'));import run_bank
from run_bank import config,run_case,summarize
p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',default=['r4-batch-h64-phase15','r4-batch-h64-phase30','r4-dir-crossbar64-source']);p.add_argument('--resume-interrupted',action='store_true');args=p.parse_args()
local_protocol=HERE/'protocol';local_protocol.mkdir(exist_ok=True)
base_source=(ROOT/'round4/protocol/bank.lua').read_text();observer=(HERE/'observer.lua').read_text();(local_protocol/'bank.lua').write_text(base_source+'\n'+observer)
run_bank.HERE=local_protocol
(HERE/'protocol-manifest.json').write_text(json.dumps({'base_protocol':'round4/protocol/bank.lua','base_sha256':hashlib.sha256(base_source.encode()).hexdigest(),'observer_sha256':hashlib.sha256(observer.encode()).hexdigest(),'only_source_change':'Append read-only on_nth_tick observer; no existing traffic source changes.','bank':240,'warmup':5400,'duration':10800,'seed':17,'scenario':'S1','phase_policy_seconds':[15,30]},indent=2))
out=HERE/'paired-results.json';rows=json.loads(out.read_text()) if out.exists() else []
for ident in args.ids:
 if any(r['id']==ident for r in rows):continue
 cfg=config(ident,seed=17,scenario='S1',bank=240,warmup=5400,duration=10800);cfg['batch_expected_controllers']=4 if ident.startswith('r4-batch-') else 0
 raw=run_case(cfg,timeout=1800,resume_interrupted=args.resume_interrupted);row=summarize(raw)
 observation=json.loads((ROOT/raw['evidence_directory']/'script-output/circuit-observations.json').read_text())
 periods=[]
 for controller in observation['controllers']:
  tr=controller['transitions'];periods.append(sorted(set(b['tick']-a['tick'] for a,b in zip(tr[1:],tr[2:]))))
 row['actual_phase_ticks_per_controller']=periods
 row['minimum_combinator_energy']=min([r['minimum_energy'] for r in observation['all_combinators']],default=None)
 row['minimum_combinator_energy_after_warmup']=min([r['minimum_energy_after_warmup'] for r in observation['all_combinators']],default=None)
 row['minimum_accumulator_energy_after_warmup']=min([r['minimum_energy_after_warmup'] for r in observation['batteries']],default=None)
 row['circuit_observation_file']=str((ROOT/raw['evidence_directory']/'script-output/circuit-observations.json').relative_to(ROOT))
 row['per_origin_measured_completions']=[sum(1 for r in raw['records'] if r['origin']==o and 5400<=r.get('complete_tick',-1)<16200) for o in range(1,5)]
 row['comparison_group']='H64 actual native circuit batching; paired bank240 warm90s measure180s seed17. Do not rank directly against bank150 or 60s screens.'
 rows.append(row);out.write_text(json.dumps(rows,indent=2));print(json.dumps({k:row.get(k) for k in ['id','throughput','all_od_completed_in_window','damage_events','ticks_without_external_bank_by_origin','per_origin_measured_completions','actual_phase_ticks_per_controller','minimum_combinator_energy','minimum_accumulator_energy_after_warmup','evidence_directory']}),flush=True)

#!/usr/bin/env python3
import json,pathlib,collections
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
rows=json.loads((HERE/'paired-results.json').read_text()) if (HERE/'paired-results.json').exists() else []
out=[]
for row in rows:
 obs=json.loads((ROOT/row['circuit_observation_file']).read_text());window=[r for r in obs['samples'] if 5400<=r['tick']<16200]
 states=collections.Counter((g['close_condition_fulfilled'],g['signal_state']) for r in window for g in r['gates'])
 d={'id':row['id'],'controllers':len(obs['controllers']),'observed_shared_networks':[{'network_id':c['network_id'],'gate_count':len(c['gates']),'phases':sorted(g['phase'] for g in c['gates'])} for c in obs['controllers']],'actual_phase_ticks':row['actual_phase_ticks_per_controller'],'condition_mismatch_samples':sum(g['close_condition_fulfilled']!=(g['actual_p']!=g['phase']) for r in window for g in r['gates']),'wrong_phase_green_samples':sum(g['close_condition_fulfilled'] and g['signal_state']==0 for r in window for g in r['gates']),'signal_status_not_working_samples':sum(g['status']!=1 for r in window for g in r['gates']),'combinator_minimum_energy_after_warmup':row['minimum_combinator_energy_after_warmup'],'accumulator_minimum_energy_after_warmup':row['minimum_accumulator_energy_after_warmup'],'states':[{'closed_by_condition':c,'native_signal_state':s,'one_second_observations':n} for (c,s),n in sorted(states.items())],'interpretation':'Signal states 0=open,1=red,2=reserved/orange,3=reserved by circuit. Reservations can remain honored when a circuit condition becomes true; this is native safe behavior. One-second sample counts are observations, not counts of trains or exact duration at a state. Power minima refer to the one-second sampling grid. Tick0 power transients are excluded from measurement power checks.'}
 out.append(d)
(HERE/'operational-validation.json').write_text(json.dumps(out,indent=2))
print(json.dumps([{'id':r['id'],'controllers':r['controllers'],'phase_ticks':r['actual_phase_ticks'],'condition_mismatch':r['condition_mismatch_samples'],'wrong_phase_green':r['wrong_phase_green_samples'],'energy_after_warm':r['combinator_minimum_energy_after_warmup']} for r in out]))

"""Native four-exit60s closure then drain; only circuit boundary conditions change."""
import argparse,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'round4/protocol'));import run_bank as bank
bank.HERE=HERE

def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',required=True);p.add_argument('--seeds',nargs='+',type=int,default=[17]);p.add_argument('--output',required=True);p.add_argument('--timeout',type=int,default=900);a=p.parse_args()
    output=pathlib.Path(a.output);output=output if output.is_absolute() else ROOT/output;rows=[];identity=bank.engine_identity()
    for ident in a.ids:
        for seed in a.seeds:
            c=bank.config(ident,seed,bank=80,warmup=1800,duration=19800);c.update(block_enabled=True,block_exit='ALL',block_start=3600,block_end=7200)
            raw=bank.run_case(c,identity,a.timeout);r=bank.summarize(raw)
            expected=sorted((tick,side,closed) for tick,closed in [(c['block_start'],True),(c['block_end'],False)] for side in 'NESW')
            actual=sorted((e['tick'],e['exit'],e['closed']) for e in raw['block_history'])
            assert raw['block_controller_count']==4 and actual==expected, 'all-four closure command evidence mismatch'
            assert {e['exit'] for e in raw['controlled_exits']}==set('NESW')
            assert all(e['offset']==c['exit_clearance'] for e in raw['controlled_exits'])
            midpoint=(c['block_start']+c['block_end'])//2
            mid=next(s for s in raw['block_signal_samples'] if s['tick']==midpoint)
            r.update(closure_commands_verified=True,controlled_exits=raw['controlled_exits'],block_signal_samples=raw['block_signal_samples'],all_four_midpoint_native_red=all(s.get('signal_state_name') in ('closed','reserved_by_circuit_network') for s in mid['states']),all_four_midpoint_circuit_reserved=all(s.get('signal_state_name')=='reserved_by_circuit_network' for s in mid['states']))
            r.update(total_requested=len(raw['records']),total_completed=raw['total_completed'],remaining=raw['remaining'],active_world=raw['active_world'],retired=raw['retired'],complete_drain_observed=raw['remaining']==0 and raw['active_world']==0,block_history=raw['block_history'],last_complete_tick=max(v.get('complete_tick',0) for v in raw['records']),interpretation='Finite all-exit closure and recovery gate; does not prove no deadlock for every future demand.')
            rows.append(r);output.write_text(json.dumps(rows,indent=2))
            print(json.dumps({k:r[k] for k in ['id','seed','total_requested','total_completed','remaining','active_world','damage_events','complete_drain_observed','evidence_directory']}),flush=True)
if __name__=='__main__':main()

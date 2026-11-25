#!/usr/bin/env python3
"""Frozen fresh-seed confirmation; each worker receives disjoint candidate IDs."""
import argparse,hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(HERE/'protocol'));import run_bank as bank

def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',required=True);p.add_argument('--output',required=True)
    p.add_argument('--seeds',nargs='+',type=int,help='Schedule only this subset of the already frozen seeds; never changes the plan.')
    p.add_argument('--resume-interrupted',action='store_true',help='Archive a lost execution attempt and restart its unchanged native case.')
    a=p.parse_args()
    plan=json.loads((HERE/'holdout-plan.json').read_text());assert set(a.ids)<=set(plan['ids'])
    seeds=plan['seeds'] if a.seeds is None else a.seeds;assert set(seeds)<=set(plan['seeds'])
    identity=bank.engine_identity();out=pathlib.Path(a.output);out=out if out.is_absolute() else ROOT/out;rows=[]
    for ident in a.ids:
        for seed in seeds:
            assert hashlib.sha256((ROOT/'blueprints'/f'{ident}.txt').read_bytes()).hexdigest()==plan['blueprint_sha256'][ident]
            assert hashlib.sha256((HERE/'protocol/bank.lua').read_bytes()).hexdigest()==plan['protocol_lua_sha256']
            cfg=bank.config(ident,seed,plan['scenario'],plan['bank'],plan['warmup'],plan['duration'],plan['loaded'])
            assert cfg['spacing']==plan['spacing']
            raw=bank.run_case(cfg,identity,plan['timeout'],resume_interrupted=a.resume_interrupted);r=bank.summarize(raw)
            r['bank']=plan['bank'];r['confirmation_group']='fresh-seed-longer-horizon'
            rows.append(r);out.write_text(json.dumps(rows,indent=2))
            print(json.dumps({k:r[k] for k in ['id','seed','throughput','all_od_completed_in_window','damage_events','ticks_without_external_bank_by_origin','evidence_directory']}),flush=True)
if __name__=='__main__':main()

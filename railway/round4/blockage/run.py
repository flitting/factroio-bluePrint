"""Paired same-FIFO preloaded bank, with/without a 60-second exit closure."""
import argparse,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'protocol'))
import run_bank as bank
bank.HERE=HERE

def config(ident,seed,closed):
    c=bank.config(ident,seed,bank=80,warmup=1800,duration=19800)
    c.update(protocol_name='round4-expanded-native-exit-blockage-v1',block_exit='W',block_enabled=closed,block_start=3600,block_end=7200)
    return c

def summarize(raw):
    row=bank.summarize(raw);cfg=raw['config'];records=raw['records']
    phases={}
    for name,start,end in [('before',1800,3600),('closure',3600,7200),('first_recovery_minute',7200,10800)]:
        done=[r for r in records if start<=r.get('complete_tick',10**9)<end]
        entered=[r for r in records if start<=r.get('entry_tick',10**9)<end]
        hs=[h for sample in raw['queue_head_samples'] if start<=sample['tick']<end for h in sample['heads']]
        phases[name]={'from_tick':start,'to_tick_exclusive':end,'seconds':(end-start)/60,
                      'completed':len(done),'completed_open_destinations':sum(r['destination']!=4 for r in done),
                      'by_destination':{d:sum(r['destination']==i for r in done) for i,d in enumerate('NESW',1)},
                      'entered_open_destinations':sum(r['destination']!=4 for r in entered),
                      'external_head_exposure_origin_seconds':sum(h['blocked_destination_head_with_open_destination_next'] for h in hs)}
    row.update(block_enabled=cfg['block_enabled'],phases=phases,block_history=raw['block_history'],
               total_requested=len(records),total_completed=sum('complete_tick' in r for r in records),
               last_complete_tick=max([0]+[r.get('complete_tick',0) for r in records]),
               active_world=raw['active_world'],remaining=raw['remaining'],
               complete_drain_observed=raw['remaining']==0 and raw['active_world']==0,
               queue_proxy_definition='One-second samples of stopped native-signal queue heads on external incoming rail within 120 tiles of portal; head targets W and physically next train targets an open exit. Descriptive exposure, not a counterfactual HOL loss estimate.')
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',required=True);p.add_argument('--seeds',nargs='+',type=int,default=[17]);p.add_argument('--output',required=True);p.add_argument('--timeout',type=int,default=900)
    a=p.parse_args();out=pathlib.Path(a.output);out=out if out.is_absolute() else ROOT/out
    out.parent.mkdir(parents=True,exist_ok=True);rows=[];identity=bank.engine_identity()
    for ident in a.ids:
        for seed in a.seeds:
            for closed in [False,True]:
                r=summarize(bank.run_case(config(ident,seed,closed),identity,a.timeout));rows.append(r)
                out.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
                print(json.dumps({k:r[k] for k in ['id','seed','block_enabled','phases','complete_drain_observed','damage_events','evidence_directory']}),flush=True)

if __name__=='__main__':main()

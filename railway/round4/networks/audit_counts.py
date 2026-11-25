#!/usr/bin/env python3
"""Read-only independent index audit; writes only inside round4/networks.

This is an observation inventory, not a ranking or a native engine runner.
The reference index is imported without executing its main function.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import base64, hashlib, importlib.util, json, sys, zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('root_r4_index', ROOT/'round4/index_results.py')
index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(index)
DIRS = [
    'round4/protocol/experiments',
    'round4/blockage/experiments',
    'round4/blockage-all/experiments',
    'round4/batching/protocol/experiments',
    'round4/external/spacing-protocol/experiments',
]
EXOGENOUS = [
    'bank','scenario','warmup','duration','loaded','spacing','gap',
    'near','straight','entry_plane','exit_plane','sink_plane',
    'exit_clearance','length','outlet_length','stop_offset',
    'station_signal_clearance','protocol_name','block_enabled',
    'block_exit','block_start','block_end',
]

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def decode(text):
    return json.loads(zlib.decompress(base64.b64decode(text.strip()[1:])))

def rail_only_hash(text, straight_halfturn=False):
    es = decode(text)['blueprint']['entities']
    rails = []
    for e in es:
        if 'rail' not in e['name'] or e['name'] in ['rail-support','rail-signal','rail-chain-signal']:
            continue
        d = e.get('direction',0)
        if straight_halfturn and e['name'] in ['straight-rail','elevated-straight-rail','half-diagonal-rail','elevated-half-diagonal-rail']:
            d %= 8
        rails.append([e['name'],e['position']['x'],e['position']['y'],d])
    assert rails
    mx = min(r[1] for r in rails); my = min(r[2] for r in rails)
    def num(v): return int(v) if isinstance(v,float) and v.is_integer() else v
    return digest(sorted((name,num(x-mx),num(y-my),d) for name,x,y,d in rails))

def hashes(text):
    return {
        'exact':index.entities_hash(text),
        'rails_and_supports':index.entities_hash(text,False,True),
        'rails_only':rail_only_hash(text),
        'rails_only_halfturn':rail_only_hash(text,True),
    }

def audit_records(req, raw):
    c=req['config']; rr=raw['records']; a=c['warmup']; b=a+c['duration']
    entered = sum(a<=r.get('entry_tick',-1)<b for r in rr)
    completed = sum(a<=r.get('complete_tick',-1)<b for r in rr)
    inside = lambda t:sum(r.get('entry_tick',b+1)<t and r.get('complete_tick',b+1)>=t for r in rr)
    req_cfg={k:v for k,v in c.items() if k!='blueprint'}
    fifo=[]
    for origin in range(1,5):
        whole=sorted((r for r in rr if r['origin']==origin),key=lambda r:r['id'])
        seen=sorted((r for r in whole if 'entry_tick' in r),key=lambda r:(r['entry_tick'],r['id']))
        fifo.append([r['id'] for r in seen]==[r['id'] for r in whole[:len(seen)]])
    return {
        'request_raw_config_equal':raw['config']==req_cfg,
        'fifo_is_full_request_prefix':all(fifo),
        'measurement_count_equal':completed==raw['completed'],
        'inventory_balance':entered-completed==inside(b)-inside(a),
        'total_record_count':len(rr)==4*c['bank'],
        'retired_active_conservation':raw['retired']+raw['active_world']==len(rr),
        'total_complete_remaining_conservation':raw['total_completed']+raw['remaining']==len(rr),
        'demand_sha256':digest([(r['id'],r['origin'],r['destination'],r['arrival_tick']) for r in rr]),
    }

def main():
    before = defaultdict(list); skipped=[]
    for p in sorted((ROOT/'blueprints').glob('*.txt')):
        if p.name.startswith('r4-'):continue
        try:
            hs=hashes(p.read_text())
        except (KeyError,ValueError,IndexError,zlib.error) as exc:
            skipped.append({'path':str(p.relative_to(ROOT)),'reason':type(exc).__name__});continue
        for k,h in hs.items():before[k,h].append(p.stem)
    rows=[]; incomplete=[]; per_directory={}
    for dirname in DIRS:
        done=[];bad=[]
        for p in sorted((ROOT/dirname).glob('*/request.json')):
            req=json.loads(p.read_text());rp=p.parent/'script-output/result.json'
            if req.get('exit_code')!=0 or not rp.exists():
                item={'directory':str(p.parent.relative_to(ROOT)),'status':req.get('status'),'exit_code':req.get('exit_code')}
                incomplete.append(item);bad.append(item);continue
            raw=json.loads(rp.read_text());c=req['config'];text=c['blueprint'].strip();hs=hashes(text)
            group={k:c.get(k) for k in EXOGENOUS}
            group['block_protocol']='block_enabled' in c
            group['source_sha256']=req['source_sha256']
            group['engine_identity_sha256']=digest(req['engine'])
            item={
                'id':c['id'],'seed':c['seed'],'source_directory':dirname,
                'evidence_directory':str(p.parent.relative_to(ROOT)),
                'case_sha256':req['case_sha256'],'hashes':hs,
                'prior_artifact_matches':{k:before.get((k,h),[]) for k,h in hs.items()},
                'source_sha256':req['source_sha256'],
                'completed':raw['completed'],'throughput':raw['throughput'],
                'damage_events':raw['damage_events'],
                'comparable_group':group,'comparable_group_sha256':digest(group),
                'batch_expected_controllers':c.get('batch_expected_controllers'),
                'matches_current_input':(ROOT/'blueprints'/f"{c['id']}.txt").exists() and (ROOT/'blueprints'/f"{c['id']}.txt").read_text().strip()==text,
                'record_audit':audit_records(req,raw),
            }
            rows.append(item);done.append(item)
        per_directory[dirname]={'completed':len(done),'incomplete':len(bad),'unique_case_sha256':len({x['case_sha256'] for x in done}),'unique_ids':len({x['id'] for x in done})}
    def stats(rs):
        new=[r for r in rs if r['id'].startswith('r4-')]
        out={'completed_records':len(rs),'unique_case_sha256':len({r['case_sha256'] for r in rs}),
             'all_unique_ids':len({r['id'] for r in rs}),'r4_unique_ids':len({r['id'] for r in new})}
        for k in ['exact','rails_and_supports','rails_only','rails_only_halfturn']:
            out['r4_unique_'+k]=len({r['hashes'][k] for r in new})
            out['r4_unique_'+k+'_excluding_pre_r4_artifacts']=len({r['hashes'][k] for r in new if not r['prior_artifact_matches'][k]})
        return out
    by_case=defaultdict(list);by_config=defaultdict(set);by_geom=defaultdict(set);groups=defaultdict(list)
    for r in rows:
        by_case[r['case_sha256']].append(r['evidence_directory'])
        by_config[r['hashes']['exact']].add(r['id'])
        by_geom[r['hashes']['rails_only_halfturn']].add(r['id'])
        groups[r['comparable_group_sha256']].append(r)
    compact_groups=[]
    for h,rs in groups.items():
        compact_groups.append({'group_sha256':h,'config':rs[0]['comparable_group'],'count':len(rs),'ids':sorted({r['id'] for r in rs}),'seeds':sorted({r['seed'] for r in rs})})
    output={
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'audited_root_script_sha256':hashlib.sha256((ROOT/'round4/index_results.py').read_bytes()).hexdigest(),
        'definitions':{
            'completed':'request.exit_code==0 plus final result, not sufficient evidence of all-OD service or optimum',
            'new_prefix':'r4-* input IDs; historical aliases are deduplicated by exact tested input',
            'prior_artifacts':'Every decodable non-r4 leaf blueprint currently in blueprints/*.txt, including untested drafts; excluding these is a conservative novelty test',
            'rails_only':'rail and ramp names/positions/directions modulo common translation, excluding signals, supports and circuit/power entities',
            'rails_only_halfturn':'as rails_only, additionally canonicalizes straight and half-diagonal rail direction modulo8; curve/ramp full orientation retained',
            'not_counted':'native builder/static-graph validation, CPU profiling and nested interrupted attempt archives are outside this traffic inventory',
        },
        'per_directory':per_directory,
        'original_three_directories':stats([r for r in rows if r['source_directory'] in DIRS[:3]]),
        'all_five_directories':stats(rows),
        'duplicate_case_hashes':{k:v for k,v in by_case.items() if len(v)>1},
        'exact_duplicate_ids':{k:sorted(v) for k,v in by_config.items() if len(v)>1},
        'geometry_duplicate_ids':{k:sorted(v) for k,v in by_geom.items() if len(v)>1},
        'prior_match_r4_ids':sorted({r['id'] for r in rows if r['id'].startswith('r4-') and r['prior_artifact_matches']['exact']}),
        'stale_current_inputs':[{'id':r['id'],'evidence_directory':r['evidence_directory']} for r in rows if not r['matches_current_input']],
        'record_audit_failures':[{'id':r['id'],'evidence_directory':r['evidence_directory'],'audit':r['record_audit']} for r in rows if any(v is False for v in r['record_audit'].values())],
        'groups':compact_groups,'incomplete':incomplete,'cases':rows,
        'skipped_prior_nonleaf_or_invalid_inputs':skipped,
    }
    (HERE/'audit-result-index-data.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ['generated_utc','per_directory','original_three_directories','all_five_directories','duplicate_case_hashes','exact_duplicate_ids','prior_match_r4_ids','record_audit_failures']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

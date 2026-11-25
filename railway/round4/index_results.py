#!/usr/bin/env python3
"""Index completed fourth-round native cases; retain exact tested input identity."""
from pathlib import Path
from datetime import datetime,timezone
import base64,hashlib,json,sys,zlib
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'round4'
sys.path.insert(0,str(ROOT/'round2/protocol'));from run_protocol import summarize

def entities_hash(bp,signals=True,rail_geometry=False):
    doc=json.loads(zlib.decompress(base64.b64decode(bp.strip()[1:])))['blueprint']
    es=[]; numbers=[]
    for e in doc['entities']:
        if not signals and e['name'] in ['rail-signal','rail-chain-signal']:continue
        if rail_geometry and ('rail' not in e['name'] or e['name'] in ['rail-signal','rail-chain-signal']):continue
        numbers.append(e['entity_number']);e={k:v for k,v in e.items() if k!='entity_number'}
        es.append(e)
    # Coordinate translation and labels are not distinct geometry/configuration.
    mx=min(e['position']['x'] for e in es);my=min(e['position']['y'] for e in es)
    def num(v):return int(v) if isinstance(v,float) and v.is_integer() else v
    for e in es:
        e['position']={a:num(e['position'][a]-(mx if a=='x' else my)) for a in ['x','y']}
        e['direction']=e.get('direction',0)
        if e['name'] in ['rail-signal','rail-chain-signal']:e['rail_layer']=1 if e.get('rail_layer',0) in [1,'elevated'] else 0
    encoded=[json.dumps(e,sort_keys=True,separators=(',',':')) for e in es]
    canonical=sorted(encoded)
    lookup={n:hashlib.sha256(v.encode()).hexdigest() for n,v in zip(numbers,encoded)}
    wires=[]
    if signals:
        for wire in doc.get('wires',[]):
            a,ca,b,cb=wire
            if a in lookup and b in lookup:wires.append(sorted([(lookup[a],ca),(lookup[b],cb)]))
    payload={'entities':canonical,'wires':sorted(wires)}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    completed=[];incomplete=[]
    for directory in [HERE/'protocol/experiments',HERE/'blockage/experiments',HERE/'blockage-all/experiments',HERE/'batching/protocol/experiments',HERE/'external/spacing-protocol/experiments']:
        for reqpath in sorted(directory.glob('*/request.json')):
            req=json.loads(reqpath.read_text());rp=reqpath.parent/'script-output/result.json'
            if req.get('exit_code')!=0 or not rp.exists():
                incomplete.append({'directory':str(reqpath.parent.relative_to(ROOT)),'status':req.get('status'),'exit_code':req.get('exit_code')});continue
            raw=json.loads(rp.read_text());raw['evidence_directory']=str(reqpath.parent.relative_to(ROOT));cfg=req['config'];row=summarize(raw)
            tested=cfg['blueprint'].strip();local=ROOT/'blueprints'/f"{cfg['id']}.txt"
            row.update(spacing=cfg['spacing'],gap=cfg['gap'],near=cfg['near'],straight=cfg['straight'],bank=cfg['bank'],loaded=cfg.get('loaded',False),case_sha256=req['case_sha256'],blueprint_sha256=hashlib.sha256((tested+'\n').encode()).hexdigest(),exact_configuration_sha256=entities_hash(tested),non_signal_geometry_sha256=entities_hash(tested,False),rail_and_support_geometry_sha256=entities_hash(tested,False,True),matches_current_input=local.exists() and local.read_text().strip()==tested,total_completed=raw['total_completed'],retired=raw['retired'],mean_transit_seconds=raw['mean_transit_seconds'],p95_transit_seconds=raw['p95_transit_seconds'])
            row['blocked']=cfg.get('block_enabled',False);row['block_protocol']='block_enabled' in cfg
            row['source_saturated_in_window']=all(n==0 for n in raw['no_upstream_ticks'])
            row['comparable_group']={'bank':cfg['bank'],'scenario':cfg['scenario'],'warmup':cfg['warmup'],'duration':cfg['duration'],'loaded':cfg.get('loaded',False),'blocked':cfg.get('block_enabled',False),'source':'preloaded stationary FIFO bank','spacing':cfg['spacing'],'gap':cfg['gap'],'near':cfg['near'],'straight':cfg['straight'],'entry_plane':cfg['entry_plane'],'exit_plane':cfg['exit_plane'],'sink_plane':cfg['sink_plane'],'exit_clearance':cfg['exit_clearance'],'protocol_source_sha256':req['source_sha256']}
            row['comparable_group'].update(block_protocol='block_enabled' in cfg,block_exit=cfg.get('block_exit'),block_start=cfg.get('block_start'),block_end=cfg.get('block_end'),station_signal_clearance=cfg.get('station_signal_clearance'),outlet_length=cfg.get('outlet_length'),stop_offset=cfg.get('stop_offset'),length=cfg.get('length'))
            completed.append(row)
    result={'generated_utc':datetime.now(timezone.utc).isoformat(),'completed_cases':len(completed),'new_exact_configurations_tested':len({r['exact_configuration_sha256'] for r in completed if r['id'].startswith('r4-')}),'new_distinct_non_signal_geometries_tested':len({r['rail_and_support_geometry_sha256'] for r in completed if r['id'].startswith('r4-')}),'definitions':['Geometries are exact rail, ramp and support layouts modulo translation, excluding signals and circuit/power entities; not abstract graph isomorphism classes.','Configurations include signals; labels and entity numbering do not count as changes.','Only native exit_code0 with final result is a completed experiment.','Unchanged IDs with changed bytes are reported and cannot silently inherit previous test evidence.','No mixed-bank, mixed-window or mixed-scenario aggregate should be ranked.'],'cases':completed,'incomplete':incomplete}
    (HERE/'results-index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:result[k] for k in ['completed_cases','new_exact_configurations_tested','new_distinct_non_signal_geometries_tested']}))
if __name__=='__main__':main()

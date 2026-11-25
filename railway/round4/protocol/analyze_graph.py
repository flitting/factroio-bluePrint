"""Native graph diagnostics: connectivity, signal blocks, and OD sharing.

This is diagnostic, not a proof that 12 selected shortest routes are the only
possible paths or that finite queues cannot deadlock.
"""
import argparse,hashlib,itertools,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'));from run import run
sys.path.insert(0,str(HERE));from run_bank import config

def cases_for(ids):
    out=[]
    for ident in ids:
        cfg=config(ident)
        doc=json.loads((ROOT/'blueprints'/f'{ident}.json').read_text())
        out.append({'id':ident,'entities':len(doc['blueprint']['entities']),'blueprint':cfg['blueprint'],'core_chunk_radius':cfg['core_chunk_radius'],'surface_size':max(4096,cfg['core_chunk_radius']*64+640)})
    return out

def analyze(row):
    rails={r['id']:r for r in row['rails']}
    paths={f"{p['origin']}-{p['destination']}":p for p in row['paths']}
    pairs=[]
    for a,b in itertools.combinations(paths,2):
        pa,pb=paths[a],paths[b];ra,rb=set(pa['rails']),set(pb['rails'])
        ba={rails[r]['block'] for r in ra};bb={rails[r]['block'] for r in rb}
        same_o=pa['origin']==pb['origin'];same_d=pa['destination']==pb['destination']
        pairs.append({'a':a,'b':b,'shared_rails':len(ra&rb),'shared_blocks':len(ba&bb),'same_origin':same_o,'same_destination':same_d,'independent_ports':not same_o and not same_d})
    independent=[p for p in pairs if p['independent_ports']]
    # A presence signature is intentionally insensitive to segment lengths and signal density.
    structural=[]
    for rot in range(4):
        mapped={}
        for key,p in paths.items():
            o=(p['origin']-1+rot)%4+1;d=(p['destination']-1+rot)%4+1
            mapped[f'{o}-{d}']=set(p['rails'])
        structural.append(tuple(int(bool(mapped[a]&mapped[b])) for a,b in itertools.combinations(sorted(mapped),2)))
    signature=hashlib.sha256(bytes(min(structural))).hexdigest()
    return {'id':row['id'],'all_12_od':row['all_12_od'],'all_signals_working':row['all_signals_working'],'entities':row['entities'],'signals':len(row['signals']),'rails':len(rails),'rail_length':sum(r['length'] for r in rails.values()),'bounding_box_union_tiles':row['bounding_box_union_tiles'],'area':row['bounds']['area'],'bounds':row['bounds'],'native_core_rail_blocks':row['native_core_rail_blocks'],'native_core_rail_segments':row['native_core_rail_segments'],'static_path_steps_sum':sum(p['steps'] for p in paths.values()),'static_path_length_mean':sum(p['length'] for p in paths.values())/len(paths),'independent_od_pair_count':len(independent),'independent_od_pairs_share_rails':sum(p['shared_rails']>0 for p in independent),'independent_od_pairs_share_blocks':sum(p['shared_blocks']>0 for p in independent),'rotational_route_sharing_signature':signature,'od_pair_sharing':pairs,'interpretation':'Sharing for native shortest paths on an empty map. Different signatures prove these selected path-sharing relations differ; identical signatures do not prove graph isomorphism. Signals alter block sharing. These are structural diagnostics, not timing or deadlock proofs.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ids',nargs='+',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    out=pathlib.Path(a.output);out=out if out.is_absolute() else ROOT/out;out.parent.mkdir(parents=True,exist_ok=True)
    result=run('r4-native-graph',HERE/'graph.lua',{'cases':cases_for(a.ids)},61,timeout=600)
    rows=[analyze(r) for r in result['cases']]
    out.write_text(json.dumps({'evidence_directory':result['evidence_directory'],'cases':rows},indent=2))
    for r in rows:print(json.dumps({k:r[k] for k in ['id','all_12_od','all_signals_working','area','independent_od_pairs_share_rails','independent_od_pairs_share_blocks','rotational_route_sharing_signature']}),flush=True)
if __name__=='__main__':main()

"""Explore native signal packing on newly imported geometries; rails unchanged.

These are signal configurations within their existing geometry family. Adding
signals is only a proposal; build, live status and native drive gates follow.
"""
import argparse,base64,copy,hashlib,json,math,pathlib,zlib
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=pathlib.Path(__file__).resolve().parent

def save(ident,doc):
    for i,e in enumerate(doc['blueprint']['entities'],1):e['entity_number']=i
    doc['blueprint']['label']=ident
    for d in [ROOT/'blueprints',HERE]:
        (d/f'{ident}.json').write_text(json.dumps(doc,indent=2))
        (d/f'{ident}.txt').write_text('0'+base64.b64encode(zlib.compress(json.dumps(doc,separators=(',',':')).encode())).decode()+'\n')

def nonsig(doc):
    return sorted(json.dumps({k:v for k,v in e.items() if k!='entity_number'},sort_keys=True) for e in doc['blueprint']['entities'] if e['name'] not in ['rail-signal','rail-chain-signal'])

def generate(graph_summary,ids,spacings):
    summary=json.loads(graph_summary.read_text());raw=json.loads((ROOT/summary['evidence_directory']/'script-output/result.json').read_text());cases={c['id']:c for c in raw['cases']}
    out=[]
    for ident in ids:
        row=cases[ident];rails={r['id']:r for r in row['rails']};usage={}
        for path in row['paths']:
            for a,b in zip(path['rails'],path['rails'][1:]):
                ends=[e for e in rails[a]['ends'] if b in e['connections']]
                assert len(ends)==1,(ident,a,b)
                usage.setdefault(a,set()).add(ends[0]['rd'])
        candidates=[];seen=set();ambiguous=[]
        for rid,dirs in usage.items():
            if len(dirs)!=1:ambiguous.append(rid);continue
            end=next(e for e in rails[rid]['ends'] if e['rd']==next(iter(dirs)))
            if not end['can_place_signal']:continue
            loc=end['out_signal'];key=(loc['position']['x'],loc['position']['y'],loc['direction'],loc['rail_layer'])
            if key not in seen:
                seen.add(key);candidates.append({'name':'rail-signal','position':loc['position'],'direction':loc['direction'],'rail_layer':loc['rail_layer']})
        old=json.loads((ROOT/'blueprints'/f'{ident}.json').read_text());ground=[e for e in old['blueprint']['entities'] if e['name']=='straight-rail']
        dx=row['core_straight_bounds'][0]-min(e['position']['x'] for e in ground);dy=row['core_straight_bounds'][2]-min(e['position']['y'] for e in ground)
        for spacing in spacings:
            sigs=copy.deepcopy(row['signals']);adds=[]
            for c in sorted(candidates,key=lambda e:(e['rail_layer'],e['position']['y'],e['position']['x'],e['direction'])):
                p=c['position']
                if any(s['rail_layer']==c['rail_layer'] and math.hypot(p['x']-s['position']['x'],p['y']-s['position']['y'])<spacing for s in sigs):continue
                sigs.append(c);z=copy.deepcopy(c);z['position']['x']-=dx;z['position']['y']-=dy;adds.append(z)
            doc=copy.deepcopy(old);doc['blueprint']['entities']+=adds
            new=ident.replace('r4-ext-','r4-sig-')+f'-d{spacing}'
            assert nonsig(doc)==nonsig(old)
            save(new,doc)
            out.append({'id':new,'base':ident,'kind':'signal_configuration_not_new_topology','spacing_euclidean':spacing,'added_signals':len(adds),'raw_signal_count':len(sigs),'non_signal_entities_identical':True,'ambiguous_direction_rails_skipped':ambiguous,'native_candidate_evidence':summary['evidence_directory'],'raw_sha256':hashlib.sha256((ROOT/'blueprints'/f'{new}.txt').read_bytes()).hexdigest()})
    (HERE/'generation-manifest.json').write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--ids',required=True,nargs='+');p.add_argument('--spacings',nargs='+',type=int,default=[2,4,8]);a=p.parse_args()
    for r in generate(pathlib.Path(a.graph),a.ids,a.spacings):print(r['id'],r['raw_signal_count'])

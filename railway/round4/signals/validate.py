"""Native normal build, status, 12 static OD; remove only nonworking signals.

No rail changes. Full native journeys are validated separately for selected
candidates, and every traffic run requires original 1+4 consists and no damage.
"""
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE));from generate import save,nonsig
sys.path.insert(0,str(ROOT/'scripts'));from run import run
sys.path.insert(0,str(ROOT/'round4/protocol'));from analyze_graph import cases_for,analyze

def main():
    manifest=json.loads((HERE/'generation-manifest.json').read_text());ids=[r['id'] for r in manifest];pruned=[]
    for iteration in range(4):
        result=run('r4-new-geometry-signal-gate',ROOT/'round4/protocol/graph.lua',{'cases':cases_for(ids)},61,timeout=600)
        (HERE/f'native-iteration-{iteration}.json').write_text(json.dumps(result,indent=2))
        if all(c['all_signals_working'] for c in result['cases']):break
        for c in result['cases']:
            if c['all_signals_working']:continue
            ident=c['id'];doc=json.loads((ROOT/'blueprints'/f'{ident}.json').read_text());ground=[e for e in doc['blueprint']['entities'] if e['name']=='straight-rail'];dx=c['core_straight_bounds'][0]-min(e['position']['x'] for e in ground);dy=c['core_straight_bounds'][2]-min(e['position']['y'] for e in ground)
            def key(e,dx=0,dy=0):return e['name'],e['position']['x']+dx,e['position']['y']+dy,e.get('direction',0),1 if e.get('rail_layer',0) in [1,'elevated'] else 0
            bad={key(s) for s in c['non_working']};old=doc['blueprint']['entities'];new=[e for e in old if key(e,dx,dy) not in bad]
            assert len(old)-len(new)==len(bad);doc['blueprint']['entities']=new;save(ident,doc)
            pruned.append({'id':ident,'iteration':iteration,'signals':c['non_working'],'evidence_directory':result['evidence_directory']})
    else:raise RuntimeError('Signal pruning did not converge')
    assert all(c['all_12_od'] for c in result['cases'])
    for r in manifest:
        assert nonsig(json.loads((ROOT/'blueprints'/f"{r['id']}.json").read_text()))==nonsig(json.loads((ROOT/'blueprints'/f"{r['base']}.json").read_text()))
    (HERE/'signal-pruning.json').write_text(json.dumps(pruned,indent=2))
    summary={'evidence_directory':result['evidence_directory'],'cases':[analyze(c) for c in result['cases']]}
    (HERE/'validation-summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({'valid':len(ids),'pruned_signals':sum(len(r['signals']) for r in pruned),'evidence_directory':result['evidence_directory']}))
if __name__=='__main__':main()

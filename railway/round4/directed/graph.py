import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'));from run import run
s=(ROOT/'round3/signals/graph.lua').read_text().replace('width=1024,height=1024','width=4096,height=4096').replace('s.request_to_generate_chunks({0,0},10)','s.request_to_generate_chunks({0,0},34)')
(HERE/'graph.lua').write_text(s)
ids=sys.argv[1:] or ['r4-dir-crossbar64-source'];cases=[]
for ident in ids:
 es=json.loads((ROOT/'blueprints'/f'{ident}.json').read_text())['blueprint']['entities'];cases.append({'id':ident,'entities':len(es),'blueprint':(ROOT/'blueprints'/f'{ident}.txt').read_text().strip()})
r=run('r4-directed-graph',HERE/'graph.lua',{'cases':cases},61,timeout=300)
(HERE/'graph-results.json').write_text(json.dumps(r,indent=2))
for c in r['cases']:print(c['id'],c['all_12_od'],c['all_signals_working'],[p['length'] for p in c['paths']])
print(r['evidence_directory'])

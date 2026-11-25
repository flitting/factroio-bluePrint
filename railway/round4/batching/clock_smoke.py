import json,sys,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from run import run
source=HERE/'clock_smoke.lua';source.write_text((HERE/'circuit.lua').read_text()+'\n'+(HERE/'clock_smoke_tail.lua').read_text())
raw=run('r4-batch-clock-smoke',source,{'phases':[360,900,1800],'duration':11000},11001,timeout=600)
(HERE/'clock-smoke.json').write_text(json.dumps(raw,indent=2))
for r in raw['cases']:
 traces=r['phase_trace'];durations=[b['tick']-a['tick'] for a,b in zip(traces[1:],traces[2:])]
 print(json.dumps({'id':r['id'],'phase_ticks_observed':sorted(set(durations)),'trace':traces[:6],'final':r['final'],'evidence_directory':raw['evidence_directory']}),flush=True)

#!/usr/bin/env python3
"""Run native signal-density configurations on two additional geometry families."""
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=HERE/'signals';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'round4/protocol'));from analyze_graph import cases_for,analyze
sys.path.insert(0,str(ROOT/'scripts'));from run import run
ids=['r4-ext-cube','r4-ext-three-chunk-square']
result=run('r4-external-extra-geometry-graph',ROOT/'round4/protocol/graph.lua',{'cases':cases_for(ids)},61,timeout=600)
summary={'evidence_directory':result['evidence_directory'],'cases':[analyze(c) for c in result['cases']]};graph=OUT/'base-graph.json';graph.write_text(json.dumps(summary,indent=2))
spec=importlib.util.spec_from_file_location('generate',ROOT/'round4/signals/generate.py');gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen);gen.HERE=OUT;sys.modules['generate']=gen
manifest=gen.generate(graph,ids,[2,4,8]);print('Generated',[(r['id'],r['raw_signal_count']) for r in manifest],flush=True)
spec=importlib.util.spec_from_file_location('r4extra_validate',ROOT/'round4/signals/validate.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);v.HERE=OUT;v.main()
from run_bank import run_case,config
from run_protocol import summarize
rows=[]
for r in manifest:
 raw=run_case(config(r['id'],seed=17,scenario='S1',bank=80,warmup=1800,duration=3600))
 s=summarize(raw);rows.append(s);(OUT/'screen.json').write_text(json.dumps(rows,indent=2));print(json.dumps({k:s[k] for k in ['id','throughput','damage_events','all_od_completed_in_window','evidence_directory']}),flush=True)

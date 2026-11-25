#!/usr/bin/env python3
"""Import pinned community designs into a rail-system-only benchmark view.

Original source JSON is immutable and retained with upstream revision/sha.
The upstream FaTul format uses shift_x/y; apply those shifts before encoding.
Decorative lamps/poles/copper wires and snap grid are omitted in test inputs.
Every rail, signal, rail-layer, ramp and support is preserved.
"""
from pathlib import Path
import json,copy,base64,zlib,hashlib,collections
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
NAMES=['celtic-knot','buffered-celtic-knot','twister','windmill','pinwheel','partially-unrolled-cloverleaf','paperclip','crossover-displaced-left-turn']
rows=[]
for name in NAMES:
    source=HERE/'sources/bocian'/f'{name}.json'
    src=json.loads(source.read_text())['blueprint']; ents=[]
    for orig in src['entities']:
        if 'rail' not in orig['name']:continue
        ent=copy.deepcopy(orig)
        for key in ['x','y']:ent['position'][key]+=src.get('shift_'+key,0)
        ents.append(ent)
    adapters=[]
    if name=='windmill':
        # Upstream EW boundary ends at the ground end of each ramp, without
        # a final straight rail. Four 8-tile stubs expose the same 8 ground ports.
        for xseq in [range(-60,-68,-2),range(68,76,2)]:
            for y in [0,8]:
                for x in xseq:
                    e={'name':'straight-rail','position':{'x':x+src['shift_x'],'y':y+src['shift_y']},'direction':4};ents.append(e);adapters.append(copy.deepcopy(e))
    # Pure even translation centers each design, preserving all rail grid parity.
    xs=[e['position']['x'] for e in ents];ys=[e['position']['y'] for e in ents]
    dx=2*round((min(xs)+max(xs))/4);dy=2*round((min(ys)+max(ys))/4)
    for i,e in enumerate(ents,1):
        e['entity_number']=i;e['position']['x']-=dx;e['position']['y']-=dy
    ident='r4-ext-'+name
    raw={'blueprint':{'item':'blueprint','label':ident,'description':'Benchmark rail-only view of '+src['label']+' by Bocian / Opinionated-Blueprints contributors; pinned source and exact transformations in round4/external.','version':src['version'],'icons':src['icons'],'entities':ents}}
    txt='0'+base64.b64encode(zlib.compress(json.dumps(raw,separators=(',',':')).encode())).decode()
    (ROOT/'blueprints'/f'{ident}.json').write_text(json.dumps(raw,indent=2));(ROOT/'blueprints'/f'{ident}.txt').write_text(txt+'\n')
    rows.append({'id':ident,'upstream_label':src['label'],'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'test_blueprint_sha256':hashlib.sha256(txt.encode()).hexdigest(),'original_entity_count':len(src['entities']),'rail_system_entity_count':len(ents),'removed_nonrail_entities':dict(collections.Counter(e['name'] for e in src['entities'] if 'rail' not in e['name'])),'added_adapter_entities':len(adapters),'adapter_note':'Four 8-tile ground rail stubs on EW ramp ground ends; counted in candidate area.' if adapters else None,'applied_upstream_shift':[src.get('shift_x',0),src.get('shift_y',0)],'centering_translation':[-dx,-dy],'native_validation':'pending'})
(HERE/'import-manifest.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))

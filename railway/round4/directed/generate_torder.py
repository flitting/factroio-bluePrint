from generate import *
cases=[];manifest=[]
for ident,C,H,compact in [('r4-dir-torder32-16',32,16,2),('r4-dir-torder64-64',64,64,False)]:
 bp,case,meta=generate(ident,C,H,'torder',compact)
 meta['hypothesis']='Control: all four inlets split off straight traffic first; all four exits merge straight traffic last, matching the native reference T branch-order invariant; geometric embedding is generated from scratch.'
 cases.append(case);manifest.append(meta)
 (HERE/f'{ident}-raw.json').write_text(json.dumps(bp,indent=2));(HERE/f'{ident}-raw.txt').write_text(case['blueprint']+'\n')
(HERE/'torder-cases.json').write_text(json.dumps(cases,indent=2));(HERE/'torder-manifest.json').write_text(json.dumps(manifest,indent=2))
print([(c['id'],c['entities'],c['bounds']) for c in manifest])

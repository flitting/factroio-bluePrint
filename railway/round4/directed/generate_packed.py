from generate import *
cases=[];manifest=[]
for packed in [0,2,7,17]:
 for order in ['source','reverse']:
  ident=f'r4-dir-pack{packed}-'+('rev' if order=='reverse' else 'fwd')
  bp,case,meta=generate(ident,32,16,order,2,packed);cases.append(case);manifest.append(meta)
  (HERE/f'{ident}-raw.json').write_text(json.dumps(bp,indent=2));(HERE/f'{ident}-raw.txt').write_text(case['blueprint']+'\n')
(HERE/'packed-cases.json').write_text(json.dumps(cases,indent=2));(HERE/'packed-manifest.json').write_text(json.dumps(manifest,indent=2))
print([(c['id'],c['entities'],c['bounds']) for c in manifest])

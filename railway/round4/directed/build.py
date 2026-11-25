import sys,json,zlib,base64
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'));from run import run
cases=json.loads((HERE/'cases.json').read_text())
if (HERE/'packed-cases.json').exists():cases+=json.loads((HERE/'packed-cases.json').read_text())
if (HERE/'torder-cases.json').exists():cases+=json.loads((HERE/'torder-cases.json').read_text())
if (HERE/'trident-cases.json').exists():cases+=json.loads((HERE/'trident-cases.json').read_text())
if len(sys.argv)>1:cases=[c for c in cases if c['id'] in sys.argv[1:]]
r=run('r4-directed-build',HERE/'build.lua',{'cases':cases},61,timeout=300)
(HERE/('build-'+cases[0]['id']+'-'+str(len(cases))+'.json')).write_text(json.dumps(r,indent=2))
for c in r['cases']:
 print(c['id'],c['build_complete'],'ghosts',c['ghosts'],'expected',c['expected'],'remaining',len(c['remaining']),'missing',len(c['missing']),'conflicts',len(c['direction_conflicts']),'signals',len(c['signals']))
 if c['build_complete'] and not c['missing'] and not c['direction_conflicts']:
  bp=json.loads(zlib.decompress(base64.b64decode(c['blueprint'][1:])))
  for out in [HERE,ROOT/'blueprints']:
   (out/(c['id']+'.json')).write_text(json.dumps(bp,indent=2));(out/(c['id']+'.txt')).write_text(c['blueprint']+'\n')
print(r['evidence_directory'])

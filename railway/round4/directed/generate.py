"""De novo 12-OD two-layer crossbar, ground vertical trunks/high horizontal links.
All curve modules are 2.1 quarter-turn primitives. No original blueprint geometry
is copied; the contracted split/private-connect/merge graph can match a reference.
"""
import json,base64,zlib,copy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
BASE=[('curved-rail-a',0,2,10),('curved-rail-b',-2,7,10),('curved-rail-b',-6,11,4),('curved-rail-a',-11,13,4)]
NAMES='NESW'
def rot(x,y,k):
 for _ in range(k%4): x,y=-y,x
 return x,y

def generate(ident,C=64,H=64,order='source',compact=False,packed=None):
 entities={};segments=[]
 def add(n,x,y,d=0):
  q={'name':n,'position':{'x':x,'y':y},'direction':d%16};key=(n,x,y,d%16)
  entities[key]=q;return q
 def line(a,b,high=False):
  x,y=a;X,Y=b;out=[];assert x==X or y==Y
  dx=0 if x==X else (1 if X>x else -1);dy=0 if y==Y else (1 if Y>y else -1)
  length=abs(X-x)+abs(Y-y);assert length%2==0,(a,b)
  for off in range(1,length,2):out.append(add(('elevated-' if high else '')+'straight-rail',x+dx*off,y+dy*off,4 if dx else 0))
  if high:
   assert y==Y
   for sx in range(min(x,X),max(x,X)+1):
    # Keep the ground foot away from all vertical trunks.
    if (sx-(1-C*3.5+7))%16==0: add('rail-support',sx,y,4)
  return out
 def curve(x,y,v,h):
  k=0 if v==1 else 2;mir=(v==h);out=[]
  for n,a,b,d in BASE:
   if mir:a,d=-a,(18-d)%16
   a,b=rot(a,b,k);out.append(add(n,x+a,y+b,d+4*k))
  return out
 def bridge(a,b):
  x,y=a;X,Y=b;assert y==Y;h=1 if X>x else -1
  if abs(X-x)<32: return line(a,b,False)
  up=add('rail-ramp',x+h*8,y,4 if h==1 else 12)
  down=add('rail-ramp',X-h*8,y,12 if h==1 else 4)
  return [up]+line((x+h*16,y),(X-h*16,y),True)+[down]
 cols=[int(1+(i-3.5)*C) for i in range(8)]
 assert all(c%2==1 for c in cols)
 source=dict(zip('NESW',[cols[0],cols[2],cols[7],cols[5]]))
 target=dict(zip('NESW',[cols[1],cols[3],cols[6],cols[4]]))
 if packed is not None:
  solution=json.loads((HERE/'column-order-search.json').read_text())['solutions'][packed]
  permutation,groups=solution
  source={n:cols[permutation.index('i'+n)] for n in NAMES};target={n:cols[permutation.index('o'+n)] for n in NAMES}
 vin={'N':1,'E':1,'S':-1,'W':-1};vout={'N':-1,'E':1,'S':1,'W':-1}
 ods=[o+d for o in NAMES for d in NAMES if o!=d]
 if order=='destination':ods.sort(key=lambda z:(NAMES.index(z[1]),NAMES.index(z[0])))
 elif order=='straight-first':ods.sort(key=lambda z:((NAMES.index(z[1])-NAMES.index(z[0]))%4!=2,NAMES.index(z[0]),NAMES.index(z[1])))
 elif order=='interleave':ods=[NAMES[o]+NAMES[(o+delta)%4] for delta in [2,3,1] for o in [0,2,1,3]]
 elif order=='torder':ods=['EW','ES','WS','NS','NE','NW','SE','SW','SN','EN','WN','WE']
 rows={od:int(1+(i-5.5)*H) for i,od in enumerate(ods)}
 if packed is not None:
  if order=='reverse':groups=list(reversed(groups))
  ods=[od for group in groups for od in group];rows={od:int(1+(i-(len(groups)-1)/2)*H) for i,group in enumerate(groups) for od in group}
 assert all(r%2==1 for r in rows.values())
 ycore=max(abs(r) for r in rows.values());a1=ycore+(32 if compact else 128);a2=ycore+(64 if compact else 192);B=ycore+(80 if compact==2 else 96 if compact else 320)
 # odd endpoints for port centers, even endpoints for line() geometry.
 if B%2==0:B+=1
 A=max(abs(c) for c in cols)+(48 if compact==2 else 64 if compact else 256)
 if A%2==0:A+=1
 adapter={'E':-a1,'W':a2};exit_adapter={'E':a1,'W':-a2}
 # Source and target ground shafts, ending exactly at last branch.
 for o in NAMES:
  ends=[rows[od]-vin[o]*13 for od in ods if od[0]==o]
  end=max(ends) if vin[o]==1 else min(ends)
  start=(-B-1 if o=='N' else B+1 if o=='S' else adapter[o]+vin[o]*13)
  segments.append(line((source[o],start),(source[o],end)))
 for d in NAMES:
  ends=[rows[od]+vout[d]*13 for od in ods if od[1]==d]
  start=max(ends) if vout[d]==-1 else min(ends)
  end=(-B-1 if d=='N' else B+1 if d=='S' else exit_adapter[d]-vout[d]*13)
  segments.append(line((target[d],start),(target[d],end)))
 # Twelve explicitly private transverse connectors.
 paths={}
 for od in ods:
  o,d=od;x,X=source[o],target[d];y=rows[od];h=1 if X>x else -1
  first=curve(x,y-vin[o]*13,vin[o],h)
  last=list(reversed(curve(X,y+vout[d]*13,-vout[d],-h)))
  p=first+bridge((x+h*13,y),(X-h*13,y))+last
  segments.append(p);paths[od]=p
 # Four adapters preserve the 8 external N/E/S/W one-way ports.
 for o in ['E','W']:
  x=source[o];y=adapter[o];h=-1 if o=='E' else 1;outer=A+1 if o=='E' else -A-1
  endpoint=x-h*13
  p=line((outer,y),(outer+h*24,y))+bridge((outer+h*24,y),(endpoint,y))+list(reversed(curve(x,y+vin[o]*13,-vin[o],-h)))
  segments.append(p)
 for d in ['E','W']:
  x=target[d];y=exit_adapter[d];h=1 if d=='E' else -1;outer=A+1 if d=='E' else -A-1
  p=curve(x,y-vout[d]*13,vout[d],h)+bridge((x+h*13,y),(outer-h*24,y))+line((outer-h*24,y),(outer,y))
  segments.append(p)
 bp={'blueprint':{'item':'blueprint','label':ident,'version':562954249568256,'entities':list(entities.values())}}
 for i,e in enumerate(bp['blueprint']['entities'],1):e['entity_number']=i
 code='0'+base64.b64encode(zlib.compress(json.dumps(bp,separators=(',',':')).encode())).decode()
 meta={'id':ident,'family':'directed-12-link-crossbar','columns':C,'row_spacing':H,'order':order,'compact_adapters':compact,'packing_solution':packed,'row_od_order':ods,'rows':rows,'source_columns':source,'target_columns':target,'entities':len(entities),'bounds':[-A,A,-B,B],'notes':'8 external ports; 12 private high transverse links; vertical source trunks and vertical output trunks only; no intentional at-grade crossings.'}
 case={'id':ident,'blueprint':code,'expected':len(entities),'segments':segments,'minx':min(e['position']['x'] for e in entities.values()),'miny':min(e['position']['y'] for e in entities.values()),'extent':max(A,B)+64,'signal_spacing':4}
 return bp,case,meta

def main():
 cases=[];manifest=[]
 for ident,C,H,order,compact in [('r4-dir-crossbar64-source',64,64,'source',False),('r4-dir-crossbar64-destination',64,64,'destination',False),('r4-dir-crossbar64-interleave',64,64,'interleave',False),('r4-dir-crossbar64-straightfirst',64,64,'straight-first',False),('r4-dir-crossbar32-source',64,32,'source',True),('r4-dir-crossbar16-source',64,16,'source',True),('r4-dir-crossbar16-interleave',64,16,'interleave',True)]:
  bp,case,meta=generate(ident,C,H,order,compact);cases.append(case);manifest.append(meta)
  (HERE/f'{ident}-raw.json').write_text(json.dumps(bp,indent=2))
  (HERE/f'{ident}-raw.txt').write_text(case['blueprint']+'\n')
 (HERE/'cases.json').write_text(json.dumps(cases,indent=2));(HERE/'generation-manifest.json').write_text(json.dumps(manifest,indent=2))
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()

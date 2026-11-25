"""True native ternary input/output fork geometry, then 12 private OD links.
No binary source trunk is reused: each OD has a separate source and target column.
"""
from generate import *

def make_trident(ident='r4-dir-trident32-32',C=32,H=32):
 entities={};segments=[]
 def add(n,x,y,d=0):
  q={'name':n,'position':{'x':x,'y':y},'direction':d%16};entities[(n,x,y,d%16)]=q;return q
 def line(a,b,high=False):
  x,y=a;X,Y=b;assert x==X or y==Y
  dx=0 if x==X else (1 if X>x else -1);dy=0 if y==Y else (1 if Y>y else -1);length=abs(X-x)+abs(Y-y);assert length%2==0
  out=[add(('elevated-' if high else '')+'straight-rail',x+dx*k,y+dy*k,4 if dx else 0) for k in range(1,length,2)]
  if high:
   assert y==Y
   for sx in range(min(x,X),max(x,X)+1):
    if (sx-8)%16==0:add('rail-support',sx,y,4)
  return out
 def curve(x,y,v,h):
  out=[];k=0 if v==1 else 2;mirror=(v==h)
  for n,a,b,d in BASE:
   if mirror:a,d=-a,(18-d)%16
   a,b=rot(a,b,k);out.append(add(n,x+a,y+b,d+4*k))
  return out
 def bridge(a,b):
  x,y=a;X,Y=b;assert y==Y;h=1 if X>x else -1
  if abs(X-x)<32:return line(a,b)
  return [add('rail-ramp',x+h*8,y,4 if h==1 else 12)]+line((x+h*16,y),(X-h*16,y),True)+[add('rail-ramp',X-h*8,y,12 if h==1 else 4)]
 def fan(center,y,v):
  parts={0:line((center,y),(center,y+v*26))}
  for h in [-1,1]:
   parts[h]=curve(center,y,v,h)+line((center+h*13,y+v*13),(center+h*C-h*13,y+v*13))+list(reversed(curve(center+h*C,y+v*26,-v,-h)))
  return parts
 centers=[int(1+(i-3.5)*3*C) for i in range(8)]
 sc=dict(zip(NAMES,[centers[0],centers[2],centers[7],centers[5]]));tc=dict(zip(NAMES,[centers[1],centers[3],centers[6],centers[4]]))
 vin={'N':1,'E':1,'S':-1,'W':-1};vout={'N':-1,'E':1,'S':1,'W':-1}
 ods=[o+d for o in NAMES for d in NAMES if o!=d]
 rows={od:int(1+(i-5.5)*H) for i,od in enumerate(ods)};ycore=max(abs(y) for y in rows.values())
 fork={o:-vin[o]*(ycore+65) for o in NAMES};merge={d:vout[d]*(ycore+65) for d in NAMES}
 A=max(abs(c) for c in centers)+C+64;B=ycore+288
 if A%2==0:A+=1
 if B%2==0:B+=1
 ay={'E':-(ycore+160),'W':ycore+224};by={'E':ycore+160,'W':-(ycore+224)}
 # Trident fans have one straight and two symmetric turning exits at one native rail end.
 for o in NAMES:
  for p in fan(sc[o],fork[o],vin[o]).values():segments.append(p)
  start=-B-1 if o=='N' else B+1 if o=='S' else ay[o]+vin[o]*13
  segments.append(line((sc[o],start),(sc[o],fork[o])))
 for d in NAMES:
  for p in fan(tc[d],merge[d],-vout[d]).values():segments.append(list(reversed(p)))
  end=-B-1 if d=='N' else B+1 if d=='S' else by[d]-vout[d]*13
  segments.append(line((tc[d],merge[d]),(tc[d],end)))
 source={};target={}
 for od in ods:
  o,d=od;delta=(NAMES.index(d)-NAMES.index(o))%4
  side=0 if delta==2 else -vin[o] if delta==3 else vin[o]
  source[od]=sc[o]+side*C
  backdelta=(NAMES.index(o)-NAMES.index(d))%4
  other=0 if backdelta==2 else vout[d] if backdelta==3 else -vout[d]
  target[od]=tc[d]+other*C
  x,X=source[od],target[od];y=rows[od];h=1 if X>x else -1
  segments.append(line((x,fork[o]+vin[o]*26),(x,y-vin[o]*13)))
  p=curve(x,y-vin[o]*13,vin[o],h)+bridge((x+h*13,y),(X-h*13,y))+list(reversed(curve(X,y+vout[d]*13,-vout[d],-h)))
  segments.append(p)
  segments.append(line((X,y+vout[d]*13),(X,merge[d]-vout[d]*26)))
 for o in ['E','W']:
  x=sc[o];y=ay[o];h=-1 if o=='E' else 1;outer=A+1 if o=='E' else -A-1
  segments.append(line((outer,y),(outer+h*24,y))+bridge((outer+h*24,y),(x-h*13,y))+list(reversed(curve(x,y+vin[o]*13,-vin[o],-h))))
 for d in ['E','W']:
  x=tc[d];y=by[d];h=1 if d=='E' else -1;outer=A+1 if d=='E' else -A-1
  segments.append(curve(x,y-vout[d]*13,vout[d],h)+bridge((x+h*13,y),(outer-h*24,y))+line((outer-h*24,y),(outer,y)))
 es=list(entities.values());bp={'blueprint':{'item':'blueprint','label':ident,'version':562954249568256,'entities':es}}
 for i,e in enumerate(es,1):e['entity_number']=i
 code='0'+base64.b64encode(zlib.compress(json.dumps(bp,separators=(',',':')).encode())).decode()
 case={'id':ident,'blueprint':code,'expected':len(es),'segments':segments,'minx':min(e['position']['x'] for e in es),'miny':min(e['position']['y'] for e in es),'extent':max(A,B)+64,'signal_spacing':4}
 meta={'id':ident,'family':'ternary-trident-12-private-links','column_spacing':C,'row_spacing':H,'source_centers':sc,'output_centers':tc,'source_columns_by_od':source,'output_columns_by_od':target,'rows':rows,'fork_points':fork,'merge_points':merge,'raw_entities':len(es),'bounds':[-A,A,-B,B],'native_gate_required':'Prove three outgoing native rail neighbors at each first fork; three incoming neighbors at final merge; 12 OD and all working signals; no arbitrary API creation bypass.'}
 return bp,case,meta

if __name__=='__main__':
 bp,case,meta=make_trident()
 (HERE/(case['id']+'-raw.json')).write_text(json.dumps(bp,indent=2));(HERE/(case['id']+'-raw.txt')).write_text(case['blueprint']+'\n')
 (HERE/'trident-cases.json').write_text(json.dumps([case],indent=2));(HERE/'trident-manifest.json').write_text(json.dumps([meta],indent=2))
 print(json.dumps(meta,indent=2))

"""De novo central elevated circulation ring plus independent straight corridors.

Geometry uses only verified 90-degree primitive, not any user blueprint route.
Four external RHT one-way pairs. Ring feeders are elevated after an initial
right fork; exits descend off the ring and dogleg to a late output merge.
"""
import json,base64,zlib,copy
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
BASE=[('curved-rail-a',0,2,10),('curved-rail-b',-2,7,10),('curved-rail-b',-6,11,4),('curved-rail-a',-11,13,4)]
V=[(0,-1),(1,0),(0,1),(-1,0)]
def rot(x,y,k):
 for _ in range(k%4):x,y=-y,x
 return x,y
def key(e):return e['name'],e['position']['x'],e['position']['y'],e.get('direction',0)
def rail(n,x,y,d):return {'name':n,'position':{'x':x,'y':y},'direction':d%(8 if n in ('straight-rail','elevated-straight-rail') else 16)}
def line(a,b,high=False):
 x,y=a;u,v=b;assert x==u or y==v
 d=0 if x==u else 4;dx=0 if x==u else (1 if u>x else -1);dy=0 if y==v else (1 if v>y else -1)
 n=abs(u-x)+abs(v-y);assert n%2==0,(a,b,n)
 return [rail(('elevated-' if high else '')+'straight-rail',x+dx*i,y+dy*i,d) for i in range(1,n,2)]
def quarter(a,h,right=True,high=False):
 k=(h-2)%4;out=[]
 for n,x,y,d in BASE:
  if not right:x,d=-x,(18-d)%16
  x,y=rot(x,y,k);out.append(rail(('elevated-' if high else '')+n,a[0]+x,a[1]+y,d+4*k))
 dx,dy=rot((-13 if right else 13),13,k)
 return out,(a[0]+dx,a[1]+dy),(h+(1 if right else -1))%4

def ramp(a,h,up=True):
 dx,dy=V[h];return [rail('rail-ramp',a[0]+8*dx,a[1]+8*dy,(h if up else (h+2)%4)*4)],(a[0]+16*dx,a[1]+16*dy)

def transformed(p,k):
 out=[]
 for e in p:
  x,y=rot(e['position']['x'],e['position']['y'],k);out.append(rail(e['name'],x,y,e.get('direction',0)+4*k))
 return out

def make(R=75,near=False,highcore=False):
 E=R+99;paths={};features=[];lane=5 if highcore else 1
 # Four straight native lanes, with optional N/S central bridge.
 for k in range(4):
  if highcore and k%2==0:
   a=(-lane,-E);b=(-lane,-32);p=line(a,b);q,c=ramp(b,2,True);p+=q;p+=line(c,(-lane,16),True);q,c=ramp((-lane,16),2,False);p+=q;p+=line(c,(-lane,E));paths[f'core{k}']=transformed(p,k)
  else:paths[f'core{k}']=transformed(line((-lane,-E),(-lane,E)),k)
 # High ring. Base westbound upper segment and NW corner then west side.
 for k in range(4):
  p=line((R-13,-R),(-R+13,-R),True)
  q,c,h=quarter((-R+13,-R),3,False,True);p+=q
  p+=line(c,(-R,R-13),True)
  # Include the first rail of next corner so last straight gets direction.
  q,_,_=quarter((-R,R-13),2,False,True);p+=q[:1]
  paths[f'ring{k}']=transformed(p,k)
 # Feeder, rotated N entrance. Goes right, climbs, then turns left to join west ring.
 p,q,h=quarter((-lane,-R-29),2,True,False)
 a,q=ramp(q,h,True);p+=a
 p+=line(q,(-R+13,-R-16),True)
 a,q,h=quarter((-R+13,-R-16),3,False,True);p+=a
 p+=line(q,(-R,-R+15),True)
 # Exit, base W outlet. Off-ring right; descend then dogleg into late output merge.
 z,q,h=quarter((-R,-lane-39),2,True,True)
 a,q=ramp(q,h,False);z+=a
 a,q,h=quarter(q,h,False,False);z+=a
 a,q,h=quarter(q,h,True,False);z+=a
 z+=line(q,(q[0]-2,q[1]),False)
 for k in range(4):paths[f'feed{k}']=transformed(p,k);paths[f'exit{k}']=transformed(z,k)
 if near:
  for k in range(4):
   if highcore:
    q,end,h=quarter((-lane,-lane-39),2,True,False)
    a,end,h=quarter(end,h,False,False);q+=a
    a,end,h=quarter(end,h,True,False);q+=a
    q+=line(end,(end[0]-2,end[1]))
   else:
    q,end,h=quarter((-lane,-lane-13),2,True,False);q+=line(end,(end[0]-2,end[1]))
   paths[f'near{k}']=transformed(q,k)
 ents={}
 for p in paths.values():
  for e in p:ents[key(e)]=e
 ent=list(ents.values());ident=f'r4-net-ring-{R}'+('-near' if near else '')+('-bridge' if highcore else '')
 for i,e in enumerate(ent,1):e['entity_number']=i
 doc={'blueprint':{'item':'blueprint','label':ident,'version':562949957943296,'entities':ent}}
 bp='0'+base64.b64encode(zlib.compress(json.dumps(doc,separators=(',',':')).encode())).decode()
 (HERE/f'{ident}-raw.json').write_text(json.dumps(doc,indent=2));(HERE/f'{ident}-raw.txt').write_text(bp+'\n')
 return {'id':ident,'blueprint':bp,'expected':len(ent),'minx':min(e['position']['x'] for e in ent),'miny':min(e['position']['y'] for e in ent),'paths':paths,'radius':R,'near_bypass':near,'central_ns_bridge':highcore,'external_lane_offset':lane,'signal_spacing':4,'signal_policy':'chains_inside'}
if __name__=='__main__':
 cases=[make(R,near,bridge) for R in [75,91] for near,bridge in [(False,False),(True,False),(False,True),(True,True)]]
 (HERE/'cases.json').write_text(json.dumps(cases));print([(c['id'],c['expected']) for c in cases])

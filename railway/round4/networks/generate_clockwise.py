"""New directed high ring: far turns use only one quadrant, near/straight bypass.

Widening the two external rails allows the far-turn ramp to finish between
opposite ground mainlines, avoiding the opposite direction at grade. No user
blueprint rail route is used.
"""
import json,base64,zlib
from pathlib import Path
from generate import rail,line,quarter,ramp,rot,transformed,key
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
BASE=[('curved-rail-a',0,2,10),('curved-rail-b',-2,7,10),('curved-rail-b',-6,11,4),('curved-rail-a',-11,13,4)]
def widequarter(a,h,right=True,high=False,span=61):
 n=(span-13)//2;assert span>=13 and (span-13)%2==0
 out=[];k=(h-2)%4;raw=BASE[:2]+[('straight-rail',-5-2*i,10+2*i,2) for i in range(n)]+[(nm,x-2*n,y+2*n,d) for nm,x,y,d in BASE[2:]]
 for nm,x,y,d in raw:
  if not right:x,d=-x,((-d)%8 if nm=='straight-rail' else (18-d)%16)
  x,y=rot(x,y,k);out.append(rail(('elevated-' if high else '')+nm,a[0]+x,a[1]+y,d+4*k))
 dx,dy=rot(-span if right else span,span,k)
 return out,(a[0]+dx,a[1]+dy),(h+(1 if right else -1))%4

def make(R=75,lane=17,span=61,bridge=True,clockwise=True,private=False,exit_extension=16,bridge_half=48):
 assert lane%2==1 and R%2==1
 E=R+99+exit_extension;paths={}
 for k in range(4):
  if bridge and k%2==0:
   p=line((-lane,-E),(-lane,-bridge_half-16));q,a=ramp((-lane,-bridge_half-16),2,True);p+=q;p+=line(a,(-lane,bridge_half),True);q,a=ramp((-lane,bridge_half),2,False);p+=q;p+=line(a,(-lane,E))
  else:p=line((-lane,-E),(-lane,E))
  paths[f'core{k}']=transformed(p,k)
 for k in range(4):
  p=line((-R+13,-R),(R-13,-R),True)
  q,a,h=quarter((R-13,-R),1,True,True);p+=q;p+=line(a,(R,R-13),True)
  q,_,_=quarter((R,R-13),2,True,True);p+=q[:1]
  if not private:paths[f'ring{k}']=transformed(p,k)
 # Left fork from N input; ramp ends before crossing N output ground line.
 p,a,h=quarter((-lane,-R-29),2,False,False)
 q,a=ramp(a,h,True);p+=q;p+=line(a,(R-13,-R-16),True)
 q,a,h=quarter((R-13,-R-16),1,True,True);p+=q
 p+=line(a,(R,lane-39 if private else -R+15),True)
 # E output. Ramp comes down outside the through corridors, then late merge.
 z,a,h=quarter((R,lane-39),2,False,True)
 if exit_extension:
  b=(a[0]+exit_extension,a[1]);z+=line(a,b,True);a=b
 q,a=ramp(a,h,False);z+=q
 q,a,h=quarter(a,h,True,False);z+=q;q,a,h=quarter(a,h,False,False);z+=q
 z+=line(a,(a[0]+2,a[1]))
 for k in range(4):
  paths[f'feed{k}']=transformed(p,k);paths[f'exit{k}']=transformed(z,k)
  q,a,h=widequarter((-lane,-lane-span),2,True,False,span);q+=line(a,(a[0]-2,a[1]));paths[f'near{k}']=transformed(q,k)
 ents={key(e):e for p in paths.values() for e in p};ents=list(ents.values())
 for i,e in enumerate(ents,1):e['entity_number']=i
 ident=f'r4-net-'+('quadrant-direct' if private else 'farring')+f'-r{R}-l{lane}-n{span}-e{exit_extension}-h{bridge_half}'+('' if bridge else '-planar')
 doc={'blueprint':{'item':'blueprint','label':ident,'version':562949957943296,'entities':ents}};code='0'+base64.b64encode(zlib.compress(json.dumps(doc,separators=(',',':')).encode())).decode()
 (H/f'{ident}-raw.json').write_text(json.dumps(doc,indent=2));(H/f'{ident}-raw.txt').write_text(code+'\n')
 return {'id':ident,'blueprint':code,'expected':len(ents),'minx':min(e['position']['x'] for e in ents),'miny':min(e['position']['y'] for e in ents),'paths':paths,'radius':R,'near_span':span,'near_bypass':True,'central_ns_bridge':bridge,'external_lane_offset':lane,'signal_spacing':4,'signal_policy':'chains_inside','ring_direction':'clockwise','private_far_connectors':private,'exit_extension':exit_extension,'bridge_half':bridge_half}
if __name__=='__main__':
 cases=[make(75,17,61,private=True),make(75,17,77,private=True),make(43,17,61,private=True,bridge_half=32),make(35,17,61,private=True,bridge_half=32),make(75,17,61),make(75,17,61,False,private=True)]
 (H/'clockwise-cases.json').write_text(json.dumps(cases));print([(c['id'],c['expected']) for c in cases])

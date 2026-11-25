#!/usr/bin/env python3
"""Common deterministic arrival traces; no queued demand is discarded."""
import argparse, hashlib, json, math, random
from pathlib import Path
NAMES=['N','E','S','W']
WEIGHTS={'S1':(1/3,1/3,1/3),'S2':(.15,.7,.15),'S3':(.7,.15,.15),'S4':(.15,.15,.7)}
def generate(scenario,seed,rate,duration_ticks,warmup_ticks=0):
 """rate is total offered trains/min, timing in simulation ticks (60/s)."""
 rate=float(rate);rng=random.Random(seed);end=duration_ticks+warmup_ticks;events=[];blocks=[]
 turn_weights=WEIGHTS.get(scenario,WEIGHTS['S1'])
 def append(t,o,d=None):
  if d is None:
   u=rng.random();d=(o-1)%4 if u<turn_weights[0] else ((o+2)%4 if u<sum(turn_weights[:2]) else (o+1)%4)
  events.append({'tick':int(t),'origin':NAMES[o],'destination':NAMES[d]})
 if scenario=='S9':
  if end<15600:raise ValueError('S9 requires at least 15600 ticks to cover 12 isolated OD requests and drain; use --warmup 0 --duration 18000.')
  for index in range(12):
   o=index//3;d=[d for d in range(4) if d!=o][index%3];append((index+1)*1200,o,d)
 else:
  origin_weights=[.7,.1,.1,.1] if scenario=='S5' else [.25]*4
  for o,w in enumerate(origin_weights):
   t=0.;lam=rate*w/3600
   while lam>0:
    t+=rng.expovariate(lam)
    if t>end:break
    append(t,o)
  if scenario=='S6':
   for _ in range(80):append(warmup_ticks+1800,0)
  if scenario=='S8':
   for burst in range(8):
    t=rng.randrange(warmup_ticks+1,end)
    for o in rng.sample(range(4),rng.randint(2,4)):
     for _ in range(rng.randint(8,24)):append(t,o)
  if scenario=='S7':blocks=[{'exit':'W','from_tick':warmup_ticks+1800,'to_tick':warmup_ticks+5400}]
  if scenario=='S10':
   events=[]
   for o in range(4):
    for t in range(0,end+1,12):append(t,o)
 events.sort(key=lambda e:(e['tick'],e['origin']))
 for i,e in enumerate(events):e['id']=i+1
 doc={'scenario':scenario,'seed':seed,'offered_total_per_min':1200 if scenario=='S10' else (43200/end if scenario=='S9' else rate),'warmup_ticks':warmup_ticks,'duration_ticks':duration_ticks,'events':events,'exit_blocks':blocks,'origin_order':NAMES,'turn_convention':'right hand traffic: near=(origin-1)%4; straight=(origin+2)%4; far=(origin+1)%4','queue_policy':'retain all unsent requests; FIFO per inlet; no disappearing requests'}
 doc['sha256']=hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(',',':')).encode()).hexdigest();return doc
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,default=1);p.add_argument('--rate',type=float,default=80);p.add_argument('--duration',type=int,default=18000);p.add_argument('--warmup',type=int,default=7200);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 for i in range(1,11):
  d=generate(f'S{i}',a.seed,a.rate,a.duration,a.warmup);(a.output/f'S{i}-seed{a.seed}.json').write_text(json.dumps(d,indent=2))

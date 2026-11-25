"""Descriptive longer-window diagnostics; does not pool different bank protocols."""
import json,math
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def percentile(xs,p):
 xs=sorted(xs)
 if not xs:return None
 k=(len(xs)-1)*p;i=int(k);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(k-i)
rows=[]
for fn in ['formal-selected.json','formal-long-tail.json']:
 p=H/fn
 if not p.exists():continue
 for summary in json.loads(p.read_text()):
  raw=json.loads((R/summary['evidence_directory']/'script-output/result.json').read_text());cfg=raw['config'];records=raw['records'];lo=cfg['warmup'];hi=lo+cfg['duration'];inf=10**30
  done=[r for r in records if lo<=r.get('complete_tick',inf)<hi];entered=sum(lo<=r.get('entry_tick',inf)<hi for r in records)
  inflight=lambda t:sum(r.get('entry_tick',inf)<t and r.get('complete_tick',inf)>=t for r in records)
  ib,ia=inflight(lo),inflight(hi);assert len(done)-entered==ib-ia
  od=[]
  for o in range(1,5):
   for d in range(1,5):
    if o==d:continue
    rr=[r for r in records if r['origin']==o and r['destination']==d];tt=sorted(r['complete_tick'] for r in rr if lo<=r.get('complete_tick',inf)<hi)
    pending_start=sum(r.get('complete_tick',inf)>=lo for r in rr);pending_end=sum(r.get('complete_tick',inf)>=hi for r in rr)
    gaps=[(b-a)/60 for a,b in zip(tt,tt[1:])]
    if pending_start and tt:gaps.append((tt[0]-lo)/60)
    if pending_end and tt:gaps.append((hi-tt[-1])/60)
    if pending_start and not tt:gaps.append((hi-lo)/60)
    od.append({'od':'NESW'[o-1]+'-'+'NESW'[d-1],'completed':len(tt),'pending_start':pending_start,'pending_end':pending_end,'maximum_observed_service_gap_seconds':max(gaps,default=0),'boundary_gaps_are_censored':True})
  latency=[(r['complete_tick']-r['entry_tick'])/60 for r in done]
  row={'id':summary['id'],'group':'bank150/warm3600/measure10800/seed17','throughput':summary['throughput'],'completed':len(done),'entered':entered,'inflight_start':ib,'inflight_end':ia,'inventory_balance_verified':True,'bins_60_seconds':[sum(t<=r.get('complete_tick',inf)<t+3600 for r in records) for t in range(lo,hi,3600)],'crossing_latency_seconds_mean':sum(latency)/len(latency),'crossing_latency_seconds_p95':percentile(latency,.95),'od':od,'evidence_directory':summary['evidence_directory'],'definitions':'Inflight is between the fixed entry and completion measurement planes, not exact physical membership of the blueprint AABB. Crossing latency is conditional on completion in the measurement window. Max service gaps include boundary-censored lower bounds only while requests remain; finite gaps are not deadlock proofs.'}
  rows.append(row)
(H/'formal-diagnostics.json').write_text(json.dumps(rows,indent=2));print([{k:r[k] for k in ['id','throughput','entered','inflight_start','inflight_end','bins_60_seconds','crossing_latency_seconds_mean','crossing_latency_seconds_p95']} for r in rows])

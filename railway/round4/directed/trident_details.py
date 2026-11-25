"""Read-only latency / service balance diagnostics for completed trident cases."""
import json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def describe(summary):
 raw=json.loads((ROOT/summary['evidence_directory']/'script-output/result.json').read_text());w=raw['config']['warmup'];end=w+raw['config']['duration']
 times={i:[] for i in range(1,5)};bydest=collections.Counter();byod=collections.Counter();odtimes={a+'-'+b:[] for a in 'NESW' for b in 'NESW' if a!=b}
 for r in raw['records']:
  if w<=r.get('complete_tick',-1)<end:
   od='NESW'[r['origin']-1]+'-'+'NESW'[r['destination']-1]
   times[r['origin']].append(r['complete_tick']);bydest[r['destination']]+=1;byod[od]+=1;odtimes[od].append(r['complete_tick'])
 gaps={}
 for side,ts in times.items():
  ts=sorted(ts);points=[w]+ts+[end];gaps['NESW'[side-1]]=max(b-a for a,b in zip(points,points[1:]))/60
 odgaps={}
 for od,ts in odtimes.items():
  points=[w]+sorted(ts)+[end];odgaps[od]=max(b-a for a,b in zip(points,points[1:]))/60
 samples={s['tick']:s for s in raw['samples']}
 bins=[{'from_tick':start,'to_tick_exclusive':min(start+3600,end),'completed':sum(start<=r.get('complete_tick',-1)<min(start+3600,end) for r in raw['records'])} for start in range(w,end,3600)]
 assert sum(b['completed'] for b in bins)==raw['completed']
 return {'seed':raw['seed'],'evidence_directory':summary['evidence_directory'],'bank':raw['config']['bank'],'warmup':w,'duration':end-w,'throughput':raw['throughput'],'completed_by_origin':{'NESW'[i-1]:len(times[i]) for i in range(1,5)},'completed_by_destination':{'NESW'[i-1]:bydest[i] for i in range(1,5)},'completed_by_od':dict(sorted(byod.items())),'largest_observed_origin_completion_gap_seconds_including_censored_window_ends':gaps,'largest_observed_od_completion_gap_seconds_including_censored_window_ends':odgaps,'60_second_completion_bins':bins,'mean_transit_seconds':raw['mean_transit_seconds'],'p95_transit_seconds':raw['p95_transit_seconds'],'entry_supply_min':raw['entry_supply_min'],'inside_at_warmup':samples[w]['inside'],'inside_at_end':samples[end]['inside'],'measurement_planes':'Same relative port planes as controls; entry80, exit86body-margin rule. Large candidate geometry belongs inside these planes.'}

for source,target in [('long-trident.json','trident-long-details.json'),('../holdout-trident.json','trident-holdout-details.json')]:
 p=HERE/source;rows=[describe(summary) for summary in json.loads(p.read_text())] if p.exists() else []
 (HERE/target).write_text(json.dumps({'cases':rows,'interpretation':'Directional service balance and latency diagnostics, not fairness/deadlock proofs. Source/destination demand traces are paired by seed and bank. Selection and fresh longer-horizon confirmation groups must remain separate.'},indent=2))
 print(target,'detailed cases',len(rows))

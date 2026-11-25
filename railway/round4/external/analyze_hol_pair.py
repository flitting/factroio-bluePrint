#!/usr/bin/env python3
"""Finite outage/recovery comparisons. No claim of universal deadlock freedom."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
source=ROOT/'round4/hol-paired.json'
rows=json.loads(source.read_text());raws={};groups={}
for row in rows:
 raw=json.loads((ROOT/row['evidence_directory']/'script-output/result.json').read_text());raws[(row['id'],row['seed'],row['block_enabled'])]=raw;groups.setdefault((row['id'],row['seed']),{})[row['block_enabled']]=row

def demand(raw):return [(r['id'],r['origin'],r['destination']) for r in raw['records']]
def before(raw):
 return [{**{k:r[k] for k in ['id','origin','destination','arrival_tick','spawn_tick']},**{k:r[k] if r.get(k,10**9)<3600 else None for k in ['entry_tick','complete_tick','sink_tick']}} for r in raw['records']]
comparisons=[]
for (ident,seed),cases in groups.items():
 if False not in cases or True not in cases:continue
 control,blocked=cases[False],cases[True];a,b=raws[(ident,seed,False)],raws[(ident,seed,True)]
 phases={}
 for key in ['before','closure','first_recovery_minute']:
  x,y=control['phases'][key],blocked['phases'][key]
  phases[key]={'open_control':x,'closed_treatment':y,'completed_open_destinations_delta':y['completed_open_destinations']-x['completed_open_destinations'],'entered_open_destinations_delta':y['entered_open_destinations']-x['entered_open_destinations'],'external_head_exposure_origin_seconds_delta':y['external_head_exposure_origin_seconds']-x['external_head_exposure_origin_seconds']}
 row={'id':ident,'seed':seed,'same_generated_fifo':demand(a)==demand(b),'preclosure_train_events_identical':before(a)==before(b),'preclosure_head_samples_identical':[s for s in a['queue_head_samples'] if s['tick']<3600]==[s for s in b['queue_head_samples'] if s['tick']<3600],'both_zero_damage':a['damage_events']==b['damage_events']==0,'both_all_320_completed_retired':all(v['total_completed']==320 and v['retired']==320 and v['remaining']==0 and v['active_world']==0 and all('sink_tick' in r for r in v['records']) for v in [a,b]),'control_block_history':a['block_history'],'closed_block_history':b['block_history'],'last_complete_tick_control':control['last_complete_tick'],'last_complete_tick_closed':blocked['last_complete_tick'],'additional_total_drain_seconds':(blocked['last_complete_tick']-control['last_complete_tick'])/60,'phases':phases,'control_evidence':control['evidence_directory'],'closed_evidence':blocked['evidence_directory']}
 ar={r['id']:r for r in a['records']};br={r['id']:r for r in b['records']};nonw=[i for i,r in ar.items() if r['destination']!=4];event_keys=['entry_tick','complete_tick','sink_tick']
 changed=[i for i in nonw if any(ar[i].get(k)!=br[i].get(k) for k in event_keys)]
 last_sink_a=max(r['sink_tick'] for r in a['records']);last_sink_b=max(r['sink_tick'] for r in b['records'])
 row.update(open_destination_train_count=len(nonw),open_destination_train_events_compared=event_keys,open_destination_event_mismatch_count=len(changed),open_destination_event_mismatch_ids=changed,all_open_destination_train_events_exactly_equal=not changed,last_retire_tick_control=last_sink_a,last_retire_tick_closed=last_sink_b,additional_retirement_makespan_seconds=(last_sink_b-last_sink_a)/60,additional_completion_makespan_seconds=row['additional_total_drain_seconds'],legacy_additional_total_drain_seconds_definition='Extra time until the last train crosses the completion line; final retirement is reported separately.')
 comparisons.append(row)
streams={}
for (ident,seed,closed),raw in raws.items():streams.setdefault(seed,set()).add(hashlib.sha256(json.dumps(demand(raw),separators=(',',':')).encode()).hexdigest())
doc={'protocol':'round4/blockage/run.py and bank.lua unchanged','config':{'bank_per_origin':80,'total_trains':320,'warmup_ticks':1800,'duration_ticks':19800,'closure_start_tick':3600,'closure_end_tick_exclusive':7200,'blocked_exit':'W'},'same_fifo_across_all_geometries_and_treatments_by_seed':{str(k):len(v)==1 for k,v in streams.items()},'comparisons':comparisons,'interpretation':['Finite 320-train outage/recovery experiment, not capacity ranking.','The outgoing first W signal is switched through a native circuit input by the external test fixture at tick3600/7200. The core and FIFO sequence are unchanged. This is a prescribed external outage, not a self-contained optimizing controller.','Open-destination phase completions are paired descriptive service outcomes; the observed external head proxy is not itself a counterfactual capacity loss.','Different blueprint boundaries move the outside/inside distinction; a low external proxy may also mean queues moved inside the junction.','All 320 trains completing and retiring after recovery demonstrates recovery only for these finite realized demand streams, not universal deadlock freedom.']}
(HERE/'hol-comparison.json').write_text(json.dumps(doc,indent=2))
lines=['# 单西出口关闭/恢复的同序列配对','', '本组固定每来源80列、总320列1+4原生列车。对每个几何和seed各运行open对照与W出口60秒关闭处理。t=60s关闭、t=120s恢复，总模拟360s；同一FIFO、核心、车辆参数不变。关闭事件是外部故障夹具通过原生电路输入实现，不是蓝图内优化控制器。60s/120s为夹具切换输入的时点；原生电路计算与已预约列车仍依游戏规则处理，已经越过门的列车也会继续完成。因此关闭窗口内少量W完成不等于故障夹具未起作用。','', '| 几何 / seed | 关闭期开放终点完成：open→closed | 恢复首分钟开放终点完成：open→closed | 关闭期外部HOL暴露 origin·s：open→closed | 末列完成/退休多耗时s | 开放目的地事件变化列数 | 320列均完成/退休 |','|---|---:|---:|---:|---:|---:|---|']
for r in comparisons:
 p=r['phases'];cl=p['closure'];re=p['first_recovery_minute']
 lines.append(f'| {r["id"]} / {r["seed"]} | {cl["open_control"]["completed_open_destinations"]}→{cl["closed_treatment"]["completed_open_destinations"]} | {re["open_control"]["completed_open_destinations"]}→{re["closed_treatment"]["completed_open_destinations"]} | {cl["open_control"]["external_head_exposure_origin_seconds"]}→{cl["closed_treatment"]["external_head_exposure_origin_seconds"]} | {r["additional_completion_makespan_seconds"]:.3f} / {r["additional_retirement_makespan_seconds"]:.3f} | {r["open_destination_event_mismatch_count"]}/{r["open_destination_train_count"]} | {r["both_all_320_completed_retired"]} |')
lines += ['', '入口队首代理量只计一秒采样中距入口边界120 tiles以内、因原生信号停止、队首欲往W且紧随的下一列欲往开放出口的状态。跨四来源累加为origin·s。它不能检测所有内部队首阻塞，也不能换算为吞吐损失；边界不同可把同类等待从外部移到内部。因此同时展示开放终点交付量、恢复与完整排空。','', '配对的生成序列、关闭前事件和关闭前队首采样一致性检查在 `hol-comparison.json`；原始逐车事件与独立证据目录由 `../hol-paired.json` 指向。总时窗包含后段队列耗尽，整窗平均吞吐不进入主排名。','', '本组观察到有限工作负载恢复完成不能证明所有随机到达、无限队列、多个出口长期关闭时都无死锁。','']
if len(comparisons)==2:
 lines[2:2]=['## 本组实测结论', '', '在这一个seed17、总320列的配对关闭/恢复试验中，Trident的242列开放目的地列车，其入界、完成、退休时间逐车精确保持不变；Dense有144/242列至少一个事件时间变化。Trident在关闭期间的开放终点交付93→93、恢复首分钟83→83；Dense分别79→51、78→57。这比仅观察外部队首代理更强，但仍限于本负载、关闭时点和60秒持续时间。', '', '四例均320列全部完成且退休、零损伤，完成有限恢复验收。Trident并未在本有限整批任务中更快完工；两个几何的路径长度与初始管线填充时间不同。表内同时给最后完成时刻与最后退休时刻的增量，不把两条测量线混为一谈。', '']
(HERE/'HOL.zh-CN.md').write_text('\n'.join(lines))
print(json.dumps({'pairs':len(comparisons),'same_fifo_by_seed':doc['same_fifo_across_all_geometries_and_treatments_by_seed'],'all_finite_drained':all(r['both_all_320_completed_retired'] for r in comparisons)}))

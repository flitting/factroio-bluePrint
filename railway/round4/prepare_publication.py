#!/usr/bin/env python3
"""Stage reviewable Git tree batches without publishing or copying third-party BPs."""
from pathlib import Path
import hashlib,json,re,shutil

ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'round4';OUT=HERE/'publish'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    result=json.loads((HERE/'final/results-summary.json').read_text())
    assert result['publication_gate_complete']
    index=json.loads((HERE/'results-index.json').read_text())
    OUT.mkdir(exist_ok=True);staged=OUT/'files';staged.mkdir(exist_ok=True)
    records=[]
    def add(local,repo,binary=False,content=None):
        source=ROOT/local;target=staged/repo;target.parent.mkdir(parents=True,exist_ok=True)
        if content is None:shutil.copyfile(source,target)
        else:target.write_text(content)
        records.append({'path':repo,'source':local,'staged':str(target.relative_to(ROOT)),
            'bytes':target.stat().st_size,'sha256':digest(target),'binary':binary})
    report=(HERE/'final/REPORT.zh-CN.md').read_text().replace('figures/crossbar-embeddings.svg','figures/crossbar-embeddings.png')
    add('round4/final/REPORT.zh-CN.md','railway/round4/REPORT.zh-CN.md',content=report)
    for name in ['README.md','junctions-round4.txt','trident-research.txt','blueprint-manifest.json','book-validation.json']:
        add('round4/final/'+name,'railway/round4/'+name)
    review=json.loads((HERE/'final/final-review.json').read_text());assert review['overall_status']=='passed' and not review['required_fixes']
    add('round4/final/final-review.json','railway/round4/final-review.json')
    old_readme=(OUT/'github-readme-before.md').read_text()
    assert '## 第三轮' in old_readme and '## 第四轮' not in old_readme
    section=f'''## 第四轮：不同构型搜索与三分叉新结构

- [第四轮完整报告](round4/REPORT.zh-CN.md)
- [三分叉研究候选与紧凑对照蓝图册](round4/junctions-round4.txt)
- [三分叉单图](round4/trident-research.txt)
- [配对结果、原生CPU与恢复证据](round4/results-summary.json)
- [全部完成流量案例及协议分组](round4/completed-flow-catalog.json)
- [原创实验蓝图说明](blueprints/ROUND4-EXPERIMENTS.md)

136次完成流量案例、95种新实体配置、54种不同轨道几何（不是54个抽象拓扑家族）。独立较长三种子确认：涡轮对照102.42→三分叉117.50列/游戏分钟（+14.73%）；代价为46.44倍占地、约2.48倍原生寻路计时均值、更多延迟和部分方向服务下降。单W及全出口关闭恢复有完整原生证据；有限试验不证明稳定容量、全局最优或任意流量无死锁。生成/运行源码与原创实验蓝图已加入，完整逐车数据见本会话的railway-optimization-round4.zip。

'''
    new_readme=old_readme.replace('## 第三轮',section+'## 第三轮',1)
    add('round4/publish/github-readme-before.md','railway/README.md',content=new_readme)
    for name in ['paired-throughput.svg','area-cpu.svg']:
        add('round4/final/figures/'+name,'railway/round4/figures/'+name)
    add('round4/final/figures/trident-native-structure.png','railway/round4/figures/trident-native-structure.png',True)
    add('round4/directed/crossbar-embeddings.png','railway/round4/figures/crossbar-embeddings.png',True)

    # Compact public data retains all principal facts without embedding input BP strings.
    compact={k:v for k,v in result.items() if k not in ['selection_case_details','holdout_case_details','native_geometry','W_blockage','batching','capacity_diagnostics']}
    compact['case_diagnostics']=[{k:v for k,v in r.items() if k!='od'} for r in result['selection_case_details']+result['holdout_case_details']]
    compact['geometry']={k:{a:b for a,b in v.items() if a!='bounds'} for k,v in result['native_geometry'].items()}
    compact['W_blockage']=[{k:v for k,v in r.items() if k in ['id','seed','block_enabled','phases','total_requested','total_completed','retired','active_world','complete_drain_observed','damage_events','evidence_directory']} for r in result['W_blockage']]
    add('round4/final/results-summary.json','railway/round4/results-summary.json',content=json.dumps(compact,ensure_ascii=False,indent=2)+'\n')
    # Index every completed native flow case, keeping conditions rather than pooling them.
    groups={};cases=[]
    for r in index['cases']:
        key=json.dumps(r['comparable_group'],sort_keys=True,separators=(',',':'))
        if key not in groups:groups[key]='G'+str(len(groups)+1)
        cases.append({k:r.get(k) for k in ['id','seed','throughput','blueprint_sha256','all_od_completed_in_window','damage_events','source_saturated_in_window','evidence_directory']}|{'protocol_group':groups[key]})
    catalog={'definitions':index['definitions'],'protocol_groups':{v:json.loads(k) for k,v in groups.items()},'completed_cases':cases,
             'incomplete_or_failed_attempts':index['incomplete'],'note':'Construction/graph/clock/CPU gates are separate. Full raw cases are in the private research archive.'}
    add('round4/results-index.json','railway/round4/completed-flow-catalog.json',content=json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')

    # Original tested blueprints only. Community originals and their signal derivatives stay out.
    ids=sorted({r['id'] for r in index['cases'] if r['id'].startswith(('r4-dir-','r4-net-','r4-batch-')) and r['matches_current_input']})
    ids+=['r3-sig-turbine2-dense2','r2-sig-stacked-cloverleaf-all4-clean']
    for ident in ids:add('blueprints/'+ident+'.txt','railway/blueprints/'+ident+'.txt')
    add('round4/final/README.md','railway/blueprints/ROUND4-EXPERIMENTS.md',content='''# 第四轮实验蓝图

此目录的r4-dir/r4-net/r4-batch条目是从原生轨道元件生成、实际运行过的原创实验配置，包含退步和饥饿观察案例，不是全部推荐成品。请先阅读[完整报告](../round4/REPORT.zh-CN.md)和[协议分组的流量目录](../round4/completed-flow-catalog.json)。

优先查看[大型三分叉研究候选与两张紧凑对照的蓝图册](../round4/junctions-round4.txt)。三分叉提高总饱和排出吞吐，但占地、CPU、延迟和方向公平性存在明显代价。未明确许可的社区源图与派生信号图不在此公开目录复制；来源和获取脚本在round4/external下。
''')

    # All authored source, excluding generated scenarios with embedded third-party inputs.
    skip={'experiments','validation','profiles','temp','publish','final','sources','__pycache__','script-output'}
    for p in sorted(HERE.rglob('*')):
        rel=p.relative_to(ROOT)
        if p.is_file() and p.suffix in ['.py','.lua'] and not any(x in skip for x in p.relative_to(HERE).parts):
            assert not re.search(r'0eN[A-Za-z0-9+/=]{200,}',p.read_text()),'Embedded blueprint needs manual publication review: '+str(rel)
            add(str(rel),'railway/'+str(rel))
    for rel in ['scripts/run.py','scripts/demand.py','round2/protocol/run_protocol.py','round2/final/validate_books.lua','round3/signals/graph.lua']:
        add(rel,'railway/'+rel)
    metadata=['PLAN.zh-CN.md','EXECUTION-NOTES.zh-CN.md','holdout-plan.json','long-selection-plan.json',
        'protocol/changes.json','protocol/equivalence.json','cpu/changes.json','cpu/quiescence.json',
        'directed/NEXT-CUBE-EMBEDDING.md','directed/trident-native-proof.json','directed/trident-long-plan.json',
        'external/source-catalog.json','external/source-reproducibility-review.json','external/README.zh-CN.md','external/HOL.zh-CN.md','external/hol-comparison.json',
        'external/clean-repair.json','external/clean-equivalence.json',
        'networks/REPORT.zh-CN.md','networks/audit-result-index.md','batching/README.zh-CN.md',
        'batching/operational-validation.json','batching/clock-timing-validation.json','blockage-all/review.json']
    for rel in metadata:
        if (HERE/rel).exists():add('round4/'+rel,'railway/round4/'+rel)
    # Separate immutable text objects into modest calls; a single larger text stays whole.
    batches=[];current=[];size=0
    for r in records:
        if r['binary']:continue
        if current and size+r['bytes']>50000:batches.append(current);current=[];size=0
        current.append({'path':r['path'],'mode':'100644','type':'blob','content':(ROOT/r['staged']).read_text()});size+=r['bytes']
    if current:batches.append(current)
    for i,b in enumerate(batches):(OUT/f'tree-batch-{i:03d}.json').write_text(json.dumps({'tree_elements':b},ensure_ascii=False))
    manifest={'repository':'flitting/factroio-bluePrint','branch':'railway/repair-and-optimize-2026-11-25',
        'files':records,'text_batch_count':len(batches),'binary_files':[r for r in records if r['binary']],
        'original_tested_blueprint_ids':ids,'third_party_blueprint_contents_excluded':True,
        'publication_requires_fresh_head_read_and_expected_sha':True}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    old_pr=json.loads((OUT/'github-pr-before.json').read_text())
    body=f'''## 第四轮：跨构型原生搜索

原先的搜索集中在四张源图的局部变体。本轮从零生成新分合流网络，加入独立社区结构、信号组合和原生电路配时，并保持8个外部端口、1机车4空货厢和原生物理/寻路/信号行为。

- 完成136个原生流量案例，95种新实体配置、54种轨道几何；不把这些计数当作抽象拓扑家族或全部成功方案数。
- 新三分叉入口/出口与12条私有OD连接，在冻结新种子211/307/401、每入口240列、2分钟预热+4分钟计量下，102.4167→117.5列/游戏分钟，+14.73%，3/3提高。选择组单独保留，不跨窗口合并均值。
- 代价：808,934格²（对照46.44倍），2824灯；同负载串行原生trainPathFinder均值23.063→57.129微秒/tick（2.48倍，3次重复有波动）。方向服务和延迟完整披露，未宣称均衡稳定容量。
- 单W出口关闭60秒，三分叉242列开放终点请求的入口、完成、退场时刻逐车不变；两方案配对均320列完成退场。三分叉全出口同时关闭60秒后也320列完整排空，零损伤。这是有限恢复验证。
- 原生固定15秒/30秒相位控制均72.67，未控同几何109列/分钟，保留负结果。
- 蓝图册原生导入通过（3项、10033实体）；全部非标签字段与已测试输入一致。源图修复与前三轮结果保留。

详见[第四轮报告](railway/round4/REPORT.zh-CN.md)、[结果摘要](railway/round4/results-summary.json)、[可导入蓝图册](railway/round4/junctions-round4.txt)与[独立复核](railway/round4/final-review.json)。公共提交包含原创生成器、运行协议与原创实验蓝图；社区图公开来源和哈希，不复制未明确许可的原始/派生蓝图本体。

---

## 既有修复与前轮记录

'''+(old_pr.get('body') or '')
    (OUT/'pr-body.md').write_text(body)
    print(json.dumps({'files':len(records),'original_blueprints':len(ids)-2,'text_batches':len(batches),'binary_files':len(manifest['binary_files']),'total_bytes':sum(r['bytes'] for r in records)}))

if __name__=='__main__':main()

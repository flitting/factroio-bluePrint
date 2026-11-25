import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(p,default=None):
 q=HERE/p
 return json.loads(q.read_text()) if q.exists() else default
struct=[]
for f in ['structural-audit.json','packed-structural-audit.json','torder-structural-audit.json','trident-structural-audit.json']:
 struct+=load(f,{'cases':[]})['cases']
short=[]
for f in ['screen-source.json','screen-rest.json','screen-packed.json','screen-torder.json','screen-trident.json']:short+=load(f,[])
long=load('long-pair-seed17.json',[])+load('long-trident.json',[])
holdout=load('../holdout-trident.json',[])
recovery=load('../all-exits-drain.json',[])
sp={r['id']:r for r in short}
lines=['# 第4轮：从零合成的两层交叉开关网','',
'本目录先探索一种从零生成的空间嵌入：地面纵向输入/输出通道，通过独立横向连接完成12个非掉头OD。横向连接跨越中间纵轨时升到高架，邻接纵轨之间无需跨越其他纵轨时直接在地面转弯。没有复制原四张蓝图的实体布局。',
'', '**范围说明：17个二级分流／汇流配置改变空间嵌入、分流与汇流次序及储车长度；另外1个trident改变了首次分叉和最后汇入的原生邻接数。旧Dense T与本目录18个配置的42对不同入口且不同出口的原生最短OD路径，都没有共轨和共同闭塞区段。粗粒度的共同轨道存在性签名相同，不能由此断言完整连接图相同，也不能把零冲突视为本轮才实现的收益。**','',
'## 真正三向分流／汇流的补充原型','',
'`r4-dir-trident32-32` 在每个入口同一个native轨端同时分为左、直、右三路，并在每个出口一次汇合三路。三条叶子从分流后各自占用纵轨，然后连接各自的横向OD通道，合计24条叶子纵轨。`trident-native-proof.json` 直接读取native rail ends：旧Dense T四个首次分叉及四个最后汇入均为2邻居，而trident的8个节点全部为3邻居，且三条对应OD路径分别使用3个不同后继/前驱。它具有明确的局部分叉图差异，不能只依赖仍然相同的66对共轨presence签名判断。短窗筛选后已冻结蓝图和协议，进入三种子选择长窗与独立长时确认；仍未优化面积，也未证明全局最优。','',
'## 构造与搜索','',
'- 四方向各一进一出，合计8个外部端口；所有适配弯道与匝道均属于候选，占地计算没有把它们移到免费测试夹具。',
'- 基础模块是2.1版由4段曲轨组成的90°转弯（端点相对位移13×13格）、直线、16格坡道及原生支撑。坡道方向从低端指向高端，中心至两端各8格。',
'- 最初支撑间距32格的构造草稿残留624个高架直轨ghost，未计作成功候选；改为16格并通过正常ghost复活后才导出可用蓝图。没有强制创建轨道绕过建造规则。',
'- 首组采用64格列距、12个独立横向行，改变全局行序和行间距。后组对列排列进行搜索，并允许互不重叠的横向连接放在同一行。',
'- `search_columns.py` 枚举40320个8列排列，其中10080满足N/S外部右行端口顺序；按“行数、横向总列跨度、最长列跨度”排序，得到32个并列结果，最优模型值为(6,28,4)。这只是该布局模型的几何代理目标，不是原生吞吐优化；40320或32均不是已建造蓝图数量。',
'- 从其中4个列排列分别取正向/反向行序，共8个打包构型；32格列距、16格行距。正常建造、12OD原生路径请求和信号工作状态全部单独检查。',
'- `branch_orders.py` 从原生有序轨道路径提取4个入口先分出的目的地及4个出口最后汇入的来源，并按90°旋转归一化。该描述比“是否共轨”更细，但仍不是全图同构证明。',
'', '## 原生结构与短窗筛选','',
'Factorio Headless 2.1.25；1机头4货车、空载、核燃料、制动1–7。短窗使用bank80、seed17、warmup1800、duration3600；完成量是有限排队清空吞吐，不是最大稳定服务率。大图填充时间可能使30秒warmup不足，长窗单列报告。',
'', '| ID | 原生实体 | 工作信号 | AABB面积 | 独立OD共block对数 | 短窗列/分 |', '|---|---:|---:|---:|---:|---:|']
for r in struct:
 a=sp.get(r['id']);lines.append(f"| {r['id']} | {r['entities']} | {r['signals']} | {r['area']:.2f} | {r['independent_od_pairs_share_blocks']}/42 | {a['throughput'] if a else '未完成'} |")
lines+=['','所有列出的结构审计均要求12/12 OD found且全部信号working。流量筛选仍需独立满足12OD在测窗完成、damage_events=0、四入口外部bank未耗尽。','', '## 正式长窗','',
'固定bank150、warmup3600、duration10800。二级交叉开关的2个长窗使用seed17；trident冻结后使用既定选择种子17/31/47，并由主实验保留未见种子确认。与旧Dense T同bank/seed进行配对；不同bank会改变后续入口的随机OD序列，不直接把短窗与长窗差值解释为单一warmup效果。','',
'| ID | Seed | 列/分 | 12 OD完成 | 损伤 | 外部bank耗尽tick |','|---|---:|---:|---|---:|---|']
for r in long:lines.append(f"| {r['id']} | {r['seed']} | {r['throughput']:.6f} | {r['all_od_completed_in_window']} | {r['damage_events']} | {r['ticks_without_external_bank_by_origin']} |")
lines+=['','旧Dense T在同seed17长窗是105.333333列/分。当前H16-source的105.666667仅意味着3游戏分钟多完成1列，不能据此声称取得可靠改进，其面积也更大。trident在17/31/47三个选择种子的均值为119.111111列/分，同组旧Dense T为101.666667列/分，配对均差17.444444列/分（+17.1585%）。这些种子属于选择阶段，独立确认另列。','']
if holdout:
 lines+=['## 独立长时确认','',
 '本组由 `../holdout-plan.json` 预先冻结：bank240、warmup7200、duration14400、seeds211/307/401。每个入口有240列预置列车，先预热2游戏分钟，再测量4游戏分钟。蓝图和容量协议hash与选择阶段冻结版本相符；不与bank150组混合平均。这里只列主实验已合并的完成记录；与旧Dense T的逐seed配对比较由主报告汇总。','',
 '| Seed | 列/分 | 12 OD完成 | 损伤 | 外部bank耗尽tick |','|---|---:|---|---:|---|']
 for r in holdout:lines.append(f"| {r['seed']} | {r['throughput']:.6f} | {r['all_od_completed_in_window']} | {r['damage_events']} | {r['ticks_without_external_bank_by_origin']} |")
 lines+=['']
if recovery:
 lines+=['## 四出口同时封闭后的恢复','',
 '独立边界条件测试通过原生电路控制四个第一出口信号，在tick3600同时关闭，在tick7200恢复，即持续60游戏秒。记录原生信号状态；不强制修改列车速度、位置或轨道预约。有限bank80每入口，共320列，请求序列为seed17。','',
 '| Seed | 完成／请求 | 残留请求 | 世界内活动列车 | 损伤 | 四出口中点电路红灯 | 完全清空 |','|---|---:|---:|---:|---:|---|---|']
 for r in recovery:lines.append(f"| {r['seed']} | {r['total_completed']}/{r['total_requested']} | {r['remaining']} | {r['active_world']} | {r['damage_events']} | {r['all_four_midpoint_circuit_reserved']} | {r['complete_drain_observed']} |")
 lines+=['','原生状态样本保留了切换过渡：tick3602仍有已经预约的橙灯；tick3720、5400与7199的四信号全部为电路关闭态，tick7202全部为开放态。它没有用脚本强制撤销列车预约。']
 for r in recovery:lines.append(f"seed{r['seed']}最后一列在tick{r['last_complete_tick']}完成，即重新开放后{(r['last_complete_tick']-7200)/60:.1f}游戏秒；全部{r['retired']}列在测试结束前退出测试世界。")
 lines+=['','这是特定有限队列与60秒全部出口关闭的恢复证据，不是任意到达过程或任意永久阻塞下的死锁自由证明。','']
lines+=[
'## 解释与局限','',
'- trident原生首次分叉／最后汇入在同一轨端有3个邻接轨道，是已验证结构事实；吞吐成绩属于整个空间布局、储车长度、分流／汇流和信号组合。没有完成消融实验，不能把差异全部归因于这一邻接数变化。',
'- 这里的3是同一轨端的后继（分流）／前驱（汇流）数，不是把外部主干也算入后的岔口总度数。trident取消了二级分流之间由两个目的地共用的中间段，但其边界入口至首次分叉的共用路径更长：N/E/S/W分别含112/313/112/346个原生轨实体，旧Dense T为2/1/2/3。这是轨实体步数而非精确长度；不能把这一方案概括为相对旧图已减少总共享距离或已经更早分流。',
'- `block-order.json` 检查所选12条原生空图路径的闭塞转换联合图。本目录18个配置均为DAG；这一点仅支持这些静态路线的无环资源顺序，不是所有动态替代路径、到达过程或出口阻塞情景的死锁证明。',
'- 无独立端口OD共block没有排除同入口FIFO的队首阻塞或同出口3→1汇流的竞争；也不自动保证最大吞吐。',
'- 不把18个参数/几何构型称为18个抽象家族：17个为二级分流/汇流交叉开关嵌入，1个为真正三向trident原型。二级分流的17图包含8种旋转归一化次序，其中7种不同于旧T，另外2图刻意复现旧T次序作为控制。',
'- 占地使用与此前相同的全部核心实体外接矩形，不能用稀疏网格的空白部分替本方案免计面积。',
'- `static_path_steps_sum`仅是静态路径搜索工作量描述；本目录没有进行正式CPU计时，不能把并发运行的墙钟时间当成UPS或寻路CPU成本。',
'- 正常建造、空图可达、有限并发测试都不能证明所有到达流和永久出口阻塞下的死锁自由。','',
'## 下一步消融（未执行，不计作本轮候选）','',
'冻结当前trident。可把单侧扇出支路沿入口主干延后16格，让三个同点后继变为两个相距16格的二级分叉；出口反向实施。保留同一24条叶子纵轨、12条横向OD连接、外部端口和面积，以3/3、2/3、3/2、2/2四组比较入口提前分流与出口单次汇流的贡献。仍需重新做正常建造和原生连接gate，并检查轨道路径长度与信号变化。此次不继续扩充该组，计算资源转向三种子正式长窗、未见种子确认、阻塞恢复和串行CPU。','',
'另一个尚未构造的方向见 `NEXT-CUBE-EMBEDDING.md`：trident的12条私有OD连接抽象上是去除同源同宿配对的K4,4，与立方体图同构。可研究两层四边形与四条连接边的紧凑核心，再处理固定方位的外部端口。这个数学表示尚未完成原生蓝图和流量测试，不计作本轮成功候选。','',
'## 主要证据与复现','',
'- `generation-manifest.json`、`packed-manifest.json`、`torder-manifest.json`：生成配置与确切行/列顺序。',
'- `build-*.json` 与其evidence_directory：正常原生建造、剩余ghost、轨段缺口、方向冲突及工作信号。',
'- `structural-audit.json`、`packed-structural-audit.json`、`torder-structural-audit.json`：原生12OD、面积及闭塞共享。',
'- `branch-orders.json`：原生分流/汇流次序描述。',
'- `screen-*.json`、`long-pair-seed17.json`、`long-trident.json`：直接引用各native运行的request、日志与逐列车结果。',
'- `trident-long-plan.json`冻结蓝图和协议hash；`trident-long-details.json`记录按来源/出口/OD的完成量、平均/P95通过时间和内部在制列车数。','',
'```bash', 'python3 round4/directed/search_columns.py', 'python3 round4/directed/generate.py', 'python3 round4/directed/generate_packed.py', 'python3 round4/directed/generate_torder.py',
'python3 round4/directed/build.py r4-dir-pack0-fwd',
'python3 round4/protocol/analyze_graph.py --ids r4-dir-pack0-fwd --output round4/directed/check-pack0.json',
'python3 round4/protocol/run_bank.py --ids r4-dir-pack0-fwd --seeds 17 --bank 150 --warmup 3600 --duration 10800 --output round4/directed/check-long.json', '```','']
(HERE/'REPORT.zh-CN.md').write_text('\n'.join(lines))
summary={'structurally_valid_configurations':len(struct),'short_completed':len(short),'long_completed':len(long),'holdout_completed':len(holdout),'all_exit_recovery_completed':len(recovery),'short_cases':short,'long_cases':long,'holdout_cases':holdout,'all_exit_recovery_cases':recovery,'scope':'17 binary crossbar configurations (8 split/merge order invariants, including reference-T order controls) and one true ternary trident prototype; no global optimum claim.'}
(HERE/'results-summary.json').write_text(json.dumps(summary,indent=2))
print('structural',len(struct),'short',len(short),'long',len(long))

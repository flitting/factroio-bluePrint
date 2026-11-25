# 第四轮：外部新几何来源与原生验证

本工作线从独立公开设计中取得 14 个几何输入，扩大此前以用户四张原蓝图为中心的搜索覆盖。它们是 **14 个几何候选，不等于 14 个互异抽象拓扑家族**。原信号配置保持不变；仅删除电杆、灯和装饰铜线，并在必要处补齐四向地面端口。所有适配部分计入候选面积。3 Chunk Square 原灯基线另发现一盏未接轨信号，原灯97的短筛只作为缺陷样本；修复和密化配置单独标识。

## 固定测试条件

Factorio Headless 2.1.25，base/quality/elevated-rails/space-age；四向各一进一出、右行；每车 1 机头 + 4 空货车厢，普通品质、核燃料、制动 1—7。短筛使用相同 S1、seed 17、每入口预放 80 列车、热身 1800 ticks、计数 3600 ticks。每项必须普通蓝图建造成功、信号工作、12 次独立原生自动驾驶完成，并在并发测试中检查 12 OD 与损伤。吞吐是饱和队列在这一分钟窗口内的通过量，不能称为最大稳定容量。

`validation-summary.json` 与 `extra-validation-summary.json` 含建造/独立驾驶证据目录；`screen.json` 和 `extra-screen.json` 含完整短筛路径。正式长窗及 CPU 比较由总流程统一完成。

## 几何候选与初筛

| 候选 | 信号数 | 投影包围盒面积 tiles² | 12独立OD / 全部工作信号 | 异源异终点共轨/共block 对数 | 短筛 trains/min |
|---|---:|---:|---:|---:|---:|
| r4-ext-partially-unrolled-cloverleaf | 97 | 15881.21 | 12/12 / True | 0 / 0 | 100.0 |
| r4-ext-three-chunk-square | 97 | 12538.75 | 12/12 / False | 0 / 0 | 97.0 |
| r4-ext-crossover-displaced-left-turn | 72 | 15892.34 | 12/12 / True | 0 / 0 | 94.0 |
| r4-ext-twister | 86 | 15870.09 | 12/12 / True | 0 / 0 | 90.0 |
| r4-ext-paperclip | 82 | 15870.09 | 12/12 / True | 0 / 0 | 90.0 |
| r4-ext-buffered-celtic-knot | 76 | 15870.09 | 12/12 / True | 0 / 0 | 81.0 |
| r4-ext-pinwheel | 92 | 15870.09 | 12/12 / True | 0 / 0 | 80.0 |
| r4-ext-celtic-knot | 60 | 15870.09 | 12/12 / True | 0 / 0 | 75.0 |
| r4-ext-windmill | 98 | 17885.72 | 12/12 / True | 0 / 0 | 75.0 |
| r4-ext-cube | 24 | 12094.84 | 12/12 / True | 0 / 0 | 59.0 |
| r4-ext-level-switch-two | 30 | 8682.55 | 12/12 / True | 4 / 8 | 51.0 |
| r4-ext-ground-cross | 32 | 1762.03 | 12/12 / True | 8 / 16 | 49.0 |
| r4-ext-level-switch-one | 31 | 15366.19 | 12/12 / True | 0 / 9 | 46.0 |
| r4-ext-hyper-cross | 32 | 1762.03 | 12/12 / True | 4 / 16 | 43.0 |

异源异终点共有 42 对 OD。本次分析取空地图中每个 OD 的一条原生选定路径，只比较蓝图核心内部；它是结构诊断，不覆盖所有重寻路状态，也不是死锁证明。前 8 张社区立交以及 Cube、3 Chunk Square 在这些选定路径中不共享异源异终点轨道或 block，但它们的分流次序、汇流次序、路径长度、信号位置、有效缓冲长度不同。Ground/hyper cross 与两个 level-switch 则保留平面冲突。

`route-structure.json` 记录全部 66 对路径的共轨/共block、各入口首先分出的 OD 和各出口最后并入的 OD。Celtic Knot 与 Pinwheel 的首分/末汇顺序相同，仍是不同空间几何；3 Chunk Square 的两个出口包含无法归为严格二叉顺序的并接。这些差别不靠蓝图名称推断。

## 原图与适配

- Bocian / Opinionated-Blueprints：Celtic Knot、Buffered Celtic Knot、Twister、Windmill、Pinwheel、Partially Unrolled Cloverleaf、Paperclip、Crossover Displaced Left Turn，以及 ground/hyper cross、两种 level-switch。来源仓库 https://github.com/Opinionated-Blueprints/10-Books-Full-of-Rails，固定 Git tree `d14db4ae7b7f57e3045de9b0b91d70b76ba84380`。
- DaveMcW：Cube RHD，作者发布页 https://forums.factorio.com/viewtopic.php?p=621337。
- mmmPI：3 Chunk Square，作者设计及原始字符串见 https://forums.factorio.com/viewtopic.php?p=626041。
- 外部作者原始描述中的 2-4、1-2 等测试分数不参与本研究的 1+4 排名。

Windmill 原 EW 地面终点直接落在坡道低端，补四个 8-tile 地面短接后，八个端口均能由统一脚本识别。Cube 补齐四端不同长度的末段。3 Chunk Square 原文件在独立裸建造时分为 182、48、48 三个分量；它的边缘分岔伸到蓝图外，给八端各补 8 tiles 后完全连接，随后 12 OD 均完成。两个 level-switch 的外端原为高架；通过 16-tile 高架短桥、坡道和 8-tile 地面短接落地，普通建造与信号验证通过。

3 Chunk Square 还有一盏原信号在 `(44.5,4.5), dir 11` 被61tick原生graph诊断为 `not_connected_to_rail`；`clean-repair.json` 记录只删除该信号的修复配置，三档密化配置也在native gate中清除该灯，不能把含坏灯的原始配置当作全灯工作通过。3 Chunk Square 的原始裸图，以及两个 level-switch 首稿直接接坡道时有四个坡道未生成 ghost 的草案，均保存在 `drafts/`，失败原生证据为 `validation/audit-1e384e5bfe2b39e7/`。这些草案不是成功候选；随后适配后的有效输入使用独立 hash 与验证证据。

## 来源重取与发布边界

`source-catalog.json` 列出每份输入的作者、原始 URL、固定 revision、SHA-256；`fetch_sources.py` 只从这些公开来源重取并核对 hash，不嵌入完整外部蓝图。`import_candidates.py` 与 `import_extra.py` 可从保留原文件重建测试输入。FaTul 的 `shift_x/y` 已按上游定义恢复，再进行保持铁路网格奇偶性的平移居中；信号方向与 rail_layer 全保留。

未在这些外部源中找到明确的再分发许可。私有测试保留原输入；公开研究提交只放来源、hash、重取/转换脚本及实验结果，不复制完整外部蓝图。本地原始源与候选副本不冒充用户原创，也不冒充本轮新生成拓扑。

## Cube / 3 Chunk Square 信号探索

使用总流程 `round4/signals/generate.py` 的原生可放置信号候选，在欧氏距离阈值 2、4、8 三档中添加普通信号；原轨道、坡道、支撑和已有工作信号保持一致。阈值不是沿轨 block 长度。候选需通过普通建造、全部工作信号、12 静态原生可达，随后并发短筛。此处每档计一个信号配置，不计新拓扑。

| 配置 | 短筛 trains/min | 窗口12OD | 损伤事件 |
|---|---:|---:|---:|
| r4-sig-cube-d2 | 92.0 | True | 0 |
| r4-sig-cube-d4 | 82.0 | True | 0 |
| r4-sig-cube-d8 | 79.0 | True | 0 |
| r4-sig-three-chunk-square-d2 | 97.0 | True | 0 |
| r4-sig-three-chunk-square-d4 | 99.0 | True | 0 |
| r4-sig-three-chunk-square-d8 | 96.0 | True | 0 |

## 3 Chunk Square 清洁基线补测

`r4-ext-three-chunk-square-clean` 仅移除原有唯一未接轨信号。全部工作信号、12 个原生静态 OD 路径均通过；短筛 97.0 trains/min、零损伤、12 OD 窗口完成。相对于原灯缺陷样本，320 条车记录精确相等：True；每600tick samples 精确相等：True。这确认删除该闲置信号未改变本组流量轨迹；仍不是对任何流量状态的形式证明。

## 纯流量与设施跟车参照

以下五项属于诊断，不进入混合流主排名。固定 Dense364 几何、bank150、热身3600ticks、计数3600ticks、seed17；前三项进出线 spacing8，后两项仅联合改变进出线信号间距。每组只有4个预期OD，各输出只有一个来源，不要求12OD均出现。原生空图路径诊断确认每组内部6对路径均无共核心轨或共block（`capacity-graph-reference.json`）。

| 诊断 | 总列/分钟 | N/E/S/W各列/分钟 | 外部队列空ticks | 损伤 |
|---|---:|---|---|---:|
| D0-straight | 140 | 36.0, 34.0, 36.0, 34.0 | [0, 0, 0, 0] | 0 |
| D0-near | 144 | 36.0, 36.0, 36.0, 36.0 | [0, 0, 0, 0] | 0 |
| D0-far | 129 | 32.0, 33.0, 32.0, 32.0 | [0, 0, 0, 0] | 0 |
| D0-straight-spacing4 | 138 | 37, 32, 37, 32 | [0, 0, 0, 0] | 0 |
| D0-straight-spacing2 | 136 | 37, 31, 37, 31 | [0, 0, 0, 0] | 0 |

这些排放量只描述现有参考几何与共同设施在指定纯流状态下的跟车水平，不是全局严格上界，也不是最大稳定到达率。spacing4/2 同时改变输入与输出线，因此不能单独归因于哪一端；首个出口信号 clearance 始终8 tiles。不得把这些新设施数值直接用于战胜旧协议混合流分数。

### 站点构建修补说明

spacing4 首次尝试在出口 offset2300 的车站位置与自动生成信号碰撞，原生普通放置检查拒绝建站，该失败未计入吞吐结果。后续 spacing4/2 仅使用 `spacing-protocol/bank.lua` 的私有副本，跳过距2300站点小于4 tiles的出口信号；该位置远在406 tiles整列退休线之外。spacing8 的原信号位于2296/2304，恰好4 tiles，因此原标准设施没有任何信号被移除。主协议未修改。

最终 straight spacing8/4/2 为140/138/136 trains/min。这一固定负载没有显示通过共同进出线密化可提高吞吐；不等于全局容量上界。

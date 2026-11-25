# 铁路蓝图修复与优化

Factorio 2.1.25 Headless 原生验证；每方向一入一出，1 个火车头加 4 节货车。

## 第三轮：拓扑、信号组合与队首阻塞

- [第三轮完整报告](round3/REPORT.zh-CN.md)
- [第三轮候选与基准蓝图册](round3/junctions-round3.txt)
- [364 灯密集版单图](round3/turbine-dense-364.txt)
- [第三轮关键结果](round3/results-summary.json)

同一 bank150 协议、六个配对种子：涡轮 234 灯基准 97.0，364 灯密集版 100.5 列/游戏分钟（+3.61%），同占地。本批原生寻路计时均值增加约 9.4%，存在重复波动。共测试 39 个新合法配置；新增拓扑未取得经较长窗口复核的优势，实际六车等待环及信号修复均有证据。完整源码与逐车数据见本会话的 `railway-optimization-round3.zip`。

## 前两轮：原图修复与信号优化

- [修复后的原 11 项蓝图册](../十字路口)
- [最终优化蓝图册](blueprints/optimized-junctions.txt)：原叠层对照 + 叠层清理优化版 + 涡轮 2 清理优化版
- [叠层优化单图](blueprints/stacked-signals-optimized.txt)
- [涡轮 2 优化单图](blueprints/turbine2-signals-optimized.txt)
- [完整中文报告](REPORT.zh-CN.md)
- [关键结果与版本说明](validation/round2-summary.json)
- [原图修复差异与证据](validation/repair/)

三种子长窗有限饱和放行率：原叠层 74.11、叠层信号优化 93.78、涡轮信号优化 99.22 列/游戏分钟。长窗在原 all4 版本测得；发布清理版另通过原生图、完整区块及 1,124 对逐车记录精确等价复验，所有发布信号均工作正常。CPU 对发布清理版重新计时。

完整复现代码、逐车原始记录、原生计时 CSV 和研究候选已打包为本会话的 `railway-optimization-round2.zip` 交付。此 GitHub 核心提交不含游戏引擎或大体积原始数据。


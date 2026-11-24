# 铁路蓝图修复与优化

Factorio 2.1.25 Headless 原生验证；每方向一入一出，1 个火车头加 4 节货车。

- [修复后的原 11 项蓝图册](../十字路口)
- [最终优化蓝图册](blueprints/optimized-junctions.txt)：原叠层对照 + 叠层清理优化版 + 涡轮 2 清理优化版
- [叠层优化单图](blueprints/stacked-signals-optimized.txt)
- [涡轮 2 优化单图](blueprints/turbine2-signals-optimized.txt)
- [完整中文报告](REPORT.zh-CN.md)
- [关键结果与版本说明](validation/round2-summary.json)
- [原图修复差异与证据](validation/repair/)

三种子长窗有限饱和放行率：原叠层 74.11、叠层信号优化 93.78、涡轮信号优化 99.22 列/游戏分钟。长窗在原 all4 版本测得；发布清理版另通过原生图、完整区块及 1,124 对逐车记录精确等价复验，所有发布信号均工作正常。CPU 对发布清理版重新计时。

完整复现代码、逐车原始记录、原生计时 CSV 和研究候选已打包为本会话的 `railway-optimization-round2.zip` 交付。此 GitHub 核心提交不含游戏引擎或大体积原始数据。

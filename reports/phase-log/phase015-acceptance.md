# phase015 DoD 检查清单（R015-T50/T51）

- Spec：`015-分析报告主线与生成优化.md`
- 数据窗口：最近 12 个月，48 个 T1 社区
- 生成物参考：`reports/t1-auto.md`、`reports/local-acceptance/t1-stats-snapshot.json`、`reports/local-acceptance/t1-pain-clusters.json`

## DoD 条目与状态

- [x] 主线清晰：`docs/2025-11-主业务线说明书.md` 描述 `/api/analyze → report` 主链路，标注数据准备白名单。
- [x] T1 报告可重复：`make t1-report-auto` 在现有 DB 上可生成对齐标靶的 Markdown（`reports/t1-auto.md`）。
- [x] 三层大脑可验证：Stats / Clustering / Report Agent 各有输入输出定义与脚本，JSON 快照可复现。
- [x] 不破坏现有主线：market 模式为显式开关，异常回退技术版报告（默认行为不变）。
- [ ] 文档与配置引用更新完备：Spec 008/010/013 的报告章节尚未指向新主线；配置说明待补充（计划下一轮完成）。

## 阶段总结

- Phase0~3 完成；Phase4 已接入 ReportService，待补充跨 Spec 文档与配置说明。
- 数据基线稳定（盘点见 `reports/phase-log/phase015-data-audit.md`）。
- 需要后续补：跨 Spec 配置/文档同步、market 模式端到端回归。

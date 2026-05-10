# phase015 数据盘点（R015-T10/T11）

- 数据来源：当前连接的业务库（直连验证，非空库）。
- 时间窗口：最近 12 个月。
- 生成方式：`make t1-data-audit` → `reports/local-acceptance/t1-data-audit.json`。

## 结果摘要

- T1 社区数：48
- 帖子数（12 个月）：36,759
- 评论数（12 个月）：480,294
- 语义标签：pain 39,117 / solution 33,167 / total 434,996
- 实体：content_entities total 293

## 结论

- 数据充足，无需回填。
- 审计脚本与 Stats Layer 已修复社区前缀处理，避免漏算（使用 `removeprefix("r/")`）。

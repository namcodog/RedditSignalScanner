# phase1125 - Brand Intelligence R15.1.5 archive 品牌池预审

- 这轮目的：按用户校正口径处理 archive 品牌；这些不是系统弱候选，而是历史手工核实资源。
- 当前状态变化：已生成 `archive-brand-pool-preaudit-2026-05-12`、Agent 初审包和严格审计包；严格审计为 `P0=1461 / P1=58 / P2=81 / P3=44`，全部 `db_writes=false`。
- 还没完成：需要用户优先细审 P1/P2，再看 CSV 全表后，才能进入品牌池写入设计。
- 下一步：用户确认后进入 R15.2 Dev DB `brand_registry / brand_mentions`，写入必须显式、幂等、可回滚。

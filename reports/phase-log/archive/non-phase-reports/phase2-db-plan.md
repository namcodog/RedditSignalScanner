# Phase2 趋势预聚合与降级标注（设计稿，未执行DB变更）

## 目标
- 长窗趋势查询命中预聚合，避免超时；提供稳态热度/velocity 支撑任意主题/选品/运营问题。
- 长窗降级透明：time_window_used、trend_source、trend_degraded 标记可透出。

## 方案要点
1) 窗口/字段
- 月度窗口：12/24 个月；运行常用 days: 30/90/180/365。
- 字段：posts_count、comments_count、score_sum，派生 velocity_L30/L90（生成侧计算或 MV MoM）。

2) DDL 草案
- `docs/db-design/trend_mv.sql` 更新：`mv_monthly_trend(month_start, posts_cnt, comments_cnt, score_sum, *_velocity_mom)`；索引 month_start；刷新示例 `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_trend;`。
- 未执行数据库变更。

3) 刷新/运维（待落地）
- 计划新增脚本/定时任务：refresh_mv_monthly_trend，失败报警；定义过期阈值（例：48h 未刷新即视为过期）。
- 长窗降级策略：days>90 优先查 MV；MV 不存在/过期则回退 runtime，标记 `time_window_used` 与 `trend_degraded`。

4) 生成脚本改造（设计）
- 引入 trend 加载函数：优先命中 MV；否则 runtime；计算 velocity；写入 facts `trend_source (mv_monthly_trend|runtime)`、`time_window_used`、`trend_degraded`；quality/flags 若降级则追加 `trend_degraded`。
- 不在本阶段改代码，等待评审后实装。

5) 验证计划（待执行）
- 性能：365d 查询命中 MV 不超时；记录耗时。
- 数据一致性：90d runtime vs MV 对比，允许刷新延迟内微偏差。
- 样本：至少两主题（选品向/运营向）生成 facts，检查 trend 字段与降级标记。

## 声明
- 本阶段未执行任何数据库变更或刷新，仅编写/更新设计文档。

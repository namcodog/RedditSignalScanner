# Phase 43 - SOP_v3 补齐 System A/B 与 run_id（父/子）现状口径

## 目标
- 把 “System A / System B 分工” 和 “run_id（父/子）怎么落地、怎么查” 写进 `docs/sop/数据抓取系统SOP_v3.md`。
- 保持 SOP 原有结构不变，但让文档能跟现在的代码 + 真实库一致，避免口径漂移。

## 发现了什么问题/根因？
- 团队口径里已经在用 System A/B，但 SOP_v3 只讲了 Cache-First + Celery（偏 A），没把 **A/B 适用场景**说清楚。
- run_id 体系已经升级成：
  - `crawl_run_id`（父级：整轮抓取）
  - `community_run_id`（子级：单社区）
  - 并且已落库（主表字段 + 追踪表）
 但 SOP_v3 仍停留在“posts_raw.metadata 有 run_id / comments 没有追踪列”的旧描述。

## 是否已精确定位？
- 是，问题集中在 `docs/sop/数据抓取系统SOP_v3.md` 的：
  - Step 0/1 对 System A/B 与 run_id 的描述缺失/过期
  - Step 6 Runbook 缺少按新字段/新追踪表的查询方式

## 精确修复方法？
- 只改文档，不改结构：
  - 在 Step 0 增加 “两条轨道（System A / System B）” 表格
  - 在 Step 1/3 更新 run_id 的现状落地口径（主表字段 + 追踪表 + metadata 兼容）
  - 在 Step 6 增加：
    - System B（离线回填）命令示例（抓 JSONL → ingest 入库）
    - 推荐的校验 SQL（按 `crawl_run_id` 字段、以及 `crawler_runs/crawler_run_targets`）

## 下一步
- 如果你希望 System B 也带 run_id（便于审计/回滚），可以在 `ingest_jsonl.py`/回填脚本里补上 `crawl_run_id/community_run_id` 传递与写入（升级项）。

## 变更文件
- `docs/sop/数据抓取系统SOP_v3.md`


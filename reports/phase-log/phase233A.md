# Phase 233A — run_analysis() 分支注释深度审计（2026-03-05）

## 背景
Phase 233 完成了业务逻辑地图 v1.0。Phase 233A 深入审计 `run_analysis()` 这个 1738 行的巨型函数，提取完整决策树并注入标准化注释。

## Serena 精细化研究

| 函数 | 文件 | 行号 | 关键发现 |
|------|------|------|---------|
| `_run_sample_guard` | analysis_engine.py | L1168-1190 | 防御性包装,异常→None→继续 |
| `_filter_communities_by_mode` | analysis_engine.py | L2951-2975 | ops/market 互斥,YAML 驱动 |
| `_extract_business_signals_from_labels` | analysis_engine.py | L663-832 | 170行批量查询,无N+1 |
| `_render_structured_report_with_llm` | analysis_engine.py | L3364-3387 | ✅ 已有 C/X tier guard |
| `quality_check_facts_v2` | facts_v2/quality.py | L67-261 | 4阶段检查:话题/完整度/一致性/覆盖 |
| `_determine_report_tier` | facts_v2/quality.py | L264-291 | 27行硬规则,5条if决定tier |
| `_schedule_auto_backfill_*` | analysis_engine.py | L1386-1682 | 296行,8个嵌套函数,Redis三层限流 |

## Serena 修正

| # | 原始判断 | Serena body read 后修正 |
|---|---------|----------------------|
| 🔴 | "LLM 在 C/X 时浪费调用" | ❌ 错误 — L3371 已有 `return None` 保护 |
| 🟡 | quality gate "模糊分级" | 补充精确规则: topic_mismatch→X, pains≥min→A |
| 🟡 | mode filter "粗粒度" | 补充互斥逻辑: ops 从 YAML 加载 |

## Codex 执行

- **模型**: gpt-5.3-codex Medium
- **Token**: 49,387
- **退出码**: 0
- **修改**: 12 条注释 (10 🔀 分支 + 2 ⚙️ 参数)

## 验证

| 检查项 | 结果 |
|--------|------|
| AST 语法 | ✅ |
| `grep -c '🔀 分支'` | 10 ✅ |
| `grep -c '⚙️ 参数'` | 2 ✅ |
| 行为回归 | 零影响 (纯注释) |

## Commit
```
dea89d2 — docs(Phase 2A): run_analysis() 分支注释注入 — 12 条 Serena 校正注解
  4 files changed, 141 insertions(+), 6 deletions(-)
```

## 发现的真实盲点 (后续跟进)
`_schedule_auto_backfill_for_insufficient_samples` (296行) 的 Redis budget env vars 缺文档:
- `REMEDIATION_BUDGET_PER_TASK`
- `REMEDIATION_BUDGET_USER_HOURLY`
- `REMEDIATION_BUDGET_USER_DAILY`

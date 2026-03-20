# 确定性协议 (Determinism Protocol)

> Phase 240 固化 — 2026-03-12

## 什么是确定性模式？

传入 `--anchor-ts` 参数后，报告生成脚本进入“确定性模式”。
同一参数跑 N 次，输出的 `facts_v2_*.json` 文件 SHA-1 哈希完全一致。

## 验证命令

```bash
FIXED_TS="2026-03-12T03:00:00+00:00"
PYTHONPATH=backend python backend/scripts/report/generate_t1_market_report.py \
  --topic "robot vacuum cleaner" --mode market_insight --skip-llm --days 365 \
  --anchor-ts "$FIXED_TS"
```

## 协议规则

| 规则 | 说明 |
|------|------|
| 禁止 NOW() | 所有 SQL 时间查询必须用 anchor_ts 参数 |
| LLM 守卫 | 新增 LLM 调用必须用 `if deterministic_validation:` 控制 |
| 排序 tie-break | 所有排序必须有明确的二级排序键 |
| DB 副作用 | 确定性模式下禁止写入数据库 |

## 门禁检查

```bash
make check-determinism
make test-quality-gate
```

## 受保护文件

- `backend/scripts/report/generate_t1_market_report.py`
- `backend/app/services/analysis/t1_stats.py`

## AI 协作指引

如果你是 AI Agent 正在修改上述文件：

1. 搜索 `DETERMINISM PROTOCOL` 注释了解约束
2. 搜索 `deterministic_validation` 了解守卫链
3. 新增时间查询时，必须接受 `anchor_ts` 参数
4. 新增 LLM 调用时，必须被 `deterministic_validation` 守卫
5. 修改后运行 `make check-determinism` 验证

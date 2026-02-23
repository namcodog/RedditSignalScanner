# Phase 179 - 快检：离线报告链路验证（dev）

日期：2026-01-28

## 本阶段目标
- 快速验证报告生成链路是否可跑通（离线/不调用 LLM）。

## 执行内容
- 运行离线报告脚本（跳过 LLM）：
  - 命令：`set -a && source backend/.env && set +a && PYTHONPATH=backend python backend/scripts/generate_t1_market_report.py --days 30 --skip-llm --out reports/t1-auto-quickcheck.md`

## 运行结果
- 脚本正常 заверш成，生成 facts_v2 JSON：
  - `/Users/hujia/Desktop/RedditSignalScanner/backend/reports/local-acceptance/facts_v2_119b4d88-1ecc-4d21-a422-cf66c2779a0a.json`
- 因 `--skip-llm`，未产出最终 Markdown 报告文件（仅产出事实包）。
- 过程中出现告警：
  - tokenizers fork 并行警告（建议设置 `TOKENIZERS_PARALLELISM=false`）
  - 数据质量降级（posts/comments/solutions 数量不足触发 fallback）

## 验证情况
- 事实包已生成、质量审计通过（脚本输出：`Validation passed`）。

## 风险与备注
- 若需要完整 Markdown 报告：需配置 LLM Key 并移除 `--skip-llm` 重新执行。


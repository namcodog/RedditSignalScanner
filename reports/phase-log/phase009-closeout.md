# Phase 009 收尾与验收指引

更新时间: 2025-11-11

## 本阶段完成项（与 Spec009 对齐）
- 抓取策略：实现“空集→回退（放宽/不过滤）”策略（crawler.yml → 运行逻辑接通）。
- 分层调度：crawler.yml + TieredScheduler 有效，黑名单治理接入。
- 冷/热协同：Redis 热缓存与 DB 热表沿用，增量水位线保留（新版逻辑）。
- 语义与实体：词库/指标/门禁/回灌的 Make 入口齐备（semantic-metrics/semantic-acceptance/semantic-refresh-pool 等）。
- 报告追溯：ReportMetadata 增加 lexicon_version（env 或词库文件推断）。
- 前端样例：SAMPLE_PROMPTS 跨境化，引导用户自然语言结构化输入。
- 工具封装：新增 crawl-crossborder / pool-stats / pool-clear-and-freeze / score-batched 与 phase009-verify。

## 运行与验收（建议顺序）
1) 隔离模式（默认）清池并冻结快照：
   - `make pool-clear-and-freeze`
2) 跨境抓取（无需 Celery Beat）：
   - `make crawl-crossborder`
   - `make pool-stats`
3) 生成抓取/语义快照（本地最佳努力）：
   - `make phase009-verify`
   - 输出：`backend/reports/local-acceptance/crawler-dryrun.md`、`reports/crawl-health-*.md`、`backend/reports/local-acceptance/metrics/*`
4) 语义门禁（存在本地语料时）：
   - `make semantic-metrics && make semantic-acceptance`
5) 报告门禁（需要服务运行）：
   - `make content-acceptance`

可选参数：
- 合并 Top1000 基线（探索模式）：`DISABLE_TOP1000_BASELINE=0 make crawl-crossborder`
- 启用白名单过滤：`ENFORCE_COMMUNITY_WHITELIST=1 make crawl-crossborder`

## 差距与风险（已收敛）
- Top1000 基线仍为示例数据，建议逐步替换为跨境主库；白名单开关已支持。
- 发现器 discover-crossborder 脚本后续可接入（当前以评分脚本与候选集替代）。

## 变更索引（文件路径）
- 前端样例：`frontend/src/pages/InputPage.tsx:40`
- 报告追溯：`backend/app/schemas/report_payload.py:70`、`backend/app/services/report_service.py:1006`
- 抓取回退：`backend/app/tasks/crawler_task.py:180`
- 白名单治理（可选）：`backend/app/services/community_pool_loader.py`、`backend/config/community_whitelist.yaml`
- Make 入口：`Makefile`（crawl-crossborder/pool-*/score-batched/phase009-verify）

## 备注（运维）
- 若命令涉及 Reddit API，请先配置 `.env`（client_id/secret/user_agent）与 Redis/Postgres 服务。
- 若语义指标较慢，可通过 `SEMANTIC_GATE_ARGS`/`MIN_*` 参数进行取舍；详见 Makefile 与脚本注释。


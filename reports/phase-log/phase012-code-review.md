# Phase 012 · 端到端闭环运行手册 对齐性代码审查

更新时间: 2025-11-11

## 总览结论
- 语义→回灌→抓取→分析→受控摘要→导出→门禁 的主链路均已具备可执行实现与命令入口；关键产物路径与 Spec 012 描述一致或等效。
- 主要风险点与差距集中在：
  1) 增量抓取路径未应用“空集→回退（放宽/不过滤）”策略（当前仅旧版批量抓取 `_crawl_seeds_impl` 应用）。
  2) Top1000 合并源仍为示例数据；已支持白名单开关，但默认隔离模式需保持开启。
  3) `content-acceptance` 作为本地脚本在服务依赖不足时会降级输出，建议在文档中强调前置服务状态自检。

## 对齐核查（逐步骤）

1) 语义质量（Spec011）
- 命令：`make semantic-metrics`、`make semantic-acceptance`（Makefile 已提供）。
- 阈值文件：`backend/config/quality_gates/semantic_thresholds.yml` 与脚本 `backend/scripts/semantic_acceptance_gate.py` 一致。
- 产物：`backend/reports/local-acceptance/metrics/metrics.{json,csv}`（OK）。

2) 语义→社区池回灌（Spec009）
- 自动流水线：`make semantic-release-auto`（影子评估/别名/门禁/报告/回灌）。
- 轻量回灌：`make semantic-refresh-pool`（Hybrid 评分 → 导入 `CommunityPool`，打 `layer:*` 标签，参考 `backend/scripts/import_hybrid_scores_to_pool.py`）。
- 类别与层级标注：`categories=["crossborder","crossborder:hybrid","layer:<L>"]`（OK）。

3) 抓取运行（Spec009）
- 策略配置：`backend/config/crawler.yml`（tier、fallback、热缓存 TTL、水位线开关）。
- Celery Beat 调度：`backend/app/core/celery_app.py` 已定义增量/预热/低质量补抓（OK）。
- 便利命令：`make crawl-crossborder`（隔离模式无合并）、`make crawler-dryrun`、`make phase009-verify`（OK）。
- 差距：增量抓取 `_crawl_seeds_incremental_impl` 未接入 fallback 放宽/不过滤策略（旧版 `_crawl_seeds_impl` 已接）。

4) 分析与报告（Spec010）
- 创建任务：`make local-acceptance` 或 API/UI（OK）。
- 受控摘要 v2：模板 `backend/config/report_templates/executive_summary_v2.md` + 生成器 `app/services/report/controlled_generator.py`（计算 P/S 比、竞争饱和度、层级覆盖，OK）。
- 报告追溯：`ReportMetadata.lexicon_version`（新增），LLM 审计字段（used/model/rounds）已注入（OK）。

5) 导出与门禁（Spec010）
- 导出接口：`GET /api/report/{id}/download?format=md|pdf|json`（OK；PDF 无 weasyprint 时降级 JSON）。
- 内容门禁：`make content-acceptance`（输出 `reports/local-acceptance/content-acceptance-*.json`，含簇/分层/证据密度等断言，OK）。

6) 故障自检与回退
- 语义不过线：阈值/指标文件与脚本齐备；`make refine-lexicon-fill` 可用于词库精炼（参考 Makefile 工具段）。
- 抓取空集：`crawler.yml` + `crawler_dryrun.py`；已实现旧版批量抓取的“空集→回退”，增量路径建议对齐。
- 摘要为空：受控生成器降级；导出接口 JSON 兜底（OK）。

## 差距与风险清单
1) 增量抓取未应用 Fallback（重要）
- 现状：`_crawl_seeds_incremental_impl` 直接调用 `IncrementalCrawler.crawl_community_incremental`，未在空集时放宽 time_filter/sort 或“all/top”保底。
- 影响：Beat 周期任务与 `make crawl-crossborder` 走增量链路时，遇空集的恢复能力不足；Spec 012 的“抓取为空→查看 fallback”仅在旧版路径成立。
- 建议：在增量路径 runner 中复用与 `_crawl_seeds_impl` 对齐的回退策略；或在 `IncrementalCrawler` 内部支持可选 fallback 钩子（避免重复实现）。

2) Top1000 合并源为示例数据（中）
- 现状：`backend/data/top1000_subreddits.json` 含泛社区；默认已设置 `DISABLE_TOP1000_BASELINE=1`（隔离）。
- 建议：持续维护 `backend/config/community_whitelist.yaml` 并在发布说明中强调隔离模式作为跨境验收基线。

3) 本地门禁/导出依赖服务（低）
- 现状：`content-acceptance` 需后端服务；`phase009-verify` 已尽量降级（best-effort）。
- 建议：在 README 与 Spec 012 中增补“服务未就绪 → 预期降级路径与退出码”说明。

## 精确修复方案（建议）
- 增量 Fallback：在 `backend/app/tasks/crawler_task.py::_crawl_seeds_incremental_impl.runner` 中，首次结果 `new_posts==0` 时，按 tier.fallback.widen_time_filter_to/relax_sort_mix → 再试；仍空且 allow_unfiltered_on_exhausted=true 时，`time_filter=all, sort=top, post_limit=ceil(1.2×)` 保底；记录 `fallback_applied` 标记。
- 跨境基线：将 `community_whitelist.yaml` 纳入 `semantic-release-auto` 的可选步骤（仅过滤 top1000 合并项，不影响 current pool）。
- 验收脚本：增加 `phase012-run`（一键串跑）封装 `semantic-metrics → semantic-acceptance → semantic-release-auto → content-acceptance`，输出关键信息到 `reports/phase-log/`。

## 验收建议（按 Spec 012）
1) `make semantic-metrics && make semantic-acceptance`
2) `make semantic-release-auto`（若 Reddit/DB 可用，否则跳过 Hybrid 与回灌）
3) `make content-acceptance`
4) 导出 md：`GET /api/report/{id}/download?format=md`

## 备注
- 进一步打磨：可在前端展示 `metadata.lexicon_version` 与 `metrics_summary` 折线卡片（非阻断）。


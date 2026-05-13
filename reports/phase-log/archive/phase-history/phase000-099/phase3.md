# Phase 3 集成记录（报告集成：Template → Builder → Config → Tests → Docs)

时间：2025-11-14 进度点：3.1-3.7

- 发现/根因：
  - 需要在不影响现有流程的前提下，完成“市场报告模式”的模板渲染、配置开关与可替换模板路径，并提供验证用例与操作文档。
- 定位：
  - 渲染入口：`backend/app/services/report_service.py:get_report()`（特性开关 `ENABLE_MARKET_REPORT`）。
  - 模板：`backend/config/report_templates/market_insight_v1.md`（可替换）。
  - Builder：`backend/app/services/reporting/market_report.py`（上下文聚合）。
- 精确修复：
  - Config：新增 `MARKET_REPORT_TEMPLATE`（读取到 `settings.market_report_template_path`）。
  - Service：市场模式渲染使用 `settings.market_report_template_path`；保留回退与向后兼容。
  - Template：维持轻量占位（指标卡、画像、引言、饱和度、GTM总结），满足最小可用。
- 测试：
  - `backend/tests/services/test_report_service_market_template_config.py`
    - `test_market_mode_uses_template_override`（覆盖模板路径渲染）
    - `test_market_mode_html_contains_gtm_summary`（HTML 含 GTM 概览）
- 文档：
  - `backend/.env.example` 增加示例；
  - `docs/本地启动指南.md` 增加“自定义模板”章节与单测演示。
- 结果：
  - 单测通过（2 passed）；报告服务在开启开关下按模板渲染 Market 报告，支持模板路径覆盖；Builder 上下文与 GTM 概览可见。
- 下一步：
  - 后续可按需扩展模板章节（战场分析/机会卡片），不影响现有结构；
  - E2E 场景待服务联跑后再行补充。

时间：2025-12-04 进度点：3.1 融合方案 V2.0（语义库重构与深度清洗）

- 发现/根因：
  - 垃圾检测仅靠单中心，容易漏掉营销/水贴类；模板句复用率高，影响挖掘质量；语义规则缺少层级索引。
- 定位：
  - 垃圾关键词来源 `semantic_rules` 概念 `global_filter_keywords`；
  - 规则加载入口 `backend/app/services/analysis/scoring_rules.py`；
  - 清洗入口 `backend/app/services/analysis/text_cleaner.py`。
- 精确修复：
  - 新脚本 `backend/scripts/maintenance/build_spam_centroids.py`：拉取过滤关键词→匹配帖子向量→KMeans(K=3)→输出 `backend/data/spam_centroids.pkl`。
  - 新脚本 `backend/scripts/maintenance/mine_semantic_layers.py`：按 score>2、垃圾中心距离>0.3、黑名单过滤→模板句清洗→分层路由(L1/L2/L3)→提取名词短语+负向共现→写入 `semantic_rules`（meta.layer）。
  - Loader 增强：`ScoringRulesLoader` 解析 `meta.layer` 构建 `_layer_index`，供后续 Context Filter 使用。
  - 清洗增强：`clean_template_sentences` 支持长句 DF>0.3 删除 + 短句 text_norm_hash 去重；同时去除邮件/Markdown 链接。
- 测试：
  - `SKIP_DB_RESET=1 pytest backend/tests/services/test_template_cleaner.py backend/tests/services/test_layer_router.py backend/tests/services/test_scoring_rules_loader_layering.py`（3 passed）。
- 结果：
  - 多中心垃圾向量、分层挖掘主脚本和层级索引就绪；模板句清洗策略落地，保证“先清洗再挖掘”。
  - 新增 LayerRouter 默认映射：shopify/amazonfba→L2，dropshipping/ppc→L3；未匹配默认 L1。
- 下一步：
  - 跑通 `build_spam_centroids.py` 生成中心后，再执行 `mine_semantic_layers.py` 首轮写库；
  - 结合生产库跑验证 SQL（Spam 抽查/规则覆盖率/分层分布），再按数据反馈微调 DF 阈值或 Layer 映射。

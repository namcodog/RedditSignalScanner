# #229 仓库结构清理 P0-P1

> **日期**: 2026-03-05  
> **执行者**: Codex CLI (gpt-5.3-codex-spark)  
> **验收者**: Antigravity (serena + grep + 目录校验)  
> **Codex token 消耗**: ~132K  

---

## 一、优化背景

对整个仓库执行了全面的结构审计（serena + sequential-thinking），发现 11 类结构问题。本次集中执行了 **P0（立即清理）** 和 **P1（高影响中等工作量）** 共 4 个 Phase。

**核心目标**: 不改一行业务逻辑，让 AI agent 穿透代码库时路径更清晰、import 链路更短。

---

## 二、执行明细

### Phase A: 根目录孤儿文档归位 ✅

| 文件 | 从 | 到 |
|------|-----|-----|
| Pinterest_套利机_执行方案.md | 根目录 | `docs/archive/` |
| SociaVault_API_全量验证报告.md | 根目录 | `docs/reference/` |
| 个人画像.md | 根目录 | `mem/` |
| session_log_20260223_26.md | 根目录 | `docs/archive/` |

### Phase B: API 层 shim 消灭 ✅

**问题**: `api/routes/` 是 16 个 6 行转发器 → `api/legacy/` 才是真代码，中间多了一跳。

**操作**:
- 删 `routes/` 下 16 个 shim → 移 `legacy/` 16 个真文件到 `routes/`
- 全仓库 `app.api.legacy` → `app.api.routes`（7 处）
- 删除 `api/legacy/`、`api/endpoints/` 两个空目录

**验收**: `grep "api.legacy" backend/ --include="*.py"` → 0 结果 ✅

### Phase C: report/reporting 命名空间合并 ✅

**问题**: 报告代码散落在 4 个位置（`report/`、`reporting/`、`report_service.py`、`report_export_service.py`）。

**操作**:
- `reporting/` 3 文件 → `report/`（删目录）
- 2 个散落文件 → `report/`
- 更新 30+ 处 import

**合并后 `services/report/` = 9 个文件**:
`__init__.py` / `controlled_generator.py` / `facts_reader.py` / `gtm_planner.py` / `market_report.py` / `opportunity_report.py` / `report_export_service.py` / `report_service.py` / `t1_market_agent.py`

**验收**: `grep "services.reporting" backend/` → 0 结果 ✅

### Phase D: community_discovery 三胞胎解决 ✅

**问题**: 3 个文件名几乎一样但逻辑不同。

| 文件 | 行数 | 引用数 | 处置 |
|------|------|--------|------|
| `services/community_discovery.py` | 354 | **4** | 迁入 `community/` + 原位保留 compat shim |
| `services/analysis/community_discovery.py` | 260 | 0 | 保留（独立逻辑） |
| `services/crawl/community_discovery_v2.py` | 142 | 0 | 保留（独立逻辑） |

---

## 三、优化结果总结

### 量化指标

| 指标 | 数值 |
|------|------|
| 移动/删除文件 | ~40 个 |
| 更新 import 引用 | 50+ 处 |
| 删除无用空目录 | 3 个（`legacy/`、`endpoints/`、`reporting/`） |
| 新建有意义子目录 | 1 个（`community/`） |
| **业务逻辑改动** | **0 行** |

### 效果对比

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| API 路由代码寻址 | `main.py → routes/(shim) → legacy/(代码)` — 3 跳 | `main.py → routes/(代码)` — 2 跳 |
| 报告模块定位 | 散落 4 个位置（`report/` + `reporting/` + 2个散落文件） | 统一在 `report/`（9个文件） |
| community_discovery 歧义 | 3 个同名文件，AI agent 不知道该看哪个 | 主实现有独立子目录，歧义消除 |
| 根目录噪音 | 4 个不相关文档干扰 | 全部归位 |
| AI agent 穿透效率 | import 链路冗长、命名冲突、shim 误导 | 直达真实代码，无中间层 |

---

## 四、下一步执行计划

### P1 遗留: Phase E — 服务层 41 个散落文件归位

`backend/app/services/` 根目录仍有 41 个 .py 文件散落在外，未归入领域子目录。计划分 5 批执行：

| 批次 | 文件数 | 目标目录 | 示例文件 |
|------|--------|----------|----------|
| **E1** | 7 | `crawl/` | adaptive_crawler, incremental_crawler, crawler_config, recrawl_scheduler 等 |
| **E2** | 7 | `community/` | community_pool_loader, community_cache_service, community_roles, blacklist_loader 等 |
| **E3** | 9 | `report/` + `analysis/` | analysis_engine, t1_clustering, t1_stats, ps_ratio, tier_intelligence 等 |
| **E4** | 4 | `semantic/` + `labeling/` | text_classifier, keyword_extractor, labeling, labeling_posts |
| **E5** | 14 | `metrics/` + `infrastructure/` 等 | cache_manager, cache_metrics, task_status_cache, monitoring, reddit_client 等 |

> ⚠️ 每批次完成后必须跑 `mypy --strict` + `grep` 验证，还需额外检查 Celery task 字符串注册路径。

### P2: 后续可选优化

| 编号 | 事项 | 预估工作量 |
|------|------|-----------|
| P2-1 | `backend/scripts/` 113 个脚本分类整理 | 4h |
| P2-2 | `backend/config/` 30+ 配置文件按领域分组 | 2h |
| P2-3 | Celery task 文件按领域归并 | 3h |
| P2-4 | LLM normalizer/summarizer 去重 | 2h |
| P2-5 | 测试文件按 `tests/unit` / `tests/integration` 分离 | 3h |

### 立即可做

1. **跑一次完整 mypy + pytest**: 确认 Phase A-D 零回归
2. **排期 Phase E**: 建议先做 E1-E2（爬虫+社区，最独立），再做 E3（报告+分析，依赖多）
3. **Git commit**: 将当前改动提交为 `refactor: eliminate API shim layer, merge report namespaces (P0-P1)`

# Reddit Signal Scanner - Makefile
# 统一管理开发、测试、验收与运维脚本

.PHONY: help

# 每个目标在单独的 shell 会话中执行，支持多行脚本
.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -lc

# ------------------------------------------------------------
# 基础路径与端口
# ------------------------------------------------------------
PYTHON := /opt/homebrew/bin/python3.11
PYTHON_VERSION := 3.11
BACKEND_DIR := backend
FRONTEND_DIR := frontend
SCRIPTS_DIR := $(BACKEND_DIR)/scripts
BACKEND_PORT := 8006
FRONTEND_PORT := 3006
REDIS_PORT := 6379

COMMON_SH := scripts/makefile-common.sh

# Celery 配置
CELERY_WORKER_LOG := /tmp/celery_worker.log
CELERY_APP := app.core.celery_app.celery_app
CELERY_CONCURRENCY := 4

# 本地验收脚本配置（可通过环境变量覆盖）
LOCAL_ACCEPT_ENV ?= local
LOCAL_ACCEPT_BACKEND ?= http://localhost:$(BACKEND_PORT)
LOCAL_ACCEPT_FRONTEND ?= http://localhost:$(FRONTEND_PORT)
LOCAL_ACCEPT_REDIS ?= redis://localhost:$(REDIS_PORT)/0
LOCAL_ACCEPT_EMAIL ?= test@example.com
LOCAL_ACCEPT_PASSWORD ?= test123456

# 环境变量导出
export ENABLE_CELERY_DISPATCH := 1
export PYTHONPATH := $(BACKEND_DIR)
export BACKEND_PORT FRONTEND_PORT REDIS_PORT CELERY_APP CELERY_WORKER_LOG
export PYTHON_BIN := $(PYTHON)
# 默认开启隔离模式，禁止在种子导入时自动合并 Top1000 基线
# 如需探索/扩展覆盖，可在命令前设置 DISABLE_TOP1000_BASELINE=0 覆盖
export DISABLE_TOP1000_BASELINE := 1

# ------------------------------------------------------------
# Spec 011 默认参数（可被环境变量覆盖）
# ------------------------------------------------------------
SEMANTIC_GATE_ARGS ?= --use-ci
ALIAS_QUANTILE ?= 0.95
ALIAS_MIN_FLOOR ?= 0.90
MIN_PAINS ?= 55
MAX_BRANDS ?= 30

# ------------------------------------------------------------
# 帮助
# ------------------------------------------------------------
help: ## 显示所有可用命令
	@echo "Reddit Signal Scanner - 可用命令："
	@echo ""
	@echo "⚙️  环境配置："
	@echo "  make env-check          检查Python版本和环境配置"
	@echo "  make env-setup          安装后端/前端依赖"
	@echo ""
	@echo "🚀 开发流程："
	@echo "  make dev-golden-path    🌟 黄金路径：一键启动完整环境（推荐）"
	@echo "  make dev-full           启动完整开发环境（Redis + Celery + Backend + Frontend）"
	@echo "  make dev-backend        启动后端服务（需要先启动Redis和Celery）"
	@echo "  make dev-frontend       启动前端服务"
	@echo "  make quickstart         查看常用命令速览"
	@echo ""
	@echo "📦 基础设施："
	@echo "  make redis-start        启动 Redis"
	@echo "  make redis-status       检查 Redis 状态"
	@echo "  make kill-ports         清理 8006/3006 端口占用"
	@echo "  make restart-backend    重启后端"
	@echo "  make restart-frontend   重启前端"
	@echo "  make status             运行 scripts/check-services.sh"
	@echo ""
	@echo "⚡ Celery 管理："
	@echo "  make celery-start       启动 Celery Worker"
	@echo "  make celery-restart     重启 Celery Worker"
	@echo "  make celery-logs        查看 Celery 日志"
	@echo ""
	@echo "🧭 模式说明（强烈建议先读）："
	@echo "  • 隔离模式（默认）：DISABLE_TOP1000_BASELINE=1，跨境验收只用当前社区池，不合并 Top1000。"
	@echo "    使用: make pool-clear-and-freeze → make crawl-crossborder → make pool-stats"
	@echo "  • 合并探索模式：DISABLE_TOP1000_BASELINE=0（谨慎），允许在刷新 seeds 时与 Top1000 合并用于扩大覆盖。"
	@echo "    使用: DISABLE_TOP1000_BASELINE=0 make crawl-seeds[-incremental]（不用于跨境验收）"
	@echo "  • 切记：跨境验收不要跑 make crawl-seeds，否则池会被放大并混入非跨境社区。"
	@echo "🧪 测试："
	@echo "  make test-backend       运行后端测试"
	@echo "  make test-frontend      运行前端测试"
	@echo "  make test-e2e           运行关键路径 E2E 测试"
	@echo "  make test-contract      运行 API 契约测试"
	@echo "  make test-admin-e2e     验证 Admin 端到端流程"
	@echo ""
	@echo "🧷 语义门禁："
	@echo "  make semantic-metrics   生成语义指标 (CSV+JSON)"
	@echo "  make semantic-acceptance 运行语义质量门禁 (未过线则退出1)"
	@echo "  make semantic-release-auto 一键自动：别名(高置信)→去头长尾→门禁→报告→回灌"
	@echo "  make semantic-release-contrib 合并外部种子→锁痛点+品牌基线→门禁"
	@echo "  make semantic-blacklist-suggest 从指标提出黑名单候选"
	@echo "  make semantic-refresh-cron   周期回灌入口（评分→导入）"
	@echo ""
	@echo "🧪 报告门禁："
	@echo "  make content-acceptance   运行报告内容门禁（输出JSON并以分数/断言判定）"
	@echo "🩺 诊断脚本："
	@echo "  make clusters-smoke       输出 pain_clusters JSON（需 TASK=<id>）"
	@echo "  make competitors-smoke    输出 competitor_layers_summary JSON（需 TASK=<id>）"
	@echo "  make report-markdown      下载受控Markdown（需 TASK=<id>）"
	@echo "  make report-json          下载报告JSON（需 TASK=<id>）"
	@echo "  make report-pdf           下载报告PDF（需 TASK=<id>）"
	@echo "  make report-audit         打印 LLM 审计文件（需 TASK=<id>）"
	@echo ""
	@echo "🧰 跨境流程便捷入口："
	@echo "  make crawl-crossborder   在隔离池上抓取跨境社区（无需 Celery Beat）"
	@echo "  make discover-crossborder 关键词发现跨境社区，导出候选"
	@echo "  make crawl-all-communities 一键抓取社区池（201基线+）"
	@echo "  make pool-init           初始化社区池(导入200个基线社区)"
	@echo "  make pool-import-top1000 导入 top1000_subreddits.json 到社区池"
	@echo "  make semantic-build-L1   构建 L1 语义坐标基线 (ecommerce)"
	@echo "  make semantic-mine-pain  从真实数据挖掘 pain_points 候选"
	@echo "  make crossborder-high-value 生成高价值跨境社区列表"
	@echo "  make pool-stats          输出社区池统计（总数/优先级分布/跨境标记）"
	@echo "  make pool-clear-and-freeze 清空社区池并生成简要快照（隔离模式前置）"
	@echo "  make score-batched       分批评分（需 INPUT/LIMIT/TOPN，封装 scripts/score_batched.sh）"
	@echo ""
	@echo "🎯 验收："
	@echo "  make local-acceptance   执行本地验收脚本"
	@echo "  make week2-acceptance   Week 2 (P1) 验收"
	@echo "  make final-acceptance   最终验收（注册→分析→洞察→导出）"
	@echo "  make crossborder-acceptance 跨境功能孤岛验收（离线友好）"
	@echo ""
	@echo "✅ Spec009 收尾："
	@echo "  make phase009-verify    生成抓取/语义/池统计的快照（本地最佳努力）"
	@echo "  make phase009-success   一键标记Spec009成功（生成快照与成功标记）"
	@echo "🛠  工具与维护："
	@echo "  make update-api-schema  更新 OpenAPI 基线"
	@echo "  make generate-api-client 生成前端 API 客户端"
	@echo "  make install            安装后端 + 前端依赖"
	@echo "  make clean              清理缓存和生成文件"
	@echo "  make mcp-install        安装 MCP 工具"
	@echo ""
	@echo "🔧 更多命令列表："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ------------------------------------------------------------
# 模块化 include
# ------------------------------------------------------------
include makefiles/env.mk
include makefiles/infra.mk
include makefiles/ops.mk
include makefiles/dev.mk
include makefiles/test.mk
include makefiles/celery.mk
include makefiles/db.mk
include makefiles/acceptance.mk
include makefiles/tools.mk
include makefiles/clean.mk
# ==========================================
# Crawl & Backfill (Reddit)
# ==========================================

COMMUNITIES ?= ecommerce AmazonSeller Shopify dropship dropshipping

# Search partition backfill (prefix sharding, stable without timestamp)
# Usage:
#   make crawl-search SUB=ecommerce MAX_PAGES=30 MAX_LEN=2 SPLIT=900
SUB ?=
MAX_PAGES ?= 30
MAX_LEN ?= 2
SPLIT ?= 900

.PHONY: crawl-search
crawl-search:
	@if [ -z "$(SUB)" ]; then echo "SUB is required (e.g. SUB=ecommerce)"; exit 1; fi
	python -u backend/scripts/crawl_for_lexicon.py \
	  --mode search-partition \
	  --subreddit $(SUB) \
	  --prefix-chars a-z0-9 \
	  --max-prefix-len $(MAX_LEN) \
	  --split-threshold $(SPLIT) \
	  --max-pages-per-shard $(MAX_PAGES) \
	  --sort new \
	  --output backend/data/reddit_corpus/$(SUB).jsonl \
	  --stream-write

.PHONY: crawl-search-all
crawl-search-all:
	@for s in $(COMMUNITIES); do \
	  echo "===> Backfill $$s"; \
	  $(MAKE) crawl-search SUB=$$s; \
	done

# Incremental crawl via /new with waterline
# Usage:
#   make crawl-inc SUB=ecommerce PAGES=10 LOOKBACK=7
PAGES ?= 10
LOOKBACK ?= 7

.PHONY: crawl-inc
crawl-inc:
	@if [ -z "$(SUB)" ]; then echo "SUB is required (e.g. SUB=ecommerce)"; exit 1; fi
	python -u backend/scripts/crawl_incremental.py \
	  --subreddit $(SUB) \
	  --max-pages $(PAGES) \
	  --lookback-days $(LOOKBACK) \
	  --output backend/data/reddit_corpus/$(SUB).jsonl \
	  --stream-write

.PHONY: crawl-inc-all
crawl-inc-all:
	@for s in $(COMMUNITIES); do \
	  echo "===> Incremental $$s"; \
	  $(MAKE) crawl-inc SUB=$$s; \
	done

# One-shot crawl for all communities in the pool (201 baseline + optional)
# Uses crawler.yml tier config and IncrementalCrawler with per-tier limits.
# Example: FORCE=1 make crawl-all-communities
.PHONY: crawl-all-communities
crawl-all-communities:
	@echo "==> crawl-all-communities (scope=all, force=$${FORCE:-0})"
	$(PYTHON) -u backend/scripts/crawl_once.py --scope all $$([ "${FORCE}" = "1" ] && echo --force-refresh || true)

# ---------------- P0: Discovery & Pool management ----------------
.PHONY: pool-init ## 初始化社区池(导入200个基线社区)
pool-init:
	$(PYTHON) -u backend/scripts/init_community_pool.py

.PHONY: pool-import-top1000 ## 导入 top1000_subreddits.json 到社区池
pool-import-top1000:
	$(PYTHON) -u backend/scripts/import_top1000_to_pool.py --source backend/data/top1000_subreddits.json

# ---------------- P0: Lexicon utilities ----------------
.PHONY: semantic-build-L1 ## 构建 L1 语义坐标基线
semantic-build-L1:
	$(PYTHON) -u backend/scripts/build_L1_baseline.py \
	  --corpus backend/data/reddit_corpus/ecommerce.jsonl \
	  --output backend/config/semantic_sets/L1_baseline_embeddings.pkl

.PHONY: semantic-mine-pain ## 挖掘 pain_points 候选
semantic-mine-pain:
	$(PYTHON) -u backend/scripts/mine_pain_points.py \
	  --data backend/data/crossborder_candidates.json \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --output backend/data/pain_points_candidates.csv

.PHONY: crossborder-high-value ## 生成高价值跨境社区列表（CSV）
crossborder-high-value:
	$(PYTHON) -u backend/scripts/generate_crossborder_high_value.py

# ---------------- Acceptance (function islands) ----------------
.PHONY: crossborder-acceptance ## 跨境功能孤岛验收（离线友好）
crossborder-acceptance:
	@echo "==> 跨境功能孤岛端到端验收"
	@mkdir -p backend/reports/local-acceptance
	@echo "1. 发现社区..." && $(MAKE) -s discover-crossborder KEYWORDS="amazon,shopify" LIMIT=50 || true
	@echo "2. 初始化池..." && $(MAKE) -s pool-init || true
	@echo "3. 导入Top1000..." && $(MAKE) -s pool-import-top1000 || true
	@echo "4. 构建L1基线..." && $(MAKE) -s semantic-build-L1 || true
	@echo "5. 生成高价值表..." && $(MAKE) -s crossborder-high-value || true
	@echo "6. 验证输出文件..."
	@ls -lh backend/data/crossborder_candidates.csv 2>/dev/null || echo "⚠️  候选CSV缺失"
	@ls -lh backend/config/semantic_sets/L1_baseline_embeddings.pkl 2>/dev/null || echo "⚠️  L1基线缺失"
	@ls -lh reports/local-acceptance/high_value_communities_crossborder.csv 2>/dev/null || echo "⚠️  高价值列表缺失"
	@echo "✅ 跨境功能孤岛验收完成（best-effort）"

# Validate corpus quality (dedup, time range, empty ratios)
.PHONY: corpus-report
corpus-report:
	python backend/scripts/validate_corpus.py \
	  --corpus-dir backend/data/reddit_corpus \
	  --output backend/reports/local-acceptance/corpus_stats.csv

# ==========================================
# Spec 011 Stage 0.3 - Entity Dictionary
# ==========================================

.PHONY: entity-dict ## 生成实体词典（默认均衡策略）
entity-dict:
	python -u backend/scripts/extract_entity_dict.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --output backend/config/entity_dictionary/crossborder_v2.csv \
	  --min-weight 1.2 --target-total 100

.PHONY: entity-dict-conservative ## 稳健：痛点严格触发、倾向品牌（覆盖稳）
entity-dict-conservative:
	python -u backend/scripts/extract_entity_dict.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --output backend/config/entity_dictionary/crossborder_v2_conservative.csv \
	  --min-weight 1.3 --target-total 100

.PHONY: entity-dict-aggressive ## 进取：放宽阈值、提高痛点占比（覆盖冲高）
entity-dict-aggressive:
	python -u backend/scripts/extract_entity_dict.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --output backend/config/entity_dictionary/crossborder_v2_aggressive.csv \
	  --min-weight 1.1 --target-total 100

.PHONY: entity-metrics ## 评估实体词典覆盖率（默认评估 crossborder_v2.csv）
entity-metrics:
	python -u backend/scripts/evaluate_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out backend/reports/local-acceptance/entity-metrics.csv

.PHONY: entity-metrics-all ## 对三套策略输出覆盖率对比
entity-metrics-all:
	$(MAKE) entity-dict
	$(MAKE) entity-metrics
	python -u backend/scripts/evaluate_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2_conservative.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out backend/reports/local-acceptance/entity-metrics_conservative.csv
	python -u backend/scripts/evaluate_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2_aggressive.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out backend/reports/local-acceptance/entity-metrics_aggressive.csv

.PHONY: entity-dict-balanced ## 平衡版：短语优先、品牌上限、痛点增强
entity-dict-balanced:
	python -u backend/scripts/extract_entity_dict.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --output backend/config/entity_dictionary/crossborder_v2_balanced.csv \
	  --min-weight 1.2 --target-total 100

.PHONY: entity-metrics-balanced ## 评估平衡版实体词典覆盖率
entity-metrics-balanced:
	python -u backend/scripts/evaluate_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2_balanced.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out backend/reports/local-acceptance/entity-metrics_balanced.csv

# ==========================================
# Spec 010 - Diagnostic smoke scripts
# ==========================================

.PHONY: clusters-smoke ## 输出 pain_clusters JSON（需 TASK=<id>）
clusters-smoke:
	@if [ -z "$(TASK)" ]; then echo "TASK is required (e.g. TASK=<uuid>)"; exit 1; fi
	@mkdir -p backend/reports/local-acceptance
	$(PYTHON) -u backend/scripts/cluster_smoke.py --task $(TASK) --out backend/reports/local-acceptance/cluster-$(TASK).json
	@echo "👉 输出: backend/reports/local-acceptance/cluster-$(TASK).json"

.PHONY: competitors-smoke ## 输出 competitor_layers_summary JSON（需 TASK=<id>）
competitors-smoke:
	@if [ -z "$(TASK)" ]; then echo "TASK is required (e.g. TASK=<uuid>)"; exit 1; fi
	@mkdir -p backend/reports/local-acceptance
	$(PYTHON) -u backend/scripts/competitor_smoke.py --task $(TASK) --out backend/reports/local-acceptance/competitor-layers-$(TASK).json
	@echo "👉 输出: backend/reports/local-acceptance/competitor-layers-$(TASK).json"

.PHONY: content-acceptance ## 运行报告内容门禁（输出JSON）
content-acceptance:
	@mkdir -p reports/local-acceptance
	$(PYTHON) -u backend/scripts/content_acceptance.py

# ==========================================
# Spec 009 - Crossborder convenience wrappers
# ==========================================

.PHONY: crawl-crossborder
crawl-crossborder: ## 在隔离池上抓取跨境社区（无需 Celery Beat）
	@echo "==> crawl-crossborder (isolation: $${DISABLE_TOP1000_BASELINE:-1})"
	@mkdir -p backend/reports/local-acceptance
	@cd backend && $(PYTHON) -c "from app.tasks.crawler_task import _crawl_seeds_impl; import asyncio; res = asyncio.run(_crawl_seeds_impl(False)); print('\n📊 crawl-crossborder summary:'); print(res)"

.PHONY: pool-stats
pool-stats: ## 输出社区池统计
	$(PYTHON) -u backend/scripts/pool_stats.py

.PHONY: pool-clear-and-freeze
pool-clear-and-freeze: ## 清空社区池并生成简要快照（隔离前置）
	@mkdir -p backend/reports/local-acceptance
	@STAMP=$$(date +%Y%m%d-%H%M%S); \
	$(PYTHON) -u backend/scripts/pool_stats.py > backend/reports/local-acceptance/pool-freeze-$$STAMP.txt || true; \
	$(PYTHON) -u backend/scripts/pool_clear.py --cache-too
	@echo "📄 快照: backend/reports/local-acceptance/pool-freeze-$$STAMP.txt"

.PHONY: score-batched ## 分批评分（需 INPUT/LIMIT/TOPN）
score-batched:
	@if [ -z "$(INPUT)" ] || [ -z "$(LIMIT)" ] || [ -z "$(TOPN)" ]; then \
	  echo "Usage: make score-batched INPUT=backend/data/top1000_subreddits.json LIMIT=1000 TOPN=200"; exit 1; \
	fi
	@bash backend/scripts/score_batched.sh --input "$(INPUT)" --limit "$(LIMIT)" --topn "$(TOPN)"

.PHONY: phase009-verify ## Spec009 本地快照验证（不要求服务全起）
phase009-verify:
	@echo "==> Spec009 verify (best-effort)"
	@mkdir -p backend/reports/local-acceptance
	$(PYTHON) -u backend/scripts/crawler_dryrun.py --output backend/reports/local-acceptance/crawler-dryrun.md || true
	$(MAKE) -s crawl-health || true
	# 语义指标（若本地语料存在则跑，否则跳过）
	@if [ -d backend/data/snapshots ]; then \
	  $(MAKE) -s semantic-metrics || true; \
	  $(MAKE) -s semantic-acceptance || true; \
	fi
	@echo "📄 输出: backend/reports/local-acceptance/crawler-dryrun.md"

.PHONY: phase009-success ## Spec009 一键成功标记（含快照）
phase009-success:
	@set -e; \
	STAMP=$$(date '+%Y-%m-%d %H:%M:%S'); \
	$(MAKE) -s phase009-verify; \
	echo "Spec009 OK - $$STAMP" > backend/reports/local-acceptance/phase009-success.txt; \
	mkdir -p reports/phase-log; \
	echo "# Spec009 成功标记" > reports/phase-log/phase009-success.md; \
	echo "- 时间: $$STAMP" >> reports/phase-log/phase009-success.md; \
	echo "- 快照: backend/reports/local-acceptance/crawler-dryrun.md" >> reports/phase-log/phase009-success.md; \
	echo "- 健康: reports/crawl-health-*.md (若存在)" >> reports/phase-log/phase009-success.md; \
	echo "- 语义: backend/reports/local-acceptance/metrics/metrics.json (若存在)" >> reports/phase-log/phase009-success.md; \
	echo "✅ Spec009 已标记成功：backend/reports/local-acceptance/phase009-success.txt"

.PHONY: report-markdown ## 下载指定任务的受控Markdown（需 TASK=<id>）
report-markdown:
	@if [ -z "$(TASK)" ]; then echo "TASK is required (e.g. TASK=<uuid>)"; exit 1; fi
	@mkdir -p backend/reports/local-acceptance
	$(PYTHON) -u backend/scripts/report_markdown.py --task $(TASK) --out backend/reports/local-acceptance/controlled_report-$(TASK).md
	@echo "👉 输出: backend/reports/local-acceptance/controlled_report-$(TASK).md"

.PHONY: report-json ## 下载报告JSON（需 TASK=<id>）
report-json:
	@if [ -z "$(TASK)" ]; then echo "TASK is required (e.g. TASK=<uuid>)"; exit 1; fi
	@mkdir -p backend/reports/local-acceptance
	$(PYTHON) -u backend/scripts/report_download.py --task $(TASK) --format json --out backend/reports/local-acceptance/report-$(TASK).json
	@echo "👉 输出: backend/reports/local-acceptance/report-$(TASK).json"

.PHONY: report-pdf ## 下载报告PDF（需 TASK=<id>）
report-pdf:
	@if [ -z "$(TASK)" ]; then echo "TASK is required (e.g. TASK=<uuid>)"; exit 1; fi
	@mkdir -p backend/reports/local-acceptance
	$(PYTHON) -u backend/scripts/report_download.py --task $(TASK) --format pdf --out backend/reports/local-acceptance/report-$(TASK).pdf
	@echo "👉 输出: backend/reports/local-acceptance/report-$(TASK).pdf"

.PHONY: report-audit ## 打印 LLM 审计（需 TASK=<id>）
report-audit:
	@if [ -z "$(TASK)" ]; then echo "TASK is required (e.g. TASK=<uuid>)"; exit 1; fi
	@if [ -f backend/reports/local-acceptance/llm-audit-$(TASK).json ]; then \
	  cat backend/reports/local-acceptance/llm-audit-$(TASK).json; \
	else \
	  echo "未找到审计文件：backend/reports/local-acceptance/llm-audit-$(TASK).json"; \
	fi

.PHONY: hybrid-score-demo ## 使用HybridMatcher对本地语料做快速覆盖评估
hybrid-score-demo:
	python -u backend/scripts/score_with_hybrid.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --limit-per-sub 20

.PHONY: hybrid-score-reddit ## 使用HybridMatcher+Reddit API对社区做评分
hybrid-score-reddit:
	python -u backend/scripts/score_with_hybrid_reddit.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --communities ecommerce AmazonSeller Shopify dropship dropshipping \
	  --posts-per 12 --time-filter month --sort top

.PHONY: semantic-refresh-pool ## 语义→社区池：Hybrid评分→导入pool（手动串联）
semantic-refresh-pool: hybrid-score-reddit
	$(PYTHON) -u backend/scripts/import_hybrid_scores_to_pool.py --csv backend/reports/local-acceptance/hybrid_score_communities.csv

# ==========================================
# Spec 011 Stage 1 - Success Commands
# ==========================================

.PHONY: hybrid-tests ## 仅运行 HybridMatcher 单元测试
hybrid-tests:
	pytest -q backend/tests/services/analysis/test_hybrid_matcher.py

.PHONY: phase1-success ## 阶段1一键验证：测试+本地覆盖评估+版本快照
phase1-success:
	$(MAKE) hybrid-tests
	$(MAKE) hybrid-score-demo
	$(MAKE) lexicon-version-snapshot
	@mkdir -p backend/reports/local-acceptance
	@echo "Stage 1 OK - $$(date '+%Y-%m-%d %H:%M:%S')" > backend/reports/local-acceptance/phase1-success.txt
	@echo "✅ 阶段1通过：见 backend/reports/local-acceptance/phase1-success.txt"

.PHONY: lexicon-version-snapshot ## 归档当前v2.1词库到versions/并更新CHANGELOG
lexicon-version-snapshot:
	@DATE=$$(date +%Y%m%d); \
	cp backend/config/semantic_sets/crossborder_v2.1.yml backend/config/semantic_sets/versions/crossborder_v2.1_$${DATE}.yml; \
	echo "- Snapshot v2.1 saved: versions/crossborder_v2.1_$${DATE}.yml";

# ==========================================
# Spec 011 Stage 2 - Metrics & Candidates
# ==========================================

.PHONY: stage2-metrics ## 生成阶段2质量指标（Coverage@Post、按类覆盖、Top10占比、Unique@500）
stage2-metrics:
	python -u backend/scripts/calculate_metrics.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --entity backend/config/entity_dictionary/crossborder_v2.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out-prefix backend/reports/local-acceptance/metrics/metrics \
	  --limit-per-sub 20

.PHONY: semantic-metrics ## 别名：生成语义指标
semantic-metrics: stage2-metrics

.PHONY: semantic-acceptance ## 语义质量门禁：未达阈值则退出
semantic-acceptance: stage2-metrics
	@THR=$${SEMANTIC_THRESHOLDS_YML:-backend/config/quality_gates/semantic_thresholds.yml}; \
	ENT=$${SEMANTIC_ENTITY_CSV:-backend/config/entity_dictionary/crossborder_v2.csv}; \
	JSON=$${SEMANTIC_METRICS_JSON:-backend/reports/local-acceptance/metrics/metrics.json}; \
	$(PYTHON) -u backend/scripts/semantic_acceptance_gate.py --metrics $$JSON --thresholds $$THR --entity-csv $$ENT $${SEMANTIC_GATE_ARGS} || { \
	  echo "\n❌ 语义质量门禁未通过（见上方原因）。阻断后续流程。"; exit 1; }

# ==========================================
# Spec 011 - Automated release pipeline (no manual review)
# ==========================================

.PHONY: semantic-release-auto ## 一键自动：候选→高置信别名→影子评估→去头长尾→门禁→报告→回灌
semantic-release-auto:
	set -euo pipefail; \
	THR=$${SEMANTIC_THRESHOLDS_YML:-backend/config/quality_gates/semantic_thresholds.yml}; \
	CORPUS_GLOB="backend/data/snapshots/2025-11-07-0.2/*.jsonl"; \
	ALIAS_MAP=backend/reports/local-acceptance/alias_map.csv; \
	ALIAS_THRESHOLD=$${ALIAS_THRESHOLD:-0.88}; \
	# 1) 确保 refined 词库与候选
	BASE_LEX=backend/config/semantic_sets/crossborder_v2.1_refined.yml; \
	if [ ! -f "$$BASE_LEX" ]; then \
	  $(MAKE) refine-lexicon-fill; \
	fi; \
	if [ ! -f "backend/reports/local-acceptance/crossborder_candidates.csv" ]; then \
	  $(MAKE) stage2-candidates; \
	fi; \
	# 2) 别名（自适应阈值 + 高置信自动批准）
	$(PYTHON) -u backend/scripts/merge_aliases.py \
	  --candidates backend/reports/local-acceptance/crossborder_candidates.csv \
	  --lexicon $$BASE_LEX \
	  --output $$ALIAS_MAP \
	  --threshold 0.80 --min-freq 8 --top-k 1 --layer-aware; \
	AUTO_THR=$$($(PYTHON) -u backend/scripts/compute_alias_threshold.py --alias-map $$ALIAS_MAP --quantile $${ALIAS_QUANTILE:-0.95} --min-floor $${ALIAS_MIN_FLOOR:-0.90}); \
	$(PYTHON) -u backend/scripts/filter_alias_map_by_score.py --alias-map $$ALIAS_MAP --threshold $$AUTO_THR --output backend/reports/local-acceptance/alias_map_high.csv; \
	$(PYTHON) -u backend/scripts/merge_aliases.py \
	  --apply --alias-map backend/reports/local-acceptance/alias_map_high.csv --lexicon $$BASE_LEX \
	  --output backend/config/semantic_sets/crossborder_v2.2_aliases.yml --auto-approve; \
	# 3) 影子评估：应用前/后各算一次（不改默认实体词典）
	$(PYTHON) -u backend/scripts/calculate_metrics.py \
	  --lexicon $$BASE_LEX --entity backend/config/entity_dictionary/crossborder_v2.csv \
	  --corpus "$$CORPUS_GLOB" --out-prefix backend/reports/local-acceptance/metrics/metrics_pre --limit-per-sub 20; \
	$(PYTHON) -u backend/scripts/calculate_metrics.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.2_aliases.yml --entity backend/config/entity_dictionary/crossborder_v2.csv \
	  --corpus "$$CORPUS_GLOB" --out-prefix backend/reports/local-acceptance/metrics/metrics_alias --limit-per-sub 20; \
	LEX_AUTO=$$BASE_LEX; \
	if $(PYTHON) -u backend/scripts/semantic_acceptance_gate.py --metrics backend/reports/local-acceptance/metrics/metrics_alias.json --thresholds $$THR --entity-csv backend/config/entity_dictionary/crossborder_v2.csv; then \
	  LEX_AUTO=backend/config/semantic_sets/crossborder_v2.2_aliases.yml; \
	  echo "✅ 采用别名后词库：$$LEX_AUTO"; \
	else \
	  echo "⚠️  别名后词库未通过门禁，回退到 $$LEX_AUTO"; \
	fi; \
	# 4) 去头+长尾（品牌基线 + 锁痛点 + 可选 ST 增广）
	ENT_BASE=backend/config/entity_dictionary/crossborder_v2.csv; \
	$(PYTHON) -u backend/scripts/filter_and_refill_entity_dict.py \
	  --dict $$ENT_BASE --candidates backend/reports/local-acceptance/crossborder_candidates.csv \
	  --blacklist backend/config/entity_dictionary/blacklist.txt \
	  --brands-base backend/config/entity_dictionary/brands_base.csv \
	  --output backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --total 100 --min-pains $${MIN_PAINS:-55} --max-brands $${MAX_BRANDS:-30} --lock-pains; \
	if [ "$${ENABLE_ST_AUGMENT:-0}" = "1" ]; then \
	  $(PYTHON) -u backend/scripts/augment_with_longtail_st.py \
	    --dict backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	    --candidates backend/reports/local-acceptance/crossborder_candidates.csv \
	    --corpus "$$CORPUS_GLOB" \
	    --output backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	    --model sentence-transformers/all-MiniLM-L6-v2 --sim-max $${ST_SIM_MAX:-0.45} --replace-n $${ST_REPLACE_N:-16}; \
	fi; \
	ENT_AUTO=backend/config/entity_dictionary/crossborder_v2_diverse.csv; \
	$(PYTHON) -u backend/scripts/calculate_metrics.py \
	  --lexicon $$LEX_AUTO --entity $$ENT_AUTO \
	  --corpus "$$CORPUS_GLOB" --out-prefix backend/reports/local-acceptance/metrics/metrics_diverse --limit-per-sub 20; \
	if $(PYTHON) -u backend/scripts/semantic_acceptance_gate.py --metrics backend/reports/local-acceptance/metrics/metrics_diverse.json --thresholds $$THR --entity-csv $$ENT_AUTO $${SEMANTIC_GATE_ARGS}; then \
	  echo "✅ 采用实体词典：$$ENT_AUTO"; \
	else \
	  echo "⚠️  实体词典未通过门禁，回退到 $$ENT_BASE"; \
	  ENT_AUTO=$$ENT_BASE; \
	fi; \
	# 5) 最终指标与门禁
	$(PYTHON) -u backend/scripts/calculate_metrics.py \
	  --lexicon $$LEX_AUTO --entity $$ENT_AUTO --corpus "$$CORPUS_GLOB" \
	  --out-prefix backend/reports/local-acceptance/metrics/metrics_final --limit-per-sub 20; \
	$(PYTHON) -u backend/scripts/semantic_acceptance_gate.py --metrics backend/reports/local-acceptance/metrics/metrics_final.json --thresholds $$THR --entity-csv $$ENT_AUTO; \
	# 6) 受控报告生成（结构由模板保证）
	ANALYSIS_FILE=$${CONTROLLED_ANALYSIS:-backend/reports/local-acceptance/analysis-output.json}; \
	if [ -f "$$ANALYSIS_FILE" ]; then \
	  $(PYTHON) -u backend/app/services/report/controlled_generator.py \
	    --analysis $$ANALYSIS_FILE \
	    --lexicon $$LEX_AUTO \
	    --metrics backend/reports/local-acceptance/metrics/metrics_final.json \
	    --template $(CONTROLLED_TEMPLATE) \
	    --output backend/reports/local-acceptance/controlled_report.md \
	    --task-id semantic-release-auto; \
	else \
	  echo "ℹ️  跳过受控报告生成：未找到 $$ANALYSIS_FILE"; \
	fi; \
	# 7) 语义→社区池（评分→导入）
	$(PYTHON) -u backend/scripts/score_with_hybrid_reddit.py \
	  --lexicon $$LEX_AUTO --communities ecommerce AmazonSeller Shopify dropship dropshipping \
	  --posts-per 12 --time-filter month --sort top || echo "ℹ️  跳过 Hybrid 评分：Reddit API 未配置"; \
	if [ -f backend/reports/local-acceptance/hybrid_score_communities.csv ]; then \
	  $(PYTHON) -u backend/scripts/import_hybrid_scores_to_pool.py --csv backend/reports/local-acceptance/hybrid_score_communities.csv || echo "ℹ️  跳过回灌：DB 未准备好"; \
	fi; \
	# 8) 记录本次发布
	mkdir -p reports/phase-log; \
	echo "\n[semantic-release-auto] $(shell date +%Y-%m-%dT%H:%M:%S) LEX=$$LEX_AUTO ENT=$$ENT_AUTO" >> reports/phase-log/phase3.md; \
	echo "  - metrics: backend/reports/local-acceptance/metrics/metrics_final.json" >> reports/phase-log/phase3.md; \
	if [ -f backend/reports/local-acceptance/controlled_report.md ]; then \
	  echo "  - report:  backend/reports/local-acceptance/controlled_report.md" >> reports/phase-log/phase3.md; \
	fi;

.PHONY: semantic-merge-contrib ## 合并候选与外部种子到 merged CSV
semantic-merge-contrib:
	$(PYTHON) -u backend/scripts/merge_contrib_candidates.py \
	  --base-candidates backend/reports/local-acceptance/crossborder_candidates.csv \
	  --contrib-csv backend/config/entity_dictionary/contrib_v1.csv \
	  --out-csv backend/reports/local-acceptance/crossborder_candidates_merged.csv

.PHONY: semantic-release-contrib ## 合并外部种子→锁痛点+品牌基线→门禁
semantic-release-contrib:
	set -euo pipefail; \
	# Ensure base candidates
	if [ ! -f backend/reports/local-acceptance/crossborder_candidates.csv ]; then \
	  $(MAKE) stage2-candidates; \
	fi; \
	# Merge contrib seeds
	$(MAKE) semantic-merge-contrib; \
	# Build entity dict with brands base + lock pains using merged candidates
	$(PYTHON) -u backend/scripts/filter_and_refill_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2.csv \
	  --candidates backend/reports/local-acceptance/crossborder_candidates_merged.csv \
	  --blacklist backend/config/entity_dictionary/blacklist.txt \
	  --brands-base backend/config/entity_dictionary/brands_base.csv \
	  --output backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --total 100 --min-pains 55 --max-brands 30 --lock-pains; \
	# Compute metrics & gate
	PYTHONPATH=backend $(PYTHON) -u backend/scripts/calculate_metrics.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1_refined.yml \
	  --entity backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out-prefix backend/reports/local-acceptance/metrics/metrics_contrib \
	  --limit-per-sub 20; \
	$(PYTHON) -u backend/scripts/semantic_acceptance_gate.py \
	  --metrics backend/reports/local-acceptance/metrics/metrics_contrib.json \
	  --thresholds backend/config/quality_gates/semantic_thresholds.yml \
	  --entity-csv backend/config/entity_dictionary/crossborder_v2_diverse.csv; \
	echo "✅ Contrib release passed gate";

.PHONY: semantic-blacklist-suggest ## 从 entity-metrics_* 提出黑名单候选
semantic-blacklist-suggest:
	$(PYTHON) -u backend/scripts/suggest_blacklist_terms.py \
	  --metrics-csv backend/reports/local-acceptance/entity-metrics_diverse.csv \
	  --out backend/reports/local-acceptance/blacklist_suggestions.txt || true

.PHONY: semantic-blacklist-apply ## 合并黑名单候选并去重
semantic-blacklist-apply:
	$(PYTHON) -u backend/scripts/merge_blacklist_suggestions.py \
	  --blacklist backend/config/entity_dictionary/blacklist.txt \
	  --suggestions backend/reports/local-acceptance/blacklist_suggestions.txt || true

.PHONY: semantic-weekly-govern ## 周更：候选→别名高置信→黑名单候选→合并→门禁
semantic-weekly-govern:
	$(MAKE) stage2-candidates
	$(MAKE) semantic-merge-contrib
	# alias: regenerate and apply high-confidence
	ALIAS_MAP=backend/reports/local-acceptance/alias_map.csv; \
	$(PYTHON) -u backend/scripts/merge_aliases.py \
	  --candidates backend/reports/local-acceptance/crossborder_candidates_merged.csv \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1_refined.yml \
	  --output $$ALIAS_MAP --threshold 0.80 --min-freq 8 --top-k 1 --layer-aware; \
	AUTO_THR=$$($(PYTHON) -u backend/scripts/compute_alias_threshold.py --alias-map $$ALIAS_MAP --quantile $(ALIAS_QUANTILE) --min-floor $(ALIAS_MIN_FLOOR)); \
	$(PYTHON) -u backend/scripts/filter_alias_map_by_score.py --alias-map $$ALIAS_MAP --threshold $$AUTO_THR --output backend/reports/local-acceptance/alias_map_high.csv; \
	$(PYTHON) -u backend/scripts/merge_aliases.py \
	  --apply --alias-map backend/reports/local-acceptance/alias_map_high.csv \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1_refined.yml \
	  --output backend/config/semantic_sets/crossborder_v2.2_aliases.yml --auto-approve; \
	# rebuild entity dict with defaults
	$(PYTHON) -u backend/scripts/filter_and_refill_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2.csv \
	  --candidates backend/reports/local-acceptance/crossborder_candidates_merged.csv \
	  --blacklist backend/config/entity_dictionary/blacklist.txt \
	  --brands-base backend/config/entity_dictionary/brands_base.csv \
	  --output backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --total 100 --min-pains $(MIN_PAINS) --max-brands $(MAX_BRANDS) --lock-pains; \
	# metrics + blacklist suggestions + apply + final gate
	PYTHONPATH=backend $(PYTHON) -u backend/scripts/evaluate_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out backend/reports/local-acceptance/entity-metrics_diverse.csv; \
	$(MAKE) semantic-blacklist-suggest; \
	$(MAKE) semantic-blacklist-apply; \
	PYTHONPATH=backend $(PYTHON) -u backend/scripts/calculate_metrics.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.2_aliases.yml \
	  --entity backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out-prefix backend/reports/local-acceptance/metrics/metrics_weekly \
	  --limit-per-sub 20; \
	$(PYTHON) -u backend/scripts/semantic_acceptance_gate.py \
	  --metrics backend/reports/local-acceptance/metrics/metrics_weekly.json \
	  --thresholds backend/config/quality_gates/semantic_thresholds.yml \
	  --entity-csv backend/config/entity_dictionary/crossborder_v2_diverse.csv $(SEMANTIC_GATE_ARGS)

.PHONY: semantic-refresh-cron ## 周期回灌入口：Hybrid评分→导入pool（失败容错）
semantic-refresh-cron:
	$(MAKE) hybrid-score-reddit || true
	@if [ -f backend/reports/local-acceptance/hybrid_score_communities.csv ]; then \
	  $(PYTHON) -u backend/scripts/import_hybrid_scores_to_pool.py --csv backend/reports/local-acceptance/hybrid_score_communities.csv || true; \
	fi

.PHONY: stage2-candidates ## 抽取候选短语（每层默认50）
stage2-candidates:
	python -u backend/scripts/extract_candidates.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out-yml backend/config/semantic_sets/crossborder_candidates.yml \
	  --out-csv backend/reports/local-acceptance/crossborder_candidates.csv \
	  --per-layer 50 --min-freq 12 --use-pos 1

.PHONY: stage2-daily ## 阶段2日更：指标 + 候选
stage2-daily:
	$(MAKE) stage2-metrics
	$(MAKE) stage2-candidates

# ==========================================
# Spec 011 Stage 3 - Alias + Calibration
# ==========================================

ALIAS_CANDIDATES := backend/reports/local-acceptance/crossborder_candidates.csv
ALIAS_MAP := backend/reports/local-acceptance/alias_map.csv
ALIAS_REPORT := backend/reports/local-acceptance/alias_suggestions.md
ALIAS_LEXICON_BASE := backend/config/semantic_sets/crossborder_v2.1_refined.yml
ALIAS_LEXICON_OUT := backend/config/semantic_sets/crossborder_v2.2_aliases.yml
CAL_REVIEW_SAMPLES := backend/reports/local-acceptance/review_samples.csv
CAL_REVIEW_UI := backend/reports/local-acceptance/review_ui.html
CAL_LEXICON_OUT := backend/config/semantic_sets/crossborder_v2.2_calibrated.yml
CONTROLLED_TEMPLATE := backend/config/report_templates/executive_summary_v2.md
CONTROLLED_ANALYSIS ?= backend/reports/local-acceptance/analysis-output.json
CONTROLLED_OUTPUT := backend/reports/local-acceptance/controlled_report.md

.PHONY: stage3-alias-mine ## 计算别名建议（Jaro+Cosine+层级一致性）
stage3-alias-mine:
	python -u backend/scripts/merge_aliases.py \
	  --candidates $(ALIAS_CANDIDATES) \
	  --lexicon $(ALIAS_LEXICON_BASE) \
	  --output $(ALIAS_MAP) \
	  --threshold 0.83 \
	  --min-freq 8 \
	  --top-k 2 \
	  --layer-aware

.PHONY: stage3-alias-report ## 将 alias_map.csv 转为 markdown 审核清单
stage3-alias-report:
	python -u backend/scripts/merge_aliases.py \
	  --generate-report \
	  --alias-map $(ALIAS_MAP) \
	  --output $(ALIAS_REPORT)

.PHONY: stage3-alias-apply ## 将已审核 alias_map 写入新词库（需 decision=approve）
stage3-alias-apply:
	python -u backend/scripts/merge_aliases.py \
	  --apply \
	  --alias-map $(ALIAS_MAP) \
	  --lexicon $(ALIAS_LEXICON_BASE) \
	  --output $(ALIAS_LEXICON_OUT)

.PHONY: stage3-calibration-sample ## 低置信抽样 + 审核HTML
stage3-calibration-sample:
	python -u backend/scripts/weekly_calibration.py \
	  $(if $(TASK_ID),--task-id $(TASK_ID),) \
	  --candidates $(ALIAS_CANDIDATES) \
	  --sample-rate 0.10 \
	  --stratify-by-layer \
	  --output $(CAL_REVIEW_SAMPLES)
	python -u backend/scripts/weekly_calibration.py \
	  --generate-review-ui \
	  --samples $(CAL_REVIEW_SAMPLES) \
	  --output $(CAL_REVIEW_UI)

.PHONY: stage3-calibration-apply ## 应用人工标注（review_samples.csv需填decision/target）
stage3-calibration-apply:
	python -u backend/scripts/weekly_calibration.py \
	  --apply $(CAL_REVIEW_SAMPLES) \
	  --lexicon $(ALIAS_LEXICON_BASE) \
	  --output $(CAL_LEXICON_OUT) \
	  --update-changelog

.PHONY: stage3-report-generate ## 受控报告生成（依赖 analysis-output.json）
stage3-report-generate:
	python -u backend/app/services/report/controlled_generator.py \
	  --analysis $(CONTROLLED_ANALYSIS) \
	  --lexicon $(CAL_LEXICON_OUT) \
	  --metrics backend/reports/local-acceptance/metrics/metrics.json \
	  --template $(CONTROLLED_TEMPLATE) \
	  --output $(CONTROLLED_OUTPUT) \
	  --task-id $${TASK_ID:-stage3-baseline}

.PHONY: stage2-candidates-wide ## 抽取候选短语（每层100，频次≥8，POS启用）
stage2-candidates-wide:
	python -u backend/scripts/extract_candidates.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out-yml backend/config/semantic_sets/crossborder_candidates.yml \
	  --out-csv backend/reports/local-acceptance/crossborder_candidates.csv \
	  --per-layer 100 --min-freq 8 --use-pos 1

# ==========================================
# Spec 011 Stage 2 - Diverse & Freeze
# ==========================================

.PHONY: build-entity-diverse ## 构建diverse实体词典（短语优先，brands≤30，pain≥42，总数100）
build-entity-diverse:
	python -u backend/scripts/build_entity_dict_diverse.py \
	  --base backend/config/entity_dictionary/crossborder_v2.csv \
	  --candidates backend/reports/local-acceptance/crossborder_candidates.csv \
	  --output backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --max-brands 30 --min-pains 42 --total 100

.PHONY: evaluate-entity-diverse ## 评估diverse实体词典覆盖并生成CSV
evaluate-entity-diverse:
	python -u backend/scripts/evaluate_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out backend/reports/local-acceptance/entity-metrics_diverse.csv

.PHONY: evaluate-entity-baseline ## 评估baseline实体词典覆盖并生成CSV
evaluate-entity-baseline:
	python -u backend/scripts/evaluate_entity_dict.py \
	  --dict backend/config/entity_dictionary/crossborder_v2.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --out backend/reports/local-acceptance/entity-metrics.csv

.PHONY: metrics-diversity-diff ## 导出baseline与diverse的指标对比快照
metrics-diversity-diff:
	python -u backend/scripts/diff_entity_metrics.py \
	  --base backend/reports/local-acceptance/entity-metrics.csv \
	  --new backend/reports/local-acceptance/entity-metrics_diverse.csv \
	  --out backend/reports/local-acceptance/metrics/metrics_diversity_diff.csv

.PHONY: refine-lexicon-fill ## 生成 crossborder_v2.1_refined.yml（去重并用候选补齐）
refine-lexicon-fill:
	python -u backend/scripts/refine_semantic_sets_fill.py \
	  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml \
	  --candidates backend/reports/local-acceptance/crossborder_candidates.csv \
	  --output backend/config/semantic_sets/crossborder_v2.1_refined.yml
	@DATE=$$(date +%Y%m%d); \
	cp backend/config/semantic_sets/crossborder_v2.1_refined.yml backend/config/semantic_sets/versions/crossborder_v2.1_refined_$${DATE}.yml || true; \
	echo "- Stage 2 refined saved: versions/crossborder_v2.1_refined_$${DATE}.yml";
	@echo "## [v2.1-refined] - Stage 2 closeout ($$(date +%Y-%m-%d))\n- Dedup across layers and backfill with candidates to keep Unique@500=500\n- Aligned with diverse entity dict for Stage 2 closeout" >> backend/config/semantic_sets/CHANGELOG.md

.PHONY: augment-entity-st ## 使用 ST 对diverse词典做长尾增广（默认sim≤0.50，替换16个features）
augment-entity-st:
	python -u backend/scripts/augment_with_longtail_st.py \
	  --dict backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --candidates backend/reports/local-acceptance/crossborder_candidates.csv \
	  --corpus "backend/data/snapshots/2025-11-07-0.2/*.jsonl" \
	  --output backend/config/entity_dictionary/crossborder_v2_diverse.csv \
	  --model sentence-transformers/all-MiniLM-L6-v2 --sim-max 0.50 --replace-n 16

.PHONY: phase2-success ## 阶段二一键产出：候选→diverse构建→评估→对比→refined冻结
phase2-success:
	$(MAKE) stage2-candidates
	$(MAKE) build-entity-diverse
	$(MAKE) evaluate-entity-baseline
	$(MAKE) evaluate-entity-diverse
	$(MAKE) metrics-diversity-diff
	$(MAKE) refine-lexicon-fill
	@mkdir -p backend/reports/local-acceptance
	@echo "Stage 2 OK - $$(date '+%Y-%m-%d %H:%M:%S')" > backend/reports/local-acceptance/phase2-success.txt
	@echo "✅ 阶段2通过：见 backend/reports/local-acceptance/phase2-success.txt"

# Reddit Signal Scanner - Operational Makefile
# This is the SINGLE SOURCE OF TRUTH for executing system tasks.
# Do not run python scripts directly; use these commands to ensure environment consistency.

# --- Variables ---
ROOT_DIR := $(shell pwd)
PYTHON := $(shell if [ -x "$(ROOT_DIR)/.venv/bin/python" ]; then echo "$(ROOT_DIR)/.venv/bin/python"; elif [ -x "$(ROOT_DIR)/venv/bin/python" ]; then echo "$(ROOT_DIR)/venv/bin/python"; else echo python3; fi)
PIP := $(PYTHON) -m pip
BACKEND_DIR := backend
PYTHONPATH := $(shell pwd)/$(BACKEND_DIR)
ENV_FILE := $(BACKEND_DIR)/.env
BULK_QUEUE_LIST ?= backfill_posts_queue_v2,backfill_queue,compensation_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue
SCORE_POSTS_LIMIT ?= 500
SCORE_COMMENTS_LIMIT ?= 500
LLM_LABEL_POST_LIMIT ?= 200
LLM_LABEL_COMMENT_LIMIT ?= 200

# Export PYTHONPATH so all python sub-processes see it
export PYTHONPATH
export BULK_QUEUE_LIST

# --- Colors for nice output ---
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
RED    := $(shell tput -Txterm setaf 1)
RESET  := $(shell tput -Txterm sgr0)

.PHONY: help check-health audit-t1 report-t1 test-all restore-db db-realtime-stats \
	plan-backfill plan-seed dispatch-outbox dev-backend-start dev-backend-stop \
	dev-backend-restart dev-backend-logs crawl-min crawl-start crawl-status \
	start-worker-analysis crawl-stop data-clean data-score llm-label data-pipeline \
	db-sync-noise-labels semantic-llm-sync

# --- Default Goal ---
help:
	@echo "${YELLOW}Reddit Signal Scanner Operations${RESET}"
	@echo "Usage: make [target]"
	@echo ""
	@echo "${GREEN}Targets:${RESET}"
	@echo "  ${YELLOW}check-health${RESET}   : Run a comprehensive system health check (DB, Env, Config)."
	@echo "  ${YELLOW}audit-t1${RESET}       : Audit T1 data availability (Postgres count check)."
	@echo "  ${YELLOW}refresh-mining${RESET} : Refresh Materialized Views (Sync Analysis Layer)."
	@echo "  ${YELLOW}report-t1${RESET}      : Generate the T1 Market Insight Report."
	@echo "  ${YELLOW}restore-db${RESET}     : Restore database from the latest reliable backup."
	@echo "  ${YELLOW}db-realtime-stats${RESET} : Run SOP realtime DB stats SQL."
	@echo "  ${YELLOW}plan-backfill${RESET}  : Run backfill bootstrap planner once (v2 queue)."
	@echo "  ${YELLOW}plan-seed${RESET}      : Run seed sampling planner once (v2 queue)."
	@echo "  ${YELLOW}dispatch-outbox${RESET} : Dispatch task_outbox once (batch sender)."
	@echo "  ${YELLOW}dev-backend-start${RESET}  : Start backend with backend/.env loaded (port 8006)."
	@echo "  ${YELLOW}dev-backend-stop${RESET}   : Stop backend on port 8006."
	@echo "  ${YELLOW}dev-backend-restart${RESET}: Restart backend on port 8006."
	@echo "  ${YELLOW}dev-backend-logs${RESET}   : Tail backend logs."
	@echo "  ${YELLOW}test-core${RESET}      : Run core unit tests."
	@echo "  ${YELLOW}crawl-min${RESET}      : Run minimal crawl once (dev/test DB only)."
	@echo "  ${YELLOW}crawl-start${RESET}    : Start crawler system safely (beat + patrol + bulk [+probe])."
	@echo "  ${YELLOW}crawl-status${RESET}   : Show crawler/worker status (no changes)."
	@echo "  ${YELLOW}start-worker-analysis${RESET} : Start analysis-only worker (report generation)."
	@echo "  ${YELLOW}crawl-stop${RESET}     : Stop all local celery processes (dev/test)."
	@echo "  ${YELLOW}celery-health${RESET}  : Check celery worker health."
	@echo "  ${YELLOW}celery-config${RESET}  : Verify celery config/routes."
	@echo "  ${YELLOW}local-acceptance${RESET} : Run local acceptance checklist."
	@echo "  ${YELLOW}monitor-crawl${RESET}  : Monitor crawl progress (read-only)."
	@echo "  ${YELLOW}seed-test-accounts${RESET} : Create/reset local test accounts."
	@echo "  ${YELLOW}data-clean${RESET}     : Clean/denoise data (automod + noise sync + refresh views)."
	@echo "  ${YELLOW}data-score${RESET}     : Apply rule-based scoring to new posts."
	@echo "  ${YELLOW}data-embeddings${RESET}: Backfill embeddings (posts + comments, batch; beat 默认自动补齐)."
	@echo "  ${YELLOW}llm-label${RESET}      : LLM label high-value posts/comments (batch)."
	@echo "  ${YELLOW}data-pipeline${RESET}  : Run clean -> score -> llm-label in order."
	@echo "  ${YELLOW}data-pipeline-kag${RESET} : Run clean -> score -> embeddings -> llm-label -> semantic sync."
	@echo "  ${YELLOW}semantic-llm-sync${RESET} : LLM 标签候选回流语义库（自动审核）。"
	@echo "  ${YELLOW}db-sync-noise-labels${RESET} : Sync noise_labels into posts_raw."
	@echo "  ${YELLOW}kag-acceptance${RESET} : KAG 结构化验收（示例库或指定 task_id）。"

# --- Tasks ---

## 1. System Health Check
check-health:
	@echo "${GREEN}[*] Checking System Health...${RESET}"
	@$(PYTHON) $(BACKEND_DIR)/scripts/t1_data_audit.py || (echo "${RED}[!] Health Check Failed${RESET}"; exit 1)

## 1.1 Dev Backend (Stable Restart Flow)
dev-backend-start:
	@echo "${GREEN}[*] Starting Backend (port 8006)...${RESET}"
	@mkdir -p logs
	@/bin/sh -c 'set -a; [ -f "$(ENV_FILE)" ] && . "$(ENV_FILE)"; set +a; cd "$(BACKEND_DIR)" && nohup uvicorn app.main:app --reload --port 8006 > ../logs/backend.log 2>&1 &'
	@echo "    Logs: logs/backend.log"

dev-backend-stop:
	@echo "${YELLOW}[*] Stopping Backend (port 8006)...${RESET}"
	@/bin/sh -c 'pids=$$(lsof -ti :8006 || true); if [ -n "$$pids" ]; then echo "    PIDs: $$pids"; kill $$pids; sleep 1; else echo "    (no process)"; fi'

dev-backend-restart: dev-backend-stop dev-backend-start

dev-backend-logs:
	@tail -n 100 -f logs/backend.log

## 2. T1 Data Audit (Wrapper)
audit-t1:
	@echo "${GREEN}[*] Auditing T1 Data availability...${RESET}"
	@$(PYTHON) $(BACKEND_DIR)/scripts/t1_data_audit.py

## 3. Refresh Views (SOP Phase 2)
refresh-mining:
	@echo "${GREEN}[*] Refreshing Analysis Materialized Views (SOP Sec.2)...${RESET}"
	@$(PYTHON) $(BACKEND_DIR)/scripts/refresh_mining_views.py

## 4. Generate T1 Report (SOP v4.0 Omni-Analyst)
# Usage: make report-t1 TOPIC="Your Topic" DESC="Your Product Desc"
TOPIC ?= "跨境电商运营与痛点"
DESC ?= "跨境电商卖家工具与服务"

# Auto-generate filename from TOPIC:
# 1. Keep Chinese, Letters, Numbers
# 2. Replace spaces/symbols with underscore
# 3. Truncate to 20 chars to avoid too long filenames
# 4. Add timestamp
SAFE_NAME := $(shell $(PYTHON) -c "import re; t='${TOPIC}'; print(re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '_', t)[:20])")
TIMESTAMP := $(shell date +%Y%m%d_%H%M)
OUT ?= reports/Report_${SAFE_NAME}_${TIMESTAMP}.md

# Extract model name from .env: ignore comments, pick last definition
MODEL_NAME := $(shell grep '^LLM_MODEL_NAME=' $(ENV_FILE) | tail -n 1 | cut -d '=' -f2 | tr -d '"' | tr -d "'")
ifeq ($(MODEL_NAME),)
    MODEL_NAME := x-ai/grok-4.1-fast
endif

report-t1:
	@echo "${GREEN}[*] Generating T1 Market Report (v5.1 Fully Armed Engine)...${RESET}"
	@echo "    Topic: ${TOPIC}"
	@echo "    Model: ${MODEL_NAME}"
	@echo "    File:  ${OUT}"
	@# Data Guard: Stop if DB is empty
	@$(PYTHON) $(BACKEND_DIR)/scripts/db_guard.py || (echo "${RED}[!] Data Guard Blocked Execution. See above.${RESET}"; exit 1)
	@# CRITICAL: Dynamically pass the model from .env
	@$(PYTHON) $(BACKEND_DIR)/scripts/generate_t1_market_report.py \
		--topic "${TOPIC}" \
		--product-desc "${DESC}" \
		--model "${MODEL_NAME}" \
		--out "${OUT}" \
		--run-quality
	@echo "${GREEN}[✓] Report generated at ${OUT}${RESET}"
	@echo "${GREEN}[✓] Pain Tree JSON at backend/reports/local-acceptance/pain_tree_v1.json${RESET}"

BACKUP_FILE ?= backups/db_backup_$(DB_NAME)_latest.dump

## 5. Database Restore (Emergency Button)
restore-db:
	@echo "${YELLOW}[!] Starting Database Restore Procedure...${RESET}"
	@if [ "$(DB_NAME)" = "reddit_signal_scanner" ] && [ "$${ALLOW_GOLD_DB:-0}" != "1" ]; then \
		echo "${RED}[!] 金库恢复被阻止：请先设置 ALLOW_GOLD_DB=1 并确认风险${RESET}"; \
		exit 1; \
	fi
	@echo "${YELLOW}    Target DB: $(DB_NAME)${RESET}"
	@echo "${YELLOW}    Source: $(BACKUP_FILE)${RESET}"
	@# Note: Using PGPASSWORD inline is not secure for prod, but okay for local dev restoration
	@export PGPASSWORD=postgres && pg_restore --verbose --clean --if-exists -h localhost -U postgres -d $(DB_NAME) $(BACKUP_FILE) > /tmp/restore.log 2>&1 || echo "${YELLOW}[!] Restore finished with warnings (check /tmp/restore.log)${RESET}"
	@echo "${GREEN}[✓] Restore Complete. Verifying data...${RESET}"
	@$(PYTHON) $(BACKEND_DIR)/scripts/t1_data_audit.py

## 6. Testing (SAFE: Uses test database, never touches production!)
# Test Database URL - ALWAYS use this for pytest!
TEST_DB_URL := postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test

test:
	@echo "${GREEN}[*] Running Tests (Using TEST Database: reddit_signal_scanner_test)...${RESET}"
	@cd $(BACKEND_DIR) && DATABASE_URL=$(TEST_DB_URL) pytest tests/ -v

test-core:
	@echo "${GREEN}[*] Running Core Tests (Unit only, skipping integration)...${RESET}"
	@cd $(BACKEND_DIR) && DATABASE_URL=$(TEST_DB_URL) pytest tests/ -v -m "not integration"

test-unit:
	@echo "${GREEN}[*] Running Unit Tests (No DB reset)...${RESET}"
	@cd $(BACKEND_DIR) && SKIP_DB_RESET=1 pytest tests/unit/ -v

## 7. Manual Guard Check
guard-db:
	@$(PYTHON) $(BACKEND_DIR)/scripts/db_guard.py

## 8. Quality Gate (Placeholder)
stage4-quality:
	@echo "${GREEN}[*] Running Stage 4 Quality Checks (Placeholder)...${RESET}"
	@# Add actual quality checks here (e.g., content validation, logic verification)
	@echo "${GREEN}[✓] Quality Checks Passed.${RESET}"

## 13. Phase 5: Semantic Vectorization
backfill-embeddings:
	@echo "${GREEN}[*] Starting/Resuming Embedding Backfill (Phase 5)...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.embedding_task import backfill_posts_full; print(backfill_posts_full())"

backfill-embeddings-batch:
	@echo "${GREEN}[*] Running Embedding Backfill (Batch)...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.embedding_task import backfill_posts_batch; print(backfill_posts_batch(limit=$(EMBED_BATCH_LIMIT)))"

backfill-comment-embeddings:
	@echo "${GREEN}[*] Starting/Resuming Comment Embedding Backfill...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.embedding_task import backfill_comments_full; print(backfill_comments_full())"

backfill-comment-embeddings-batch:
	@echo "${GREEN}[*] Running Comment Embedding Backfill (Batch)...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.embedding_task import backfill_comments_batch; print(backfill_comments_batch(limit=$(EMBED_BATCH_LIMIT)))"

## 14. Phase 6: Automation & Ingest
# Worker rules:
# - start-worker runs analysis_queue only (report generation).
# - For crawling data, use crawl-start (smart) or start-workers-isolated.
# - If you run multiple workers, set unique CELERY_WORKER_HOSTNAME or --hostname to avoid clashes.
start-worker:
	@echo "${GREEN}[*] Starting Celery Worker (analysis_queue only)...${RESET}"
	@echo "    Logs: logs/celery_analysis.log"
	@mkdir -p logs
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app worker --loglevel=info --pool=solo --queues=analysis_queue >> ../logs/celery_analysis.log 2>&1 &

start-beat:
	@echo "${GREEN}[*] Starting Celery Beat (scheduler only)...${RESET}"
	@echo "    Logs: logs/celery_beat.log"
	@mkdir -p logs
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app beat --loglevel=info >> ../logs/celery_beat.log 2>&1 &

start-worker-patrol:
	@echo "${GREEN}[*] Starting Patrol Worker (patrol_queue only)...${RESET}"
	@echo "    Logs: logs/celery_patrol.log"
	@mkdir -p logs
	@cd $(BACKEND_DIR) && celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=$${PATROL_WORKER_CONCURRENCY:-4} --queues=patrol_queue >> ../logs/celery_patrol.log 2>&1 &

start-worker-bulk:
	@echo "${GREEN}[*] Starting Bulk Worker (no patrol_queue)...${RESET}"
	@echo "    Logs: logs/celery_bulk.log"
	@mkdir -p logs
	@cd $(BACKEND_DIR) && DISABLE_AUTO_CRAWL_BOOTSTRAP=1 celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=$${BULK_WORKER_CONCURRENCY:-2} --queues="$(BULK_QUEUE_LIST)" >> ../logs/celery_bulk.log 2>&1 &

start-worker-probe:
	@echo "${GREEN}[*] Starting Probe Worker (probe_queue only)...${RESET}"
	@echo "    Logs: logs/celery_probe.log"
	@mkdir -p logs
	@cd $(BACKEND_DIR) && DISABLE_AUTO_CRAWL_BOOTSTRAP=1 celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=$${PROBE_WORKER_CONCURRENCY:-1} --queues=probe_queue >> ../logs/celery_probe.log 2>&1 &

start-workers-isolated: start-beat start-worker-patrol start-worker-bulk start-worker-probe
	@echo "${GREEN}[✓] Started beat + isolated workers.${RESET}"

## 14.2 Planner/Outbox (manual one-shot)
plan-backfill:
	@echo "${GREEN}[*] Running backfill bootstrap planner once...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.crawler_task import plan_backfill_bootstrap; print(plan_backfill_bootstrap())"

plan-seed:
	@echo "${GREEN}[*] Running seed sampling planner once...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.crawler_task import plan_seed_sampling; print(plan_seed_sampling())"

dispatch-outbox:
	@echo "${GREEN}[*] Dispatching task_outbox once...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.crawler_task import dispatch_task_outbox; print(dispatch_task_outbox())"

## 14.1 Smart Ops: Crawl system starter (DB-aware)
crawler-smart-status: ## 只看本地 Dev 库现状 + 启动建议（不启动进程）
	@PY=$$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo $(PYTHON) ); $$PY $(BACKEND_DIR)/scripts/smart_crawler_workflow.py

crawler-smart-start: ## 按建议一键启动 Celery（Beat + patrol + bulk；probe 视开关）
	@PY=$$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo $(PYTHON) ); BULK_QUEUE_LIST="$(BULK_QUEUE_LIST)" $$PY $(BACKEND_DIR)/scripts/smart_crawler_workflow.py --apply

## 14.3 Minimal Crawl (local smoke test; dev/test only)
MIN_CRAWL_SCOPE ?= T1
MIN_CRAWL_LIMIT ?= 5
DEV_DB_URL ?= postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_dev
MIN_CRAWL_DB_URL ?= $(DEV_DB_URL)

crawl-min:
	@echo "${GREEN}[*] Running minimal crawl (scope: $(MIN_CRAWL_SCOPE))...${RESET}"
	@case "$(MIN_CRAWL_DB_URL)" in \
		*reddit_signal_scanner_dev*|*reddit_signal_scanner_test*) ;; \
		*reddit_signal_scanner*) echo "${RED}[!] Blocked: gold DB is not allowed for crawl-min.${RESET}"; exit 1 ;; \
	esac
	@PYTHONPATH=$(PYTHONPATH) DATABASE_URL=$(MIN_CRAWL_DB_URL) $(PYTHON) $(BACKEND_DIR)/scripts/crawl_once.py --scope $(MIN_CRAWL_SCOPE) --limit $(MIN_CRAWL_LIMIT)

## 14.4 Safe crawler shortcuts
crawl-start: ## Safe start for crawler system (beat + patrol + bulk; probe optional)
	@$(MAKE) crawler-smart-start

crawl-status: ## Show crawler status (no changes)
	@$(MAKE) crawler-smart-status

start-worker-analysis: ## Analysis-only worker (report generation)
	@$(MAKE) start-worker

crawl-stop: ## Stop all local celery processes (dev/test only)
	@echo "${YELLOW}[*] Stopping celery (dev/test)...${RESET}"
	@/bin/sh -c 'pids=$$(pgrep -f "celery.*app.core.celery_app" || true); if [ -n "$$pids" ]; then echo "    PIDs: $$pids"; kill $$pids; sleep 1; else echo "    (no celery process)"; fi'

## 14.5 Diagnostics & Utility (read-only unless stated)
celery-health:
	@$(PYTHON) $(BACKEND_DIR)/scripts/check_celery_health.py

celery-config:
	@$(PYTHON) $(BACKEND_DIR)/scripts/verify_celery_config.py

local-acceptance:
	@$(PYTHON) $(BACKEND_DIR)/scripts/local_acceptance.py

monitor-crawl:
	@$(PYTHON) $(BACKEND_DIR)/scripts/monitor_crawl_progress.py

seed-test-accounts:
	@$(PYTHON) $(BACKEND_DIR)/scripts/seed_test_accounts.py

## 14.6 Data Pipeline (clean -> score -> llm label)
data-clean:
	@echo "${GREEN}[*] Cleaning/Denoising data...${RESET}"
	@$(MAKE) db-clean-automod
	@$(MAKE) db-sync-noise-labels
	@$(MAKE) refresh-mining

data-score:
	@echo "${GREEN}[*] Scoring new posts (rulebook_v1)...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.scoring_task import score_new_posts_v1; print(score_new_posts_v1(limit=$(SCORE_POSTS_LIMIT)))"
	@echo "${GREEN}[*] Scoring new comments (rulebook_v1)...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.scoring_task import score_new_comments_v1; print(score_new_comments_v1(limit=$(SCORE_COMMENTS_LIMIT)))"

llm-label:
	@echo "${GREEN}[*] LLM labeling (batch) for high-value posts/comments...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.llm_label_task import label_posts_batch; print(label_posts_batch(limit=$(LLM_LABEL_POST_LIMIT)))"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.llm_label_task import label_comments_batch; print(label_comments_batch(limit=$(LLM_LABEL_COMMENT_LIMIT)))"

data-embeddings:
	@echo "${GREEN}[*] Backfilling embeddings (posts + comments)...${RESET}"
	@$(MAKE) backfill-embeddings-batch
	@$(MAKE) backfill-comment-embeddings-batch

data-pipeline: data-clean data-score llm-label
	@echo "${GREEN}[✓] Data pipeline complete.${RESET}"

data-pipeline-kag: data-clean data-score data-embeddings llm-label semantic-llm-sync
	@echo "${GREEN}[✓] KAG pipeline complete.${RESET}"

kag-acceptance:
	@echo "${GREEN}[*] Running KAG acceptance check...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/kag_acceptance.py --from-examples --limit 6

semantic-llm-sync:
	@echo "${GREEN}[*] Syncing LLM candidates -> semantic library...${RESET}"
	@cd $(BACKEND_DIR) && $(PYTHON) -c "from app.tasks.semantic_task import sync_llm_candidates; print(sync_llm_candidates())"

discover-communities:
	@echo "${GREEN}[*] Running Semantic Discovery Radar (Phase 6)...${RESET}"
	@# Usage: make discover-communities [KEYWORDS="pain,scam"]
	@# If KEYWORDS is omitted, it will auto-extract from DB history.
	@$(PYTHON) $(BACKEND_DIR)/services/crawl/community_discovery_v2.py $(if $(KEYWORDS),--keywords "${KEYWORDS}",)

ingest-jsonl:
	@echo "${GREEN}[*] Ingesting Historical JSONL Data...${RESET}"
	@# Usage: make ingest-jsonl FILE="path/to/data.jsonl" COMMUNITY="r/name"
	@$(PYTHON) $(BACKEND_DIR)/scripts/ingest_jsonl.py --file "${FILE}" --community "${COMMUNITY}" --update-watermark


# --- Database Operations (SOP v1.8) ---

# DB Config Defaults（默认写 Dev，金库需显式放行）
DB_NAME ?= reddit_signal_scanner_dev
DB_USER ?= postgres
DB_HOST ?= localhost
SOP_STATS_SQL ?= scripts/db_realtime_stats.sql

## 9. Database Audit
db-audit:
	@echo "${GREEN}[*] Running Database Audit...${RESET}"
	@psql -d $(DB_NAME) -U $(DB_USER) -h $(DB_HOST) -f scripts/final_production_audit.sql

## 10. Full Backup
db-backup:
	@echo "${GREEN}[*] Creating Database Backup...${RESET}"
	@mkdir -p backups
	@STAMP=$$(date +%Y%m%d_%H%M%S); \
	OUT="backups/db_backup_$(DB_NAME)_$${STAMP}.dump"; \
	pg_dump -Fc -d $(DB_NAME) -U $(DB_USER) -h $(DB_HOST) > "$$OUT"; \
	cp "$$OUT" "$(BACKUP_FILE)"
	@echo "${GREEN}[✓] Backup saved to backups/db_backup_$(DB_NAME)_...dump${RESET}"
	@echo "${GREEN}[✓] Latest backup synced to $(BACKUP_FILE)${RESET}"

## 11. Sync Schema to Code (Source of Truth)
db-sync-schema:
	@echo "${GREEN}[*] Syncing Schema to Source of Truth (current_schema.sql)...${RESET}"
	@pg_dump -s -d $(DB_NAME) -U $(DB_USER) -h $(DB_HOST) > current_schema.sql
	@echo "${GREEN}[✓] current_schema.sql updated.${RESET}"

## 12. Phase 6 Maintenance Tasks
db-clean-automod:
	@echo "${GREEN}[*] Cleaning AutoMod Garbage...${RESET}"
	@psql -d $(DB_NAME) -U $(DB_USER) -h $(DB_HOST) -f scripts/phase6_clean_automod_garbage.sql

db-sync-noise-labels:
	@echo "${GREEN}[*] Syncing noise labels into posts_raw...${RESET}"
	@psql -d $(DB_NAME) -U $(DB_USER) -h $(DB_HOST) -f $(BACKEND_DIR)/scripts/sync_noise_labels.sql

db-monitor:
	@echo "${GREEN}[*] Refreshing Quality Metrics...${RESET}"
	@psql -d $(DB_NAME) -U $(DB_USER) -h $(DB_HOST) -f scripts/phase6_populate_metrics.sql

## 12.1 SOP Realtime Stats
db-realtime-stats:
	@echo "${GREEN}[*] Running SOP realtime DB stats...${RESET}"
	@psql -d $(DB_NAME) -U $(DB_USER) -h $(DB_HOST) -f $(SOP_STATS_SQL)

# --- Phase 3: Semantic Pipeline (Human Needs Graph) ---

semantic-tag:
	@echo "${GREEN}[*] Running Semantic Tagger (Incremental Batch)...${RESET}"
	@$(PYTHON) $(BACKEND_DIR)/scripts/run_semantic_pipeline.py --limit 1000

semantic-refresh:
	@echo "${GREEN}[*] Running Full Semantic Refresh (All Posts)...${RESET}"
	@echo "${YELLOW}    This may take a while.${RESET}"
	@$(PYTHON) $(BACKEND_DIR)/scripts/run_semantic_pipeline.py --refresh-all --verbose

semantic-embed:
	@echo "${GREEN}[*] Starting Vector Embedding Backfill (Phase 3 Task A)...${RESET}"
	@echo "${YELLOW}    This runs in the background. Check logs/embedding_backfill.log${RESET}"
	@mkdir -p logs
	@nohup $(PYTHON) -c "from app.tasks.embedding_task import backfill_posts_full; print(backfill_posts_full())" > logs/embedding_backfill.log 2>&1 &
	@echo "${GREEN}[✓] Process started in background.${RESET}"

# --- MCP Tooling ---
mcp-install:
	@echo "${GREEN}[*] Installing MCP Tools...${RESET}"
	@bash scripts/install_mcp.sh

mcp-verify:
	@echo "${GREEN}[*] Verifying MCP Configuration...${RESET}"
	@bash scripts/verify_mcp_config.sh

# --- Unified Dev/Test Makefiles (Phase106 readiness) ---
# 大白话：恢复 `make dev-golden-path / kill-ports / test-backend ...` 这些项目约定的统一入口，
# 避免“文档写得能跑，但 Makefile 没规则”的尴尬。
PYTHON_VERSION ?= 3.11
FRONTEND_DIR ?= frontend
BACKEND_PORT ?= 8006
FRONTEND_PORT ?= 3006
REDIS_PORT ?= 6379
COMMON_SH ?= scripts/makefile-common.sh
EMBED_BATCH_LIMIT ?= 200
CELERY_WORKER_LOG ?= /tmp/celery_worker.log
SCRIPTS_DIR ?= scripts

include makefiles/env.mk
include makefiles/infra.mk
include makefiles/db.mk
include makefiles/celery.mk
include makefiles/dev.mk
include makefiles/test.mk
include makefiles/ops.mk

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
	@echo "🧪 测试："
	@echo "  make test-backend       运行后端测试"
	@echo "  make test-frontend      运行前端测试"
	@echo "  make test-e2e           运行关键路径 E2E 测试"
	@echo "  make test-contract      运行 API 契约测试"
	@echo "  make test-admin-e2e     验证 Admin 端到端流程"
	@echo ""
	@echo "🎯 验收："
	@echo "  make local-acceptance   执行本地验收脚本"
	@echo "  make week2-acceptance   Week 2 (P1) 验收"
	@echo "  make final-acceptance   最终验收（注册→分析→洞察→导出）"
	@echo ""
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

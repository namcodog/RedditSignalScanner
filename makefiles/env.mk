# Environment setup and validation targets

.PHONY: env-check env-setup

env-check: ## 检查Python版本和环境配置
	@echo "==> 检查环境配置 ..."
	@echo ""
	@echo "1️⃣  Python 版本检查："
	@echo "   目标版本: Python $(PYTHON_VERSION)"
	@echo "   当前版本: $$($(PYTHON) --version 2>&1)"
	@$(PYTHON) --version 2>&1 | grep -q "$(PYTHON_VERSION)" && echo "   ✅ Python 版本正确" || (echo "   ❌ Python 版本不匹配！请使用 Python $(PYTHON_VERSION)" && exit 1)
	@echo ""
	@echo "2️⃣  系统Python版本："
	@echo "   系统Python: $$(python3 --version 2>&1)"
	@echo "   位置: $$(which python3)"
	@echo ""
	@echo "3️⃣  Homebrew Python 3.11："
	@echo "   位置: $(PYTHON)"
	@test -f $(PYTHON) && echo "   ✅ Python 3.11 已安装" || (echo "   ❌ Python 3.11 未安装！请运行: brew install python@3.11" && exit 1)
	@echo ""
	@echo "4️⃣  环境变量："
	@echo "   ENABLE_CELERY_DISPATCH=$(ENABLE_CELERY_DISPATCH)"
	@echo "   PYTHONPATH=$(PYTHONPATH)"
	@echo ""
	@echo "5️⃣  数据库连接性检查："
	@which pg_isready >/dev/null 2>&1 && pg_isready -h "$${POSTGRES_HOST:-localhost}" -p "$${POSTGRES_PORT:-5432}" || echo "   ℹ️  未找到 pg_isready，跳过低级检查"
	@which psql >/dev/null 2>&1 && psql "$$([ -n "$$DATABASE_URL" ] && echo $$DATABASE_URL | sed 's/+asyncpg//' || echo postgresql://$${POSTGRES_USER:-postgres}:$${POSTGRES_PASSWORD:-postgres}@$${POSTGRES_HOST:-localhost}:$${POSTGRES_PORT:-5432}/postgres)" -tAc "SELECT 1" >/dev/null && echo "   ✅ Postgres 可连接" || echo "   ⚠️  Postgres 未就绪或连接失败（可设置 DATABASE_URL 或 backend/.env）"
	@echo ""
	@echo "✅ 环境检查完成！"

env-setup: ## 设置开发环境（安装Python 3.11和依赖）
	@echo "==> 设置开发环境 ..."
	@echo ""
	@echo "1️⃣  检查Homebrew ..."
	@which brew > /dev/null || (echo "❌ Homebrew未安装！请访问 https://brew.sh" && exit 1)
	@echo "   ✅ Homebrew已安装"
	@echo ""
	@echo "2️⃣  安装Python 3.11 ..."
	@brew list python@3.11 > /dev/null 2>&1 || brew install python@3.11
	@echo "   ✅ Python 3.11已安装"
	@echo ""
	@echo "3️⃣  安装后端依赖 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt
	@echo "   ✅ 后端依赖已安装"
	@echo ""
	@echo "4️⃣  安装前端依赖 ..."
	@cd $(FRONTEND_DIR) && npm install
	@echo "   ✅ 前端依赖已安装"
	@echo ""
	@echo "✅ 开发环境设置完成！"

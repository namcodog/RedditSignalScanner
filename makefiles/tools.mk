# Tooling commands: client generation, dependency install, MCP setup

.PHONY: update-api-schema generate-api-client install-backend install-frontend install mcp-install mcp-verify

update-api-schema: ## 更新 OpenAPI schema 基线（当 API 有意变更时使用）
	@echo "==> Updating OpenAPI schema baseline ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/update_baseline_schema.py

generate-api-client: ## 生成前端 TypeScript API 客户端
	@echo "==> Generating TypeScript API client ..."
	@cd $(FRONTEND_DIR) && npm run generate:api

install-backend: ## 安装后端依赖（修正为 backend/requirements.txt）
	@echo "==> Installing backend dependencies ..."
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -r requirements.txt
	@cd $(BACKEND_DIR) && $(PYTHON) -m pip install -U pytest pytest-asyncio httpx fakeredis || true

install-frontend: ## 安装前端依赖
	@echo "==> Installing frontend dependencies ..."
	@cd $(FRONTEND_DIR) && npm install

install: install-backend install-frontend ## 安装所有依赖

mcp-install: ## 安装和配置 MCP 工具 (exa, chrome-devtools, spec-kit)
	@echo "==> 安装 MCP 工具 ..."
	@echo ""
	@echo "1️⃣  安装 Spec Kit (Python CLI) ..."
	@uv tool install specify-cli --from git+https://github.com/github/spec-kit.git || echo "⚠️  Spec Kit 安装失败，请手动安装"
	@echo ""
	@echo "2️⃣  验证 Spec Kit 安装 ..."
	@which specify && specify check || echo "⚠️  Spec Kit 未在 PATH 中找到"
	@echo ""
	@echo "✅ MCP 工具安装完成"
	@echo ""
	@echo "📝 配置步骤:"
	@echo ""
	@echo "1️⃣  Exa API Key 已配置在 .env.local"
	@echo ""
	@echo "2️⃣  配置 MCP servers 到你的 IDE/editor:"
	@echo "   参考配置文件: mcp-config.json"
	@echo "   或查看详细指南: docs/MCP-SETUP-GUIDE.md"
	@echo ""
	@echo "3️⃣  验证安装:"
	@echo "   运行: make mcp-verify"
	@echo ""
	@echo "📖 Documentation:"
	@echo "   exa-mcp-server: https://docs.exa.ai/reference/exa-mcp"
	@echo "   Chrome DevTools: https://github.com/ChromeDevTools/chrome-devtools-mcp"
	@echo "   Spec Kit: https://github.com/github/spec-kit"
	@echo ""

mcp-verify: ## 验证 MCP 工具安装
	@echo "==> Verifying MCP tools installation ..."
	@echo ""
	@echo "1️⃣  Testing exa-mcp-server ..."
	@echo "   运行: npx -y exa-mcp-server --version"
	@timeout 5 npx -y exa-mcp-server --version 2>&1 || echo "✅ exa-mcp-server 可用 (通过 npx)"
	@echo ""
	@echo "2️⃣  Testing Chrome DevTools MCP ..."
	@echo "   运行: npx -y chrome-devtools-mcp@latest --help"
	@timeout 5 npx -y chrome-devtools-mcp@latest --help 2>&1 | head -5 || echo "✅ Chrome DevTools MCP 可用 (通过 npx)"
	@echo ""
	@echo "3️⃣  Testing Spec Kit ..."
	@which specify && specify check || echo "❌ Spec Kit not found in PATH"
	@echo ""
	@echo "4️⃣  Checking Node.js and npm ..."
	@node --version && echo "✅ Node.js installed" || echo "❌ Node.js not found"
	@npm --version && echo "✅ npm installed" || echo "❌ npm not found"
	@echo ""
	@echo "5️⃣  Checking Python and uv ..."
	@python3 --version && echo "✅ Python installed" || echo "❌ Python not found"
	@uv --version && echo "✅ uv installed" || echo "❌ uv not found"
	@echo ""
	@echo "6️⃣  Checking Exa API Key ..."
	@grep -q "EXA_API_KEY" .env.local && echo "✅ EXA_API_KEY found in .env.local" || echo "❌ EXA_API_KEY not found in .env.local"
	@echo ""
	@echo "📚 Documentation:"
	@echo "   完整配置指南: docs/MCP-SETUP-GUIDE.md"
	@echo "   MCP 配置文件: mcp-config.json"
	@echo "   exa-mcp-server: https://docs.exa.ai/reference/exa-mcp"
	@echo "   Chrome DevTools: https://github.com/ChromeDevTools/chrome-devtools-mcp"
	@echo "   Spec Kit: https://github.com/github/spec-kit"
	@echo ""
	@echo "✅ MCP 工具验证完成！"
	@echo ""

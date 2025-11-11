# Tooling commands: client generation, dependency install, MCP setup

.PHONY: update-api-schema generate-api-client install-backend install-frontend install mcp-install mcp-verify
.PHONY: top1000-from-csv fetch-top1000 enrich-top1000 fetch-communities enrich-communities
.PHONY: discover-crossborder score-from-candidates
.PHONY: score-crossborder
.PHONY: top1000-from-csv crawler-dryrun entities-dictionary-check
.PHONY: import-crossborder-pool pool-stats
.PHONY: pool-clear pool-clear-and-freeze
.PHONY: semantic-lexicon-build score-with-semantic semantic-suggest semantic-lexicon-import semantic-batched semantic-lexicon-export semantic-calibrate semantic-fuse pool-diff crawl-health
.PHONY: entity-dictionary-export

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

top1000-from-csv: ## 将 CSV/Excel 转换为 backend/data/top1000_subreddits.json（用法: make top1000-from-csv FILE=path.csv [OUTPUT=path.json]）
	@if [ -z "$(FILE)" ]; then \
		echo "用法: make top1000-from-csv FILE=path.csv [OUTPUT=backend/data/top1000_subreddits.json]"; \
		echo "示例: make top1000-from-csv FILE=backend/data/top1000_subreddits_template.csv"; \
		exit 1; \
	fi
	@OUT=$${OUTPUT:-backend/data/top1000_subreddits.json}; \
	echo "==> 转换 $(FILE) → $$OUT ..."; \
	cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/top1000_csv_to_json.py "../$(FILE)" --output "../$$OUT"
	@echo "✅ 转换完成；请查看 $(OUTPUT)"

fetch-top1000: ## 从 reddit/best/communities 抓取 Top 1000（输出 CSV/JSON 到 backend/data/）
	@echo "==> 抓取 Top 1000 社区列表 ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/scrape_top_reddit_communities.py --limit 1000

fetch-communities: ## 通用抓取（可覆盖 LIMIT=5000 BASENAME=top5000_scraped MAXPAGES=120）
	@LIMIT=$${LIMIT:-1000}; BASENAME=$${BASENAME:-}; MP=$${MAXPAGES:-120}; \
	 echo "==> 抓取 $$LIMIT 社区列表 ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/scrape_top_reddit_communities.py --limit $$LIMIT --max-pages $$MP $$( [ -n "$$BASENAME" ] && echo --basename $$BASENAME )

enrich-top1000: ## 规则化补齐字段并生成 enriched CSV，再转换为 JSON（可覆盖 IN=... OUT=...）
	@IN=$${IN:-backend/data/top1000_scraped.csv}; OUT=$${OUT:-backend/data/top1000_enriched.csv}; \
	 echo "==> 富化字段: $$IN → $$OUT ..."; \
 	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/enrich_top1000_csv.py --input "../$$IN" --output "../$$OUT" && \
	 PYTHONPATH=. $(PYTHON) scripts/top1000_csv_to_json.py "../$$OUT" --output "../backend/data/top1000_subreddits.json"

enrich-communities: ## 富化任意 CSV（IN=backend/data/top5000_scraped.csv OUT=backend/data/top5000_enriched.csv JSONOUT=backend/data/top5000_subreddits.json）
	@IN=$${IN:-backend/data/top1000_scraped.csv}; OUT=$${OUT:-backend/data/top1000_enriched.csv}; JSONOUT=$${JSONOUT:-backend/data/top1000_subreddits.json}; \
	 echo "==> 富化字段: $$IN → $$OUT ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/enrich_top1000_csv.py --input "../$$IN" --output "../$$OUT" && \
	 PYTHONPATH=. $(PYTHON) scripts/top1000_csv_to_json.py "../$$OUT" --output "../$$JSONOUT"

score-crossborder: ## 评分：跨境四主题（LIMIT/INPUT/THEMES/TOPN/RESUME 可覆盖；RESUME=1 时断点续跑）
	@LIMIT=$${LIMIT:-5000}; IN=$${INPUT:-}; THEMES=$${THEMES:-what_to_sell,how_to_sell,where_to_sell,how_to_source}; TOPN=$${TOPN:-200}; RES=$${RESUME:-}; \
	 echo "==> 跨境社区评分: limit=$$LIMIT themes=$$THEMES topn=$$TOPN resume=$${RES:+on} ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/score_crossborder.py $$( [ -n "$$IN" ] && echo --input "../$$IN" ) --limit $$LIMIT --themes $$THEMES --topn $$TOPN $$( [ -n "$$RES" ] && echo --resume )

discover-crossborder: ## 发现：跨境候选社区（KEYWORDS=... LIMIT=10000）
	@KEYS=$${KEYWORDS:-amazon,fba,shopify,etsy,dropship,ecommerce,tiktok shop,aliexpress,walmart,etsy sellers,lazada,shopee,kickstarter,indiegogo,product research,winning product}; \
	 LIM=$${LIMIT:-10000}; \
	 echo "==> 发现跨境候选社区: keywords=[$$KEYS] limit=$$LIM ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/discover_crossborder_subreddits.py --keywords "$$KEYS" --limit $$LIM --export-csv ../backend/data/crossborder_candidates.csv --export-json ../backend/data/crossborder_candidates.json

score-from-candidates: ## 用 discover 结果评分（LIMIT/TOPN/RESUME 可覆盖；RESUME=1 时断点续跑）
	@LIM=$${LIMIT:-2000}; TOPN=$${TOPN:-200}; RES=$${RESUME:-1}; \
	 echo "==> 候选评分: limit=$$LIM topn=$$TOPN resume=$${RES:+on} ..."; \
	 $(MAKE) score-crossborder LIMIT=$$LIM INPUT=backend/data/crossborder_candidates.json THEMES=what_to_sell,how_to_sell,where_to_sell,how_to_source TOPN=$$TOPN RESUME=$$RES

score-batched: ## 分批断点续跑（更稳妥）。BATCHES="300 600 ... LIMIT" 可覆盖。
	@LIM=$${LIMIT:-1762}; TOPN=$${TOPN:-200}; \
	 echo "==> 分批评分: limit=$$LIM topn=$$TOPN (resume) ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. bash scripts/score_batched.sh --input ../backend/data/crossborder_candidates.json --limit $$LIM --topn $$TOPN

crossborder-progress: ## 快速查看当前评分进度（不打断）
	@echo "==> 进度快照"; \
	 if [ -f backend/data/top5000_subreddits_scored.csv ]; then \
	   echo -n "总表数据行: "; wc -l backend/data/top5000_subreddits_scored.csv | awk '{print $$1-1}'; \
	 else echo "总表尚未生成"; fi; \
	 for f in reports/local-acceptance/crossborder-*-top200.csv; do \
	   if [ -f "$$f" ]; then \
	     echo "$$(basename "$$f") : $$(($$(wc -l < "$$f") - 1)) rows"; \
	   fi; \
	 done

crawler-dryrun: ## 打印 crawler.yml 生效策略并保存到 reports/local-acceptance/crawler-dryrun-*.md
	@echo "==> 读取 backend/config/crawler.yml 并打印摘要 ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/crawler_dryrun.py
	@echo "✅ 输出已保存到 reports/local-acceptance/crawler-dryrun-*.md"

entities-dictionary-check: ## 校验实体词典目录结构并输出统计 JSON（reports/local-acceptance/）
	@echo "==> 检查 backend/config/entity_dictionary/*.yml ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/entities_dictionary_check.py
	@echo "✅ 结果已保存到 reports/local-acceptance/entities-dictionary-check-*.json"

import-crossborder-pool: ## 导入四张 crossborder 榜单到社区池（隔离模式主入口；不会合并 Top1000）
	@echo "==> 导入 crossborder 榜单到社区池 ..."
	@cd $(BACKEND_DIR) && DISABLE_TOP1000_BASELINE=1 PYTHONPATH=. $(PYTHON) scripts/import_toplists_to_pool.py \
	  --lists ../reports/local-acceptance/crossborder-what_to_sell-top200.csv \
	          ../reports/local-acceptance/crossborder-how_to_sell-top200.csv \
	          ../reports/local-acceptance/crossborder-where_to_sell-top200.csv \
	          ../reports/local-acceptance/crossborder-how_to_source-top200.csv \
	  --what-only-low --export-csv ../backend/reports/local-acceptance/crossborder_pool_freeze.csv
	@echo "✅ 导入完成；核对表: backend/reports/local-acceptance/crossborder_pool_freeze.csv"

pool-stats: ## 打印社区池统计（总量/优先级分布/带 crossborder 标签数量）
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/pool_stats.py

pool-clear: ## 清空社区池（可加 CACHE=1 同时清空缓存表）
	@echo "==> Clearing community_pool$${CACHE:+ and community_cache} ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/pool_clear.py $$( [ -n "$$CACHE" ] && echo --cache-too )
	@echo "✅ 已清空社区池$${CACHE:+与缓存}"

pool-clear-and-freeze: ## 一键清空并导入当前 crossborder 冻结榜单（隔离模式，禁用 Top1000 合并）
	@$(MAKE) pool-clear CACHE=1
	@$(MAKE) import-crossborder-pool
	@$(MAKE) pool-stats

semantic-lexicon-build: ## 生成语义集词库 v0（YAML + 预览CSV）
	@echo "==> 构建语义集词库 v0 ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/semantic_lexicon_build.py \
	  --output ../backend/config/semantic_sets/crossborder.yml \
	  --preview ../backend/reports/local-acceptance/semantic-lexicon-preview.csv
	@echo "✅ 词库已生成；请审阅: backend/reports/local-acceptance/semantic-lexicon-preview.csv"

score-with-semantic: ## 使用语义集词库进行语义评分（LIMIT/TOPN/POSTS_PER 可调）
	@LIM=$${LIMIT:-600}; TOPN=$${TOPN:-200}; POSTS=$${POSTS_PER:-10}; \
	 echo "==> 语义评分: limit=$$LIM posts_per=$$POSTS topn=$$TOPN ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/score_with_semantic.py --lexicon ../backend/config/semantic_sets/crossborder.yml --input ../backend/data/crossborder_candidates.json --limit $$LIM --posts-per $$POSTS --topn $$TOPN

semantic-suggest: ## 从真实帖子自动建议 pain_points 与 alias 候选（生成两张CSV）
	@PER=$${PER_THEME:-20}; POSTS=$${POSTS_PER:-10}; \
	 echo "==> 生成 pain_points 与 alias 候选: per_theme=$$PER posts_per=$$POSTS ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/semantic_suggest.py --lexicon ../backend/config/semantic_sets/crossborder.yml --per-theme $$PER --posts-per $$POSTS

semantic-lexicon-import: ## 从 CSV 导入词库（可自动填充 pain_points），示例: make semantic-lexicon-import FILE=backend/reports/local-acceptance/semantic-lexicon-v1.csv FILL=1
	@IN=$${FILE:-backend/reports/local-acceptance/semantic-lexicon-v1.csv}; FILL=$${FILL:-0}; TOP=$${PAIN_TOP:-30}; \
	 echo "==> 导入词库: $$IN (auto-fill pain=$$FILL top=$$TOP) ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/semantic_lexicon_import.py --input ../$$IN --output ../backend/config/semantic_sets/crossborder.yml $$( [ "$$FILL" = "1" ] && echo "--fill-pain --pain-top $$TOP" )
	@echo "✅ 词库已导入: backend/config/semantic_sets/crossborder.yml"

semantic-batched: ## 分批语义评分（更稳妥）。BATCHES="600 1000 1400 1762" 可覆盖。
	@LIM=$${LIMIT:-1762}; TOPN=$${TOPN:-200}; POSTS=$${POSTS_PER:-10}; BATCHES="$${BATCHES:-600 1000 1400 1762}"; \
	 echo "==> 分批语义评分: limit=$$LIM topn=$$TOPN posts_per=$$POSTS batches=$$BATCHES ..."; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. bash scripts/semantic_batched.sh --input ../backend/data/crossborder_candidates.json --limit $$LIM --topn $$TOPN --posts-per $$POSTS --batches "$$BATCHES"

semantic-lexicon-export: ## 导出当前 YAML 词库为 CSV（包含 pain_points）
	@OUT=$${OUT:-backend/reports/local-acceptance/semantic-lexicon-enriched.csv}; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/semantic_lexicon_export.py --input ../backend/config/semantic_sets/crossborder.yml --output ../$$OUT
	@echo "✅ 已导出: backend/reports/local-acceptance/semantic-lexicon-enriched.csv"

entity-dictionary-export: ## 导出实体词典为 CSV（category,term,source）
	@echo "==> 导出实体词典 ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/entity_dictionary_export.py
	@echo "✅ 已导出: backend/reports/local-acceptance/entity-dictionary-export.csv"

semantic-calibrate: ## 语义分数校准 + 置信度修正，生成 calibrated Top200
	@TOPN=$${TOPN:-200}; COV=$${MIN_COVERAGE:-0.05}; PUR=$${MIN_PURITY:-0.80}; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/semantic_calibrate.py --input ../backend/data/crossborder_semantic_scored.csv --topn $$TOPN --min-coverage $$COV --min-purity $$PUR

semantic-fuse: ## 旧/新融合，生成 fused Top200（alpha 可调，默认 0.6）
	@TOPN=$${TOPN:-200}; ALPHA=$${ALPHA:-0.6}; COV=$${MIN_COVERAGE:-0.03}; PUR=$${MIN_PURITY:-0.75}; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/semantic_fuse.py --semantic ../backend/data/crossborder_semantic_scored.csv --old ../backend/data/crossborder_candidates_scored.csv --topn $$TOPN --alpha $$ALPHA --min-coverage $$COV --min-purity $$PUR

pool-diff: ## 生成旧池 vs 语义融合池的对比清单（新增/移除/优先级变化）
	@OLD=$${OLD:-backend/reports/local-acceptance/crossborder_pool_freeze.csv}; NEW=$${NEW:-backend/reports/local-acceptance/crossborder_pool_freeze_semantic_fused.csv}; OUT=$${OUT:-backend/reports/local-acceptance/crossborder_pool_diff_semantic_fused.csv}; \
	 cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/pool_diff.py --old ../$$OLD --new ../$$NEW --output ../$$OUT
	@echo "✅ 对比清单: backend/reports/local-acceptance/crossborder_pool_diff_semantic_fused.csv"

crawl-health: ## 一键抓取健康快照（检测 Redis 热缓存、metrics、池统计，保存到 reports/）
	@bash scripts/crawl_health_snapshot.sh

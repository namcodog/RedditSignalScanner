# Acceptance flows and product-level verification

.PHONY: local-acceptance acceptance-full week2-acceptance-prepare week2-acceptance final-acceptance
.PHONY: p0-acceptance p1-acceptance phase-all runbook
.PHONY: admin-template-download admin-import-excel admin-import-history
.PHONY: admin-pool-count seed-import-json seed-json-from-excel
.PHONY: check-redis-hot metrics-daily-snapshot admin-stats
.PHONY: db-cache-stats db-crawl-metrics-latest
.PHONY: content-acceptance
.PHONY: report-communities

local-acceptance: ## 执行Phase6本地验收脚本并输出报告（需要先启动服务）
	@echo "==> 运行本地验收脚本 ..."
	@REFERENCE_TASK_ID=$$(cat reports/local-acceptance/seed_insight_task_id.txt 2>/dev/null || echo "") ; \
	LOCAL_ACCEPTANCE_EMAIL=$(LOCAL_ACCEPT_EMAIL) \
		LOCAL_ACCEPTANCE_PASSWORD=$(LOCAL_ACCEPT_PASSWORD) \
		LOCAL_ACCEPTANCE_REFERENCE_TASK_ID=$$REFERENCE_TASK_ID \
		$(PYTHON) backend/scripts/local_acceptance.py \
			--environment $(LOCAL_ACCEPT_ENV) \
			--backend-url $(LOCAL_ACCEPT_BACKEND) \
			--frontend-url $(LOCAL_ACCEPT_FRONTEND) \
			--redis-url $(LOCAL_ACCEPT_REDIS)

acceptance-full: ## 🎯 完整验收流程：清理 → 启动服务 → 运行验收测试
	@echo "=========================================="
	@echo "🎯 Spec 007 完整验收流程"
	@echo "=========================================="
	@echo ""
	@echo "步骤 1/3: 清理旧进程并启动服务..."
	@$(MAKE) dev-golden-path
	@echo ""
	@echo "步骤 2/3: 等待服务完全启动（30秒）..."
	@sleep 30
	@echo ""
	@echo "步骤 3/3: 运行验收测试..."
	@$(MAKE) local-acceptance
	@echo ""
	@echo "=========================================="
	@echo "✅ 完整验收流程完成！"
	@echo "=========================================="
	@echo ""
	@echo "📊 查看验收报告："
	@echo "   ls -lht reports/local-acceptance/ | head -5"

week2-acceptance-prepare: ## 🧹 Week 2 验收准备：清理数据 + 升级测试用户
	@bash scripts/week2_prepare.sh

week2-acceptance: ## 🎯 Week 2 (P1) 完整验收：Precision@50 + 实体识别 + 行动位
	@echo "=========================================="
	@echo "🎯 Week 2 (P1) 完整验收"
	@echo "=========================================="
	@echo ""
	@echo "验收条款："
	@echo "  1. Precision@50 ≥ 0.6"
	@echo "  2. 报告中能识别 50 个核心实体"
	@echo "  3. 报告包含行动位（问题定义/建议动作/置信度/优先级）"
	@echo ""
	@echo "步骤 1/3: 准备环境（清理数据 + 升级用户）..."
	@$(MAKE) week2-acceptance-prepare
	@echo ""
	@echo "步骤 2/3: 确认服务运行..."
	@curl -s http://localhost:$(BACKEND_PORT)/api/healthz > /dev/null || (echo "❌ 后端未运行，请先执行 make dev-golden-path" && exit 1)
	@echo "✅ 后端服务正常"
	@echo ""
	@echo "步骤 3/3: 运行验收测试..."
	@$(PYTHON) week2_acceptance.py
	@echo ""
	@echo "=========================================="
	@echo "✅ Week 2 (P1) 验收完成！"
	@echo "=========================================="
	@echo ""
	@echo "📊 查看报告："
	@echo "   任务 URL: http://localhost:3006/report/{task_id}"
	@echo "   配置文件: backend/config/scoring_rules.yaml"
	@echo "   实体词典: backend/config/entity_dictionary.yaml"

final-acceptance: ## 🎯 最终验收：产品经理独立使用完整流程（10 个步骤）
	@echo "=========================================="
	@echo "🎯 最终验收（Final）"
	@echo "=========================================="
	@echo ""
	@echo "测试场景：产品经理独立使用产品"
	@echo "  1. 注册新账号"
	@echo "  2. 登录系统"
	@echo "  3. 创建分析任务"
	@echo "  4. 等待分析完成（SSE 实时进度）"
	@echo "  5. 查看洞察卡片列表"
	@echo "  6. 点击卡片查看证据"
	@echo "  7. 点击原帖链接验证真实性"
	@echo "  8. 查看报告行动位"
	@echo "  9. 导出报告（PDF/CSV）"
	@echo " 10. 访问质量看板查看指标"
	@echo ""
	@echo "步骤 1/2: 确认服务运行..."
	@curl -s http://localhost:$(BACKEND_PORT)/api/healthz > /dev/null || (echo "❌ 后端未运行，请先执行 make dev-golden-path" && exit 1)
	@curl -s http://localhost:$(FRONTEND_PORT) > /dev/null || (echo "❌ 前端未运行，请先执行 make dev-golden-path" && exit 1)
	@echo "✅ 所有服务正常"
	@echo ""
	@echo "步骤 2/2: 运行最终验收测试..."
	@$(PYTHON) final_acceptance.py
	@echo "\n==> 运行内容质量门禁 (content-acceptance) ..."
	@$(MAKE) -s content-acceptance || echo "⚠️ 内容质量门禁未通过，请查看 reports/local-acceptance/content-acceptance-*.json"
	@echo ""
	@echo "=========================================="
	@echo "✅ 最终验收完成！"
	@echo "=========================================="
	@echo ""
	@echo "📊 建议："
	@echo "   - 保存脚本输出到 reports/phase-log/"
	@echo "   - 截图关键页面作为验收证据"

p0-acceptance: ## 📦 P0 一键验收（黄金路径 + 契约 + 最终验收），输出报告到 reports/local-acceptance/
	@echo "=========================================="
	@echo "📦 P0 一键验收"
	@echo "=========================================="
	@$(MAKE) acceptance-full
	@ts=$$(date +%Y%m%d-%H%M%S); \
	 echo "\n🧪 运行 API 契约测试 (test-contract) ..."; \
	 mkdir -p reports/local-acceptance; \
	 ($(MAKE) -s test-contract) 2>&1 | tee "reports/local-acceptance/test-contract-$$ts.log"; \
	 echo "\n🧪 运行最终验收 (final-acceptance) ..."; \
	 ($(MAKE) -s final-acceptance) 2>&1 | tee "reports/local-acceptance/final-acceptance-$$ts.log"; \
	 echo "\n✅ P0 一键验收完成；报告已保存至 reports/local-acceptance/"

p1-acceptance: ## 📦 P1 一键验收（Week 2 阈值/实体/行动位），输出报告
	@echo "=========================================="
	@echo "📦 P1 一键验收"
	@echo "=========================================="
	@ts=$$(date +%Y%m%d-%H%M%S); \
	 mkdir -p reports/local-acceptance; \
	 ($(MAKE) -s week2-acceptance) 2>&1 | tee "reports/local-acceptance/week2-acceptance-$$ts.log"; \
	 echo "\n✅ P1 一键验收完成；报告已保存至 reports/local-acceptance/"

phase-all: ## 🧩 全部阶段：P0 + P1 一键执行
	@$(MAKE) p0-acceptance && $(MAKE) p1-acceptance

runbook: ## 📖 标准跑法（团队标准）
	@echo ""
	@echo "🚀 标准跑法（团队统一）："
	@echo "1) 环境检查:    make env-check"
	@echo "2) 首次安装:    make env-setup"
	@echo "3) P0 一键验收: make p0-acceptance   # 黄金路径 + 契约 + 最终验收"
	@echo "4) P1 一键验收: make p1-acceptance   # Week2 阈值/实体/行动位"
	@echo "5) 全量执行:    make phase-all"
	@echo ""
	@echo "📂 关键输出位置: reports/local-acceptance/"
	@echo "   - local-acceptance-*.md     本地验收报告"
	@echo "   - test-contract-*.log       契约测试日志"
	@echo "   - final-acceptance-*.log    最终验收日志"
	@echo "   - week2-acceptance-*.log    Week2 验收日志"
	@echo ""

# ------------------------------------------------------------
# Admin 便捷命令（社区池 Excel 模板、导入、历史）
# ------------------------------------------------------------

admin-template-download: ## 下载 Admin 社区导入 Excel 模板到 reports/local-acceptance/community_template.xlsx
	@mkdir -p reports/local-acceptance
	@echo "==> 下载社区导入模板 ..."
	@curl -sSf "$(LOCAL_ACCEPT_BACKEND)/api/admin/communities/template" \
		--output reports/local-acceptance/community_template.xlsx \
		&& echo "✅ 模板已保存: reports/local-acceptance/community_template.xlsx" \
		|| (echo "❌ 模板下载失败；请确认后端运行在 $(LOCAL_ACCEPT_BACKEND)" && exit 1)

admin-import-excel: ## 导入社区池 Excel（用法: make admin-import-excel FILE=path.xlsx [DRY=1]）
	@if [ -z "$(FILE)" ]; then \
		echo "用法: make admin-import-excel FILE=path.xlsx [DRY=1]"; \
		echo "示例: make admin-import-excel FILE=reports/local-acceptance/community_template.xlsx DRY=1"; \
		exit 1; \
	fi
	@mkdir -p reports/local-acceptance
	@ts=$$(date +%Y%m%d-%H%M%S); \
	 echo "==> 导入社区池: $(FILE) (dry_run=$(DRY)) ..."; \
	 curl -sS -X POST "$(LOCAL_ACCEPT_BACKEND)/api/admin/communities/import?dry_run=$${DRY:-0}" \
		 -F "file=@$(FILE)" \
		 -o "reports/local-acceptance/admin-import-$${ts}.json" \
		 -H "Accept: application/json" \
		 || (echo "❌ 导入失败；请检查文件格式或后端是否运行" && exit 1); \
	 echo "✅ 导入结果: reports/local-acceptance/admin-import-$${ts}.json"

admin-import-history: ## 查看最近导入历史，保存到 reports/local-acceptance/admin-import-history-*.json
	@mkdir -p reports/local-acceptance
	@ts=$$(date +%Y%m%d-%H%M%S); \
	 curl -sS "$(LOCAL_ACCEPT_BACKEND)/api/admin/communities/import-history?limit=50" \
		 -o "reports/local-acceptance/admin-import-history-$${ts}.json" \
		 -H "Accept: application/json" \
		 || (echo "❌ 获取导入历史失败；请确认后端运行在 $(LOCAL_ACCEPT_BACKEND)" && exit 1); \
	 echo "✅ 历史记录: reports/local-acceptance/admin-import-history-$${ts}.json"

# ------------------------------------------------------------
# A阶段验证便捷命令（核对 Admin 权限与 DB 数量）
# ------------------------------------------------------------

admin-pool-count: ## 使用邮箱登录并查询社区池数量（可覆盖 EMAIL=... PASSWORD=...）
	@mkdir -p reports/local-acceptance
	@EMAIL=$${EMAIL:-$(LOCAL_ACCEPT_EMAIL)}; \
	 PASSWORD=$${PASSWORD:-$(LOCAL_ACCEPT_PASSWORD)}; \
	 BACKEND=$(LOCAL_ACCEPT_BACKEND); \
	 echo "==> Admin 登录并拉取社区池 ... ($$EMAIL)"; \
	 cd $(BACKEND_DIR) && ADMIN_EMAIL="$$EMAIL" ADMIN_PASSWORD="$$PASSWORD" BACKEND_URL="$$BACKEND" $(PYTHON) scripts/admin_pool_count.py

# ------------------------------------------------------------
# CLI 路径便捷命令（Excel→JSON、JSON→DB）
# ------------------------------------------------------------

seed-import-json: ## 从 seed_communities.json 导入到 DB（CLI 路径快捷）
	@echo "==> 导入 seed_communities.json 到数据库 ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/import_seed_to_db.py
	@echo "✅ 导入完成"

seed-json-from-excel: ## 将 Excel 转换为 backend/config/seed_communities.json（用法: make seed-json-from-excel FILE=path.xlsx）
	@if [ -z "$(FILE)" ]; then \
		echo "用法: make seed-json-from-excel FILE=path.xlsx"; \
		echo "示例: make seed-json-from-excel FILE=/path/社区筛选.xlsx"; \
		exit 1; \
	fi
	@echo "==> 从 Excel 生成 seed_communities.json ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/import_seed_communities_from_excel.py "$(FILE)" --output backend/config/seed_communities.json
	@echo "✅ 已生成: backend/config/seed_communities.json"

# ------------------------------------------------------------
# B阶段验证便捷命令（Redis 热缓存、每日指标、Admin统计）
# ------------------------------------------------------------

check-redis-hot: ## 查看 Redis 热缓存前10个键（默认DB 5，可覆盖 DB=）
	@DB=$${DB:-5}; echo "==> Redis DB $$DB 热缓存键(前10)"; redis-cli -n $$DB keys 'reddit:posts:*' | head -10

metrics-daily-snapshot: ## 拉取每日指标并保存到 reports/local-acceptance/metrics-daily-*.json
	@mkdir -p reports/local-acceptance
	@ts=$$(date +%Y%m%d-%H%M%S); \
	 curl -sS "$(LOCAL_ACCEPT_BACKEND)/api/metrics/daily" -o "reports/local-acceptance/metrics-daily-$$ts.json" \
	 || (echo "❌ 指标获取失败；请确认后端运行在 $(LOCAL_ACCEPT_BACKEND)" && exit 1); \
	 echo "✅ 指标已保存: reports/local-acceptance/metrics-daily-$$ts.json"

admin-stats: ## 使用邮箱登录并获取 Admin 仪表盘统计（EMAIL/PASSWORD 可覆盖）
	@EMAIL=$${EMAIL:-$(LOCAL_ACCEPT_EMAIL)}; \
	 PASSWORD=$${PASSWORD:-$(LOCAL_ACCEPT_PASSWORD)}; \
	 BACKEND=$(LOCAL_ACCEPT_BACKEND); \
	 echo "==> Admin 登录并获取仪表盘统计 ... ($$EMAIL)"; \
	 cd $(BACKEND_DIR) && ADMIN_EMAIL="$$EMAIL" ADMIN_PASSWORD="$$PASSWORD" BACKEND_URL="$$BACKEND" $(PYTHON) scripts/admin_fetch_stats.py

db-cache-stats: ## 查询 CommunityCache 概况并保存快照
	@echo "==> 查询 CommunityCache 概况 ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/cache_stats.py

db-crawl-metrics-latest: ## 获取 crawl_metrics 最新记录并保存快照
	@echo "==> 获取 crawl_metrics 最新记录 ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/crawl_metrics_latest.py

content-acceptance: ## 报告内容质量门禁（可单独运行），输出报告到 reports/local-acceptance/
	@echo "==> 运行内容质量门禁 ..."
	@cd $(BACKEND_DIR) && PYTHONPATH=. $(PYTHON) scripts/content_acceptance.py
	@echo "✅ 内容质量门禁已完成；查看 reports/local-acceptance/content-acceptance-*.json"

report-communities: ## 下载最近任务的报告Top社区列表（需 TASK_ID）到 reports/local-acceptance/
	@if [ -z "$(TASK_ID)" ]; then \
		echo "用法: make report-communities TASK_ID=<uuid> EMAIL=<email> PASSWORD=<pwd>"; \
		exit 1; \
	fi
	@EMAIL=$${EMAIL:-$(LOCAL_ACCEPT_EMAIL)}; PASSWORD=$${PASSWORD:-$(LOCAL_ACCEPT_PASSWORD)}; \
	 BACKEND=$(LOCAL_ACCEPT_BACKEND); \
	 echo "==> 获取报告社区清单: $(TASK_ID) ..."; \
	 ts=$$(date +%Y%m%d-%H%M%S); \
	 python - << PY || { echo "❌ 失败"; exit 1; }
import httpx, os, json, sys
BASE=os.environ.get('LOCAL_ACCEPT_BACKEND','http://localhost:8006')
EMAIL=os.environ.get('EMAIL',''); PASSWORD=os.environ.get('PASSWORD','')
TASK_ID=os.environ.get('TASK_ID','')
async def main():
  async with httpx.AsyncClient() as c:
    if EMAIL and PASSWORD:
      r=await c.post(f"{BASE}/api/auth/login",json={"email":EMAIL,"password":PASSWORD},timeout=30.0)
      tok=r.json().get('access_token')
      h={"Authorization":f"Bearer {tok}"}
    else:
      h={}
    r=await c.get(f"{BASE}/api/report/{TASK_ID}/communities",headers=h,timeout=60.0)
    r.raise_for_status()
    data=r.json()
    import pathlib
    out=pathlib.Path('reports/local-acceptance'); out.mkdir(parents=True, exist_ok=True)
    p=out/f'report-communities-{TASK_ID}.json'
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"✅ 已保存: {p}")
import asyncio; asyncio.run(main())
PY

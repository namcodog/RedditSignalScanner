# Infrastructure utilities: port cleanup and Redis helpers

.PHONY: kill-backend-port kill-frontend-port kill-celery kill-redis kill-ports
.PHONY: redis-start redis-stop redis-status redis-seed redis-purge

kill-backend-port: ## 清理后端端口 8006
	@echo "==> Killing processes on port $(BACKEND_PORT) ..."
	@lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || echo "✅ Port $(BACKEND_PORT) is free"
	@sleep 1

kill-frontend-port: ## 清理前端端口 3006
	@echo "==> Killing processes on port $(FRONTEND_PORT) ..."
	@lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || echo "✅ Port $(FRONTEND_PORT) is free"
	@sleep 1

kill-celery: ## 停止所有Celery Worker进程
	@echo "==> Killing Celery workers ..."
	@pkill -f "celery.*worker" || echo "✅ No Celery workers running"
	@sleep 1

kill-redis: ## 停止Redis服务
	@echo "==> Killing Redis server ..."
	@pkill redis-server || echo "✅ No Redis server running"
	@sleep 1

kill-ports: kill-backend-port kill-frontend-port ## 清理所有服务端口 (8006, 3006)

redis-start: ## 启动Redis服务
	@echo "==> Starting Redis server on port $(REDIS_PORT) ..."
	@redis-server --daemonize yes --port $(REDIS_PORT) || echo "⚠️  Redis可能已在运行"
	@sleep 1
	@redis-cli ping > /dev/null && echo "✅ Redis server is running" || echo "❌ Redis server failed to start"

redis-stop: kill-redis ## 停止Redis服务

redis-status: ## 检查Redis状态
	@echo "==> Checking Redis status ..."
	@redis-cli ping > /dev/null && echo "✅ Redis is running" || echo "❌ Redis is not running"
	@echo ""
	@echo "Redis 数据库键统计："
	@for db in 0 1 2 5; do \
		count=$$(redis-cli -n $$db DBSIZE | awk '{print $$2}'); \
		echo "  DB $$db: $$count keys"; \
	done

redis-seed: ## 填充测试数据到Redis（使用seed_test_data.py）
	@echo "==> Seeding test data to Redis ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed_test_data.py
	@echo "✅ Test data seeded successfully"

redis-purge: ## 清空Redis测试数据
	@echo "==> Purging test data from Redis ..."
	@cd $(BACKEND_DIR) && $(PYTHON) scripts/seed_test_data.py --purge
	@echo "✅ Test data purged successfully"

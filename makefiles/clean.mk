# Cleanup and maintenance commands

.PHONY: clean clean-pyc clean-test

clean: clean-pyc clean-test ## 清理所有生成文件

clean-pyc: ## 清理 Python 缓存文件
	@echo "==> Cleaning Python cache files ..."
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -delete
	@find . -type d -name '*.egg-info' -exec rm -rf {} +

clean-test: ## 清理测试缓存
	@echo "==> Cleaning test cache ..."
	@find . -type d -name '.pytest_cache' -exec rm -rf {} +
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@find . -type f -name '.coverage' -delete

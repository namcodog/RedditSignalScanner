# Phase F1 — 补齐服务包初始化 + 增加安全 pytest 入口（2026-03-05）

## 背景
Phase E 目录重组后，`backend/app/services/` 下部分子目录缺少 `__init__.py`，会让包导入和测试收集更脆弱。  
同时缺少一个“默认不碰数据库”的 pytest 入口脚本。

## 本次执行
1. 补齐 5 个服务子目录的包初始化文件：
   - `backend/app/services/community/__init__.py`
   - `backend/app/services/crawl/__init__.py`
   - `backend/app/services/infrastructure/__init__.py`
   - `backend/app/services/llm/__init__.py`
   - `backend/app/services/metrics/__init__.py`
2. 新增脚本：
   - `scripts/safe_pytest.sh`
   - 关键行为：强制 `SKIP_DB_RESET=1`；默认 `--co`（只收集不执行）；`--run` 时执行非 e2e 测试。
3. 设置可执行权限：
   - `chmod +x scripts/safe_pytest.sh`

## 验证
1. 目录检查：
   - `community/crawl/infrastructure/llm/metrics` 均存在 `__init__.py`（全部 ✅）。
2. 脚本验证：
   - 执行 `./scripts/safe_pytest.sh`
   - 结果：`861 tests collected / 8 skipped`，无导入错误中断。

## 统一反馈（5问）
1) 发现了什么？
- 5 个服务子目录缺包初始化文件，`safe_pytest.sh` 脚本不存在。

2) 是否需要修复？
- 需要。否则导入链路和测试入口缺乏稳定性，且容易误触数据库重置流程。

3) 精确修复方法？
- 给 5 个目录补最小 `__init__.py`；新增 `scripts/safe_pytest.sh`，强制 `SKIP_DB_RESET=1`，默认 collect-only。

4) 下一步系统性计划是什么？
- 把 `scripts/safe_pytest.sh` 纳入团队默认测试入口（文档和 Makefile 可选补充一个别名）。

5) 这次执行的价值是什么？达到了什么目的？
- 统一了“安全测试入口”，并补齐 Python 包结构，降低导入断裂和误操作数据库的风险。

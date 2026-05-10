# Phase 579 - Pytest 社区表清理根因审计与测试库硬保护

## 本阶段发现

1. `pytest` 现在仍然会清理社区表，但默认目标是 `reddit_signal_scanner_test`
   - `backend/tests/conftest.py::reset_database`
     - session 级会执行 `TRUNCATE community_cache, community_pool, ...`
   - `backend/tests/conftest.py::truncate_tables_between_tests`
     - function 级在每个测试后再次执行 `TRUNCATE community_cache, community_pool, ...`

2. 还有大量测试文件自己手写了社区表清理
   - 审计结果：`22` 个测试文件包含显式 `DELETE/TRUNCATE community_*`
   - 这说明“社区表被清掉”不只是 fixture 行为，还是测试实现习惯问题

3. 真正的高风险漏洞是：
   - 如果外部环境把 `DATABASE_URL` 指到 `reddit_signal_scanner_dev`
   - 同时又设置 `SKIP_DB_RESET=1`
   - 那 session/function 两个全局清理 fixture 会提前返回
   - 但测试文件里手写的 `DELETE/TRUNCATE community_*` 仍然会直接打到当前数据库

## 本阶段修复

### 1. 新增不可绕过的 pytest 数据库目标校验

文件：
- `backend/app/db/database_guard.py`

新增：
- `validate_pytest_database_target(database_url)`

规则：
- pytest 只能连接 `*_test` 数据库
- host 必须在测试白名单内
- 即使 `SKIP_DB_RESET=1` 也不能绕过

### 2. 在 pytest 启动入口前置硬阻断

文件：
- `backend/tests/conftest.py`

改动：
- 在 `DATABASE_URL` 默认值注入后，立即执行：
  - `validate_pytest_database_target(os.environ["DATABASE_URL"])`

效果：
- 现在只要 `DATABASE_URL` 指到 `reddit_signal_scanner_dev`
- pytest 会在 `conftest` 导入阶段直接失败
- 不会进入任何删表逻辑

### 3. 补充测试覆盖

文件：
- `backend/tests/core/test_database_guard.py`

新增验证：
- 阻断 `reddit_signal_scanner_dev`
- 允许 `reddit_signal_scanner_test`
- 阻断非白名单 host
- 放行显式 override

## 验证结果

### 正常测试

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/core/test_database_guard.py -q
```

结果：
- `8 passed`

### 误配 Dev 的阻断验证

```bash
cd backend && DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_dev SKIP_DB_RESET=1 python -m pytest tests/core/test_database_guard.py -q
```

结果：
- 在 `conftest` 导入阶段直接失败
- 报错：
  - `RuntimeError: Pytest is blocked because DATABASE_URL does not point to a *_test database: reddit_signal_scanner_dev`

## 结论

1. “pytest 会清社区表”这个行为本身仍然存在，但它应该只发生在 **test 库**
2. 以前让人感觉“跑 pytest 会把社区表清掉”，根因不是单一 fixture，而是：
   - fixture 双层清理
   - 测试文件散落的手写 `DELETE/TRUNCATE`
   - 再叠加 `SKIP_DB_RESET=1` 场景下缺乏不可绕过的 test-db 保护
3. 现在最危险的误伤 `dev` 路径已经被硬阻断

## 后续建议

1. 逐步把散落在测试文件中的 `DELETE/TRUNCATE community_*` 收敛到专用 helper/fixture
2. 区分：
   - 纯单元测试
   - 集成测试
   - 需要真实社区数据的验收测试
3. 减少“社区表全量清理”在测试体系里的默认占比，降低测试和业务表结构的耦合

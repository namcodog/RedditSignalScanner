# Phase 580 - pytest 默认社区清表主路径下线

## 本阶段目标

把“默认一跑 pytest 就清社区表”从主路径里拿掉。

目标不是只防止误伤 `dev`，而是让测试架构本身更合理：
- 默认 pytest 不再把社区表当 disposable 表
- 只有明确声明的测试，才允许清理社区相关表

## 本阶段改动

### 1. 默认 pytest 重置列表移除社区表

文件：
- `backend/tests/conftest.py`

新增常量：
- `DEFAULT_RESET_TABLES`
- `COMMUNITY_RESET_TABLES`

调整后：
- `reset_database()` 只清默认业务测试表，不再清：
  - `community_pool`
  - `community_cache`
  - `discovered_communities`
- `truncate_tables_between_tests()` 也不再默认清这些社区表

### 2. 新增显式社区重置能力

文件：
- `backend/tests/conftest.py`

新增 fixture：
- `reset_community_tables`

规则：
- 社区表清理不再是 pytest 默认行为
- 只有明确需要空社区盘的测试，才允许显式申请这条 destructive fixture

### 3. 补定向验证

文件：
- `backend/tests/core/test_community_reset_policy.py`

验证两件事：
1. 默认 pytest reset 列表里已经不再包含社区表
2. 显式社区 reset 路径仍然能正确清掉社区表

## 验证结果

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/core/test_community_reset_policy.py -q
```

结果：
- `2 passed`

补充：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/core/test_database_guard.py -q
```

结果：
- `8 passed`

## 当前结论

1. 最危险的问题已经分两层收住：
   - 误伤 `dev`：已由 Phase 579 的 pytest target guard 拦住
   - 默认清社区表：本阶段已从 pytest 主路径下线

2. 现在社区表的测试策略已经变成：
   - 默认不清
   - 需要时显式清

3. 这说明第 1 步“先取消默认清表”已经有效，不是只停留在方案上。

## 下一步

1. 开始做第 2 步：
   - 把散落在测试文件里的 `DELETE/TRUNCATE community_*` 逐步收敛进显式 fixture / helper
2. 再做第 3 步：
   - 重新分类社区相关测试
   - 把不需要空社区盘的测试从 destructive reset 依赖中挪出来

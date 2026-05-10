# Phase 255 - Top1000 废弃口径纠偏（禁止回流社区池）

执行时间: 2026-03-13

## 1. 发现了什么

- Round 3 深修时，`community_pool_loader.py` 里还保留着旧 Top1000 文件的合并逻辑。
- 这和项目之前已经确认的口径冲突：
  - **Top1000 是废弃噪音源，不是可补充的社区来源。**
- 如果继续允许 merge，就有机会把以前已经清掉的噪音社区重新拉回 `community_pool`。

## 2. 是否需要修复

- 需要，已经修掉。
- 这次不是“默认关掉”，而是直接把 Top1000 从导入链摘掉，避免以后有人再把它当补充数据源用回去。

## 3. 精确修复方法

- `backend/app/services/community/community_pool_loader.py`
  - 删除 Top1000 读取和 merge 补社区逻辑。
  - 保留 `top1000_file` 路径，仅用于观测“旧文件还在不在”。
  - 如果文件存在，只会返回：
    - `top1000_status = "deprecated_ignored"`
  - 不再修改：
    - `raw_communities`
    - `source_status`
    - `community_pool` 导入集合
- `backend/tests/services/community/test_community_pool_loader.py`
  - 原来的“Top1000 merge degraded”测试改成“Top1000 deprecated ignored”测试。
- 文档口径同步修正：
  - `系统全量审计扫描计划.md`
  - `reports/phase-log/phase253.md`
  - `reports/phase-log/phase254.md`

## 4. 验证结果

- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_pool_loader.py tests/services/community/test_community_pool_loader_full.py -q`
  - `9 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`
- 关键搜索核对：
  - `top1000_status = "deprecated_ignored"` 已生效
  - 旧的 `merge_failed / loaded_seed_only / merged` 口径已从本轮相关代码和文档移除

## 5. 这次执行的价值

- 这次是口径纠偏，不是小修小补。
- 用大白话说，就是：
  - **Top1000 这条旧噪音链已经彻底封口，不会再借着“补基线”这种名义回流污染社区数据表。**

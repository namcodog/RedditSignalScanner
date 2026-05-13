# phase1126 - Brand Intelligence R15.2 Dev DB 注册表

- 这轮达到的目的：把品牌池从只读审核包推进到主系统 Dev DB 可读的注册表。
- 当前状态变化：新增 `brand_registry / brand_mentions`，显式写入 `reddit_signal_scanner_dev`，结果为 `1655` 个品牌、`1254` 条证据 mention。
- 验证结果：幂等复跑为 `would_insert_registry_rows=0 / would_insert_mentions=0`；目标测试、mypy、`git diff --check`、JSON 校验和 Alembic head 检查均通过。
- 边界：Gold DB、小程序快照、cloud DB 和 Hotpost 发布链未写；P1/P2/P3 是自动匹配和 canonical 护栏，不是删除品牌。
- 下一步：R15.3 接入日常运营 sidecar，R15.4 做只读服务，让主系统、小程序和支线都读同一个品牌注册表。

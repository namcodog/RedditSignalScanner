# Phase 340 - 第三轮继续推进：Report Community Member Count Provider 独立化

## 1. 本轮目标

继续按第三轮“主服务变薄、边界更干净、单一真相源更硬”的节奏推进，把 `ReportService` 里一个很典型的越界口子收掉：

1. 不再让 `ReportService` 直接摸 `repository._db` 取社区人数。

## 2. 本轮完成

### 2.1 新增 community member count provider

新增：

- `backend/app/services/report/community_member_count_provider.py`

正式收了：

- `resolve_community_member_count(...)`

这层统一承接：

- 先查 DB 的社区人数
- DB 失败时 fallback 到 config
- config 也没有时回到默认 `100_000`
- 日志口径统一

大白话说：

- “社区人数怎么取”现在开始有自己的正式齿轮了，不再散在 `ReportService` 里。

### 2.2 补齐 repository 边界

修改：

- `backend/app/repositories/report_repository.py`

新增：

- `get_community_member_count(...)`

说明：

- 以前 `ReportService` 直接越过 repository 边界去摸 `repository._db.execute(...)`
- 现在改成：
  - `ReportService -> ReportRepository.get_community_member_count(...) -> DB`

大白话说：

- `ReportService` 不再直接碰 repository 的内部实现。

### 2.3 收薄 ReportService

修改：

- `backend/app/services/report/report_service.py`

结果：

- `_get_community_member_count(...)` 现在变成薄委托
- 只负责调 `resolve_community_member_count(...)`
- 不再自己：
  - import `select`
  - import `CommunityCache`
  - 直接跑 SQL
  - 自己维护 DB/config/default 三层 fallback 细节

大白话说：

- `ReportService` 又薄了一点，也更像真正的编排层了。

### 2.4 新增/更新测试

新增：

- `backend/tests/services/report/test_community_member_count_provider.py`

覆盖：

1. **优先用 DB**
2. **DB 报错时回 config**
3. **都没有时回默认 100_000**

更新：

- `backend/tests/services/report/test_report_service_member_count.py`

调整：

- `db error` 场景不再 mock `repository._db.execute`
- 改成 mock `repository.get_community_member_count`

说明：

- 测试口径也回到了当前真实边界，不再继续吃 repository 的内部字段。

## 3. 新增/修改文件

### 新增

- `backend/app/services/report/community_member_count_provider.py`
- `backend/tests/services/report/test_community_member_count_provider.py`

### 修改

- `backend/app/repositories/report_repository.py`
- `backend/app/services/report/report_service.py`
- `backend/tests/services/report/test_report_service_member_count.py`

## 4. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_community_member_count_provider.py \
  tests/services/report/test_report_service_member_count.py -q
```

结果：

- `10 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/report/community_member_count_provider.py \
  app/repositories/report_repository.py \
  app/services/report/report_service.py \
  tests/services/report/test_community_member_count_provider.py \
  tests/services/report/test_report_service_member_count.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- 通过

## 5. 本轮价值

这一轮值钱的地方，不是“又多一个 provider 文件”，而是：

1. `ReportService` 不再直接越过 repository 边界摸 `_db`
2. 报告链里“社区人数怎么取”开始只有一个正式真相源
3. 以后如果再改：
   - DB 优先
   - config fallback
   - 默认值
   - 日志口径
   就不容易再把 `ReportService` 一起拖重

大白话说：

- **这轮把报告链里一个很典型的越界口子收干净了。**

## 6. 下一步建议

第三轮继续按当前节奏推进，不换打法。下一刀建议优先继续打：

1. `facts / 报告模块` 剩余 wrapper / seam
2. `数据采集模块` 剩余 wrapper / side-effect
3. `语义 / 标签模块` 剩余 sync / import-export 接缝

原则不变：

- 主服务继续变薄
- task 壳继续变薄
- workflow / service 继续独立
- 单一真相源继续做硬

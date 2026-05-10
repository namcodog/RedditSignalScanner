# Phase 344 - 第三轮继续推进：Incremental Cold Storage Service 独立化

## 本轮目标

继续第三轮结构性打磨，把 `IncrementalCrawler._upsert_to_cold_storage()` 里还缠着的冷库 upsert 主链拆成独立 service，让 `IncrementalCrawler` 继续变薄。

## 发现的问题

- `backend/app/services/crawl/incremental_crawler.py` 里的 `_upsert_to_cold_storage()` 之前还在自己背：
  - 作者保证
  - 最新版本查询
  - `crawl_run_id / community_run_id` 注入
  - metadata 组装
  - duplicate 检查
  - 新帖插入
  - 无变化刷新
  - 版本切换插入
- 这让 `IncrementalCrawler` 继续同时承担：
  - 抓取入口
  - 冷库落地
  - duplicate 决策
  - run_id 持久化

大白话说：

- `IncrementalCrawler` 还在一边当入口，一边亲手跑完整冷库 upsert。

## 修复动作

### 1. 新增独立 service

新增：

- `backend/app/services/crawl/incremental_cold_storage_service.py`

正式收了：

- `ColdStorageUpsertInput`
- `ColdStorageUpsertDeps`
- `ColdStorageUpsertResult`
- `upsert_post_to_cold_storage(...)`

这条 service 现在统一承接：

- 作者保证
- 最新版本查询
- `run_id / community_run_id` 注入
- metadata 组装
- duplicate 判定
- 新帖插入 / 无变化刷新 / 更新插入

### 2. 收薄 IncrementalCrawler

修改：

- `backend/app/services/crawl/incremental_crawler.py`

`_upsert_to_cold_storage()` 现在改成薄委托：

1. 组装 `ColdStorageUpsertInput`
2. 组装 `ColdStorageUpsertDeps`
3. 调 `upsert_post_to_cold_storage(...)`
4. 回写 `self._crawler_run_row_ensured`
5. 返回旧的 `(is_new, is_updated)` 合同

这样旧入口口径不变，但真正的冷库主链已经回到独立齿轮里。

### 3. 补测试并锁新边界

新增：

- `backend/tests/services/crawl/test_incremental_cold_storage_service.py`

覆盖：

- `run_id / community_run_id` 元数据会稳定写进冷库
- `duplicate_mode=drop` 时会稳定早退，不写新行

继续保留并跑通现有 wrapper 合同测试：

- `backend/tests/services/crawl/test_incremental_crawler_run_id.py`

## 结果

- `IncrementalCrawler._upsert_to_cold_storage()` 不再亲手维护整条冷库 upsert 主链
- 冷库落地、duplicate 判定、run_id 持久化开始有独立真相源
- 后面再改：
  - duplicate 口径
  - metadata 字段
  - run_id 注入
  - 版本切换逻辑
  不容易再把 `IncrementalCrawler` 一起拖重

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_cold_storage_service.py \
  tests/services/crawl/test_incremental_crawler_run_id.py -q
```

结果：

- `3 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/crawl/incremental_cold_storage_service.py \
  app/services/crawl/incremental_crawler.py \
  tests/services/crawl/test_incremental_cold_storage_service.py
```

结果：

- 通过

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 当前判断

这一步是第三轮里一刀真正值钱的结构性收口：

- `IncrementalCrawler` 继续变薄
- 冷库 upsert 主链开始有独立齿轮
- 数据采集模块继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`

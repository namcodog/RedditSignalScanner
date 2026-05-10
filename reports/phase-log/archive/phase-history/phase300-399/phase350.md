# Phase 350 - 第三轮继续推进：posts_raw SCD2 trigger 修正 + dedup 旧红灯收口

## 本轮目标

把数据采集模块里这组一直反复冒头的历史问题一次收住：

- `posts_raw` 的 SCD2 trigger 合同修正
- `IncrementalCrawler` no-change duplicate 路径不再和 trigger 打架
- `test_incremental_crawler_dedup.py` 剩余 2 条旧红灯清零

大白话说：

- 不是再修一个测试，而是把“冷库版本切换”和“重复帖刷新”这两条链真正对齐成同一个真相源。

## 发现的问题

这轮真正的根因有两层。

### 1. 旧的 posts_raw SCD2 trigger 合同有历史问题

数据库里 `posts_raw` 的 `enforce_scd2_posts_raw` 触发器，之前会和应用层的版本切换逻辑互相打架。

这会导致：

- 旧版本关闭不稳定
- `is_current / valid_to` 合同不够硬
- `test_cold_storage_service_creates_new_version_on_score_change`
- `test_scd2_creates_new_version_and_expires_previous`

这类测试一直容易红。

### 2. no-change duplicate 路径自己打自己

更深的一层是：

- `backend/app/services/crawl/incremental_cold_storage_service.py`

里“帖子内容没变化”的路径，之前还在用：

- `INSERT ... ON CONFLICT DO UPDATE`

但现在 `posts_raw` 上已经有：

- `BEFORE INSERT OR UPDATE` 的 SCD2 trigger

于是同一条命令里会发生：

1. trigger 先去动当前行
2. `ON CONFLICT DO UPDATE` 又去碰同一行

最后就炸成：

- `ON CONFLICT DO UPDATE command cannot affect row a second time`

所以这不是“批里真有两条同 key”，而是：

- **重复帖无变化这条路径，用错了写法。**

## 修复动作

### 1. 新增 alembic migration，修正 posts_raw SCD2 trigger

新增：

- `backend/alembic/versions/20260317_000001_fix_posts_raw_scd2_trigger.py`

这次把 `posts_raw` 的 SCD2 trigger 重新钉成当前真实合同：

- `NEW.is_current = true` 时，先关闭同 `source/source_post_id` 的其他 current 版本
- `valid_from / valid_to` 自动补齐
- 保证 `valid_from < valid_to`

同时我已经把这个 migration 升到两套库：

- `reddit_signal_scanner_dev`
- `reddit_signal_scanner_test`

当前版本确认：

- `dev -> 20260317_000001`
- `test -> 20260317_000001`

### 2. 收正 cold storage no-change duplicate 路径

修改：

- `backend/app/services/crawl/incremental_cold_storage_service.py`

关键改动是：

- **有变化**：
  - 继续走“显式关闭旧 current + 插入新版本”
- **无变化**：
  - 不再走 `INSERT ... ON CONFLICT`
  - 改成直接 `UPDATE` 现有版本的：
    - `fetched_at`
    - `metadata`
    - `crawl_run_id / community_run_id`（若有）

大白话说：

- 新版本链继续按 SCD2 跑
- 重复帖刷新就老老实实更新现有版本
- 不再自己和 trigger 打架

### 3. 补测试，把这条合同锁住

修改：

- `backend/tests/models/test_database_constraints.py`
- `backend/tests/services/crawl/test_incremental_cold_storage_service.py`

新增锁定点：

- `test_posts_raw_current_unique`
  - 现在验证的是“旧 current 关闭后，新 current 能稳定插入”
  - 不再沿用旧世界里“第二次插入就该报错”的假设
- `test_cold_storage_service_refreshes_fetched_at_for_unchanged_post`
  - 明确锁住：
    - 无变化重复帖不会新增版本
    - 只会刷新现有版本的 `fetched_at`

## 结果

这轮收完后，数据采集模块里这组老问题终于说清楚了：

- `posts_raw` 的 SCD2 trigger 合同现在和应用层是一套口径
- 版本更新链和重复帖刷新链不再互相打架
- 之前那 2 条一直反复冒头的 dedup 旧红灯已经清零

一句大白话：

- **现在“帖子有变化”和“帖子没变化”终于各走各的正路了。**

## 验证

### dedup + cold storage 定向回归

```bash
cd backend && python -m pytest \
  tests/services/crawl/test_incremental_cold_storage_service.py \
  tests/services/crawl/test_incremental_crawler_dedup.py -q
```

结果：

- `15 passed`

### 数据库约束回归

```bash
cd backend && python -m pytest tests/models/test_database_constraints.py -q
```

结果：

- `9 passed`

### migration 版本确认

```bash
dev  -> 20260317_000001
test -> 20260317_000001
```

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 当前判断

这轮是第三轮里一刀很值钱的“老债收口”：

- 不是只把测试抹绿
- 而是把 `posts_raw` 的版本合同、trigger 合同、重复帖刷新合同真正收成了一套

这对继续冲 `95+` 很关键，因为这类“底层写入合同互相打架”的问题，不收干净，后面任何结构性打磨都会反复被绊。

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`

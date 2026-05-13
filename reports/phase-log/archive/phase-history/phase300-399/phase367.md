# Phase 367 - IncrementalCrawler 内容准入链成组收口

## 1. 发现了什么？

这一步第三轮继续按“成组推进”打的是数据采集模块里还留在 `IncrementalCrawler` 身上的内容准入链：

- `backend/app/services/crawl/incremental_crawler.py`

前面虽然已经把：

- incremental/comprehensive crawl workflow
- dual write
- cold/hot storage
- runtime deps

都拆成独立齿轮了，但入口类里还散着一整组“内容准入”逻辑：

- 垃圾内容判定
- 垃圾内容批量过滤
- 内容重复查重

另外这轮定向回归还顺手照出了一个真兼容口子：

- `IncrementalRuntimeDeps` 现在会在 `IncrementalCrawler.__init__()` 里抓住 `celery_app.send_task`
- 旧测试里有一类 seam 是“先建 crawler，再 monkeypatch send_task”
- 如果把 `send_task` 抓死，这类 patch seam 会被掐断

大白话说：

- 入口类还在自己背“内容进不进系统”这整组规则
- 同时前一轮 runtime deps 抽离后，旧 patch seam 也需要补平

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增内容准入服务

新增：

- `backend/app/services/crawl/incremental_content_filter_service.py`

正式收了：

- `IncrementalSpamFilterInput`
- `IncrementalSpamFilterDeps`
- `IncrementalDuplicateLookupDeps`
- `classify_spam_post(...)`
- `filter_incremental_spam_posts(...)`
- `find_incremental_content_duplicate(...)`

现在这块统一负责：

- 作者黑名单命中
- placeholder / AmazonFC 这类硬编码模板识别
- regex + crypto 词命中
- 关键词低质量过滤
- `drop / tag / allow` 三种 spam_filter_mode
- 内容查重 lookup 委托

### 3.2 收薄 IncrementalCrawler

更新：

- `backend/app/services/crawl/incremental_crawler.py`

这次把下面三段都收成了薄委托：

- `_is_spam_post(...)`
- `_filter_spam_posts(...)`
- `_find_content_duplicate(...)`

也就是说：

- 入口类不再自己亲手维护 spam 规则和 duplicate lookup 细节
- 但旧方法名还保留着
- 这样现有测试和 patch seam 不会一下子被砍断

### 3.3 补平 runtime deps 的 patch seam

还是更新：

- `backend/app/services/crawl/incremental_crawler.py`

把：

- `send_task=celery_app.send_task`

改成了：

- `send_task=lambda task_name, *args, **kwargs: celery_app.send_task(...)`

这样就不会在初始化时把 `send_task` 抓死。
旧测试里那类“先建 crawler，再 monkeypatch celery_app.send_task”的 seam 重新恢复可用。

### 3.4 新增定向测试

新增：

- `backend/tests/services/crawl/test_incremental_content_filter_service.py`

锁住 5 件事：

- 黑名单作者 -> `Spam_Bot`
- crypto spam -> `Spam_Crypto`
- `drop` 模式会真的丢弃帖子
- `tag` 模式在 slots 限制下会正确写入 side map
- duplicate lookup 能正确透传到现有 `content_duplicate_service`

同时继续保留并跑通：

- `backend/tests/services/crawl/test_content_duplicate_service.py`
- `backend/tests/services/crawl/test_incremental_crawler_dedup.py`
- `backend/tests/services/crawl/test_incremental_cold_storage_service.py`
- `backend/tests/services/crawl/test_incremental_runtime_deps_factory.py`

## 4. 测试与验证

### 成组定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_incremental_content_filter_service.py \
  tests/services/crawl/test_content_duplicate_service.py \
  tests/services/crawl/test_incremental_crawler_dedup.py \
  tests/services/crawl/test_incremental_cold_storage_service.py \
  tests/services/crawl/test_incremental_runtime_deps_factory.py -q
```

结果：

- `25 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/incremental_content_filter_service.py \
  backend/app/services/crawl/incremental_crawler.py \
  backend/tests/services/crawl/test_incremental_content_filter_service.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `IncrementalCrawler` 里“内容到底能不能进系统”这整组规则，现在开始只有一个正式真相源了
- 后面再改：
  - spam 分类
  - spam 过滤模式
  - duplicate lookup
  - spam_category side map
  不容易再把入口类一起拖重

同时，runtime deps 那个旧 patch seam 也补平了：

- 不会因为前一轮抽离成功了，结果把现有调度/派发测试的可 patch 边界悄悄掐断

一句大白话：

- 这一步不是修一个 helper，而是把数据采集模块里“内容准不准入”这一整组规则正式抽回服务层了，而且顺手把上一轮留下的 patch seam 兼容口子也补平了。

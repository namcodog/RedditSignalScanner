# Phase 283 - 数据采集模块第一轮整治：task_outbox 状态说真话

> 时间：2026-03-15  
> 模块：数据采集模块  
> 范围：`crawler_task` 调度出队 + `comments_ingest` 测试合同对齐  
> 当前状态：已完成

---

## 1. 发现了什么？

这次从数据采集模块往下走，先盯的是调度出队这层。

查下来最明显的剩余问题是：

- `task_outbox` 只要选到了待派发任务
- 最后几乎都会返回 `status="sent"`
- 即使里面实际发生了：
  - 部分发送失败
  - target 缺失
  - 只跳过没真正发出去

这会继续让调度层看起来“正常”，但实际上是**部分成功甚至整体失败**。

一句话说：

- **这条链已经不该再用 `sent` 这种模糊状态糊过去了。**

另外，在跑整组采集模块回归时，我还发现：

- `comments_ingest` 的 2 条测试夹具停留在旧世界
- 现在 `posts_raw` 入正式表前，会先做社区映射
- 没映射的帖子会进隔离区，不会进 `posts_raw`
- 所以测试里直接插 `posts_raw` 且不补 `community_pool`，已经不再符合当前真实合同

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，也没有新增 migration。  
做的是两件事：

1. 把 `task_outbox` 的状态契约收口
2. 把 `comments_ingest` 测试夹具补到当前真实数据合同

---

## 3. 精确修复方法？

### 3.1 调度出队状态契约

修改：

- `backend/app/tasks/crawler_task.py`

新增：

- `_summarize_outbox_dispatch_status`

统一后的返回口径：

- `idle`
  - 本轮没有选到待派发任务
- `completed`
  - 选到任务了，而且没有失败项
- `degraded`
  - 有部分任务发出去了，但也有失败/异常项
- `failed`
  - 选到了任务，但这一轮一个都没成功发出去

同时补充了：

- `selected`
  - 本轮一共选了多少条 outbox 记录

这样后面看调度层，就不会再只看到一个模糊的 `sent`。

### 3.2 测试补齐

修改：

- `backend/tests/tasks/test_task_outbox_dispatcher_task.py`
- `backend/tests/services/crawl/test_comments_ingest_service.py`

新增锁定：

1. `task_outbox` 部分失败时必须返回 `degraded`
2. `task_outbox` 全部失败时必须返回 `failed`
3. `comments_ingest` 测试在插入 `posts_raw` 前，必须先补 `community_pool`
   - 因为当前真实合同里，未映射社区的帖子不会进入正式 `posts_raw`

---

## 4. 验证结果

### 采集模块定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/tasks/test_task_outbox_dispatcher_task.py \
  tests/tasks/test_crawler_fallback.py \
  tests/tasks/test_execute_target_task.py \
  tests/services/crawl/test_comments_ingest_service.py -q
```

结果：

- `27 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 5. 这次执行的价值是什么？达到了什么目的？

这一步的价值很直接：

- 调度层现在不会再把“部分成功”和“整体成功”混着说
- 数据采集模块的测试也重新对齐了当前真实数据合同

一句大白话收口：

- **这一步把采集模块里“调度说得太乐观”这件事收住了，也顺手把评论写入测试拉回了当前真实世界。**

---

## 6. 下一步系统性的计划是什么？

按总整治计划，下一步进入下一组的第一个模块：

- **语义 / 标签模块**

继续保持同一口径：

- 先看模块边界和真实价值
- 再修最影响整机闭环的那一刀

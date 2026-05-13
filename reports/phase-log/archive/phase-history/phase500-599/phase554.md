# Phase 554 - community_member_sync 切到 truth-source

## 发现了什么？

这轮又扫到一条真实 worker 入口还在读旧口径：

- `backend/app/tasks/community_member_sync_task.py`

之前它还是靠 `community_cache.is_active` 选“本轮要同步 member_count 的社区”。

这会带来一个问题：

- 只要 cache 里残留 active 行，就可能被当成正式社区进入同步
- 但这不符合我们现在的唯一真相源口径

## 是否需要修复？

需要，而且这轮已经修完。

原因很直接：

- `community_member_sync` 不是展示层
- 它会直接影响社区人数、后续排序和报告视图
- 所以不能继续让 projection 表定义正式同步资格

## 精确修复方法？

### 1. worker 选择社区改成 truth-source

`community_member_sync_task.py` 现在改成联合读取：

- `community_registry`
- `community_runtime_state`
- `community_domain_membership`
- `community_governance_decision`

正式同步资格收口成：

- `registry.is_enabled = true`
- `runtime.is_enabled = true`
- `runtime.crawl_status in ('active', 'needs_backfill')`

### 2. cache 只继续承担投影和写入目标

`community_cache` 现在不再定义“谁是正式社区”。

它在这条链路里只保留：

- cache key / 社区名字投影
- member_count 写回目标

### 3. 补回归，防止旧口径回漂

新增和调整的回归覆盖：

- truth-source 启用社区会被同步
- 只有 cache active、未进 truth-source 的社区不会被同步
- celery 任务包装层不再留下未 await warning

## 本轮代码变更

### 修改

- `backend/app/tasks/community_member_sync_task.py`
- `backend/tests/tasks/test_community_member_sync.py`

## 验证

执行：

```bash
pytest backend/tests/tasks/test_community_member_sync.py -q
```

结果：

- `6 passed`

## 下一步系统性的计划是什么？

1. 继续扫 `worker / reports / API` 里剩余旧表正式判断
2. 区分：
   - 必须切 truth-source 的正式判断
   - 可以保留的 projection / 兼容层读取
3. 继续维护社区层唯一真相源活文档，保证人和 AI 看的是同一套口径

## 这次执行的价值是什么？达到了什么目的？

这一步的价值是：

- 社区层又收掉一条真实 worker 的旧口径
- 正式社区的 member_count 同步，也开始按唯一真相源执行
- 以后不会因为 `community_cache.is_active` 残留行，把非正式社区错误同步进来

一句话总结：

现在社区层的运营入口、发现入口、warmup 抓取入口、member_count 同步入口，都在往同一套 truth-source 上收口。

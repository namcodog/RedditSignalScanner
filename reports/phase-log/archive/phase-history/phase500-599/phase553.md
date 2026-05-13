# Phase 553 - warmup crawler 社区选择切到 truth-source

## 本轮目标

继续清理社区层残留旧口径，把 `warmup_crawler` 的社区选择逻辑从 `community_pool.is_active` 切到 truth-source。

## 发现了什么？

`warmup_crawler` 里有三处正式抓取判断还在看旧表：

1. `_get_specific_community()`
2. `_get_active_communities()`
3. `_get_communities_for_batch()`

这些函数之前都把：

- `community_pool.is_active = true`

当成“这个社区应该抓”的正式依据。

这和当前社区层唯一真相源口径不一致。

## 是否需要修复？

需要。

因为 warmup crawler 不是展示层，而是真实抓取行为入口。它如果继续依赖旧 projection，就会让“社区是否应该被抓”这件事继续两套口径并存。

## 精确修复方法

新增 truth-source 选择语句：

- `community_registry`
- `community_runtime_state`
- `community_domain_membership`
- `community_governance_decision`

联合筛选条件：

- `registry.is_enabled = true`
- `runtime.is_enabled = true`
- `runtime.crawl_status in ('active', 'needs_backfill')`
- `membership.is_current = true`
- `governance.decision = approved`

然后：

- `_get_specific_community()` 改成基于 truth-source 找社区
- `_get_active_communities()` 改成基于 truth-source 找社区
- `_get_communities_for_batch()` 改成：
  - truth-source 决定“有没有资格被抓”
  - `community_cache.last_crawled_at` 只用来做排序

## 本轮代码变更

### 修改

- `backend/app/tasks/warmup_crawler.py`
- `backend/tests/tasks/test_warmup_crawler.py`

## 验证

执行：

```bash
pytest backend/tests/tasks/test_warmup_crawler.py backend/tests/tasks/test_warmup_crawler_cache.py -q
```

结果：

- `7 passed`

## 下一步系统性的计划是什么？

1. 继续扫 `worker / reports / API` 里的旧表正式判断
2. 区分：
   - 必须切 truth-source 的正式判断
   - 可以暂时保留的 projection / 历史运维工具
3. 继续维护社区层活文档，保证口径不回漂

## 这次执行的价值是什么？达到了什么目的？

这一步的价值是：

- 社区层不只是“发现入口”和“运营入口”在收口
- 连 warmup 这条真实抓取入口，也开始按同一套 truth-source 选社区

一句话总结：

现在社区层的新增、审核、过滤重复、warmup 抓取，这几条关键入口都在往同一套真相源上靠了。

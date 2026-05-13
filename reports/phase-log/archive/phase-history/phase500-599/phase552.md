# Phase 552 - discovery 已存在社区过滤切到 truth-source

## 本轮目标

继续收尾社区层残留旧口径，把 `community_discovery` 里“过滤已存在正式社区”的判断，从旧 `community_pool.is_active` 切到 truth-source。

## 发现了什么？

在社区运营写入口统一完成后，`community_discovery.discover_from_pain_keywords()` 仍然还有一处旧口径：

- 通过 `community_pool WHERE is_active = true` 判断“这个社区是不是已经在正式盘里”

这会带来两个风险：

1. discovery 链仍然依赖旧 projection 表
2. 如果 truth-source 与旧表未来再次暂时不一致，discovery 会重复发现已经启用的正式社区

## 是否需要修复？

需要。

因为这条判断属于“社区是否已正式存在”的正式判断，不应该继续依赖旧表。

## 精确修复方法

把 `discover_from_pain_keywords()` 的“existing active communities”查询改成：

- `community_registry`
- `community_runtime_state`

联合判断：

- `platform = reddit`
- `registry.is_enabled = true`
- `runtime.is_enabled = true`

这样 discovery 过滤逻辑就和当前唯一真相源保持一致。

## 本轮代码变更

### 修改

- `backend/app/services/community/community_discovery.py`
- `backend/tests/services/community/test_community_discovery_service.py`

### 新增回归

新增测试覆盖：

- 已在 truth-source 启用的社区，不应再次被 `discover_from_pain_keywords()` 当作新社区写入 `discovered_communities`

## 验证

执行：

```bash
pytest backend/tests/services/community/test_community_discovery_service.py -q
```

结果：

- `7 passed`

## 下一步系统性的计划是什么？

1. 继续扫剩余 `reports / API / worker` 里是否还有旧表直写或旧表正式判断
2. 继续把社区相关正式判断链收口到 truth-source
3. 持续维护社区层活文档，避免旧文档继续误导

## 这次执行的价值是什么？达到了什么目的？

这一步的价值不在于改了一条 SQL，而在于：

- discovery 这条“新增社区入口”也开始和唯一真相源保持一致
- 社区层的正式判断越来越少依赖旧 projection
- 后面新增社区、过滤重复社区、进入正式盘这几条链，更接近同一套系统口径

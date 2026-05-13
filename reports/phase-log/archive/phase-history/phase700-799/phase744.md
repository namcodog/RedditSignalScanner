# phase744

## 发现了什么？

- `breakdown` 的主堵点不是 materialize 脚本，而是 suggestion 聚类太死。
- 原来只按 `focus_key` 硬分组，导致很多明明共享锚点的候选被拆散，最终只长出 `1` 条 suggestion。
- 真实候选里，`paid-economics` 的两条增长帖子已经共享 `google / ads`，但因为 `focus_key` 不同，之前完全进不了 `breakdown`。

## 是否需要修复？

- 需要，而且已经实修。
- 这次不再继续补 `signal`，而是直接补 `breakdown` 供给和成团规则。

## 精确修复方法

### 代码

- `backend/app/services/hotpost/breakdown_candidate_clusterer.py`
  - `paid-economics` 纳入 `breakdown` pack 白名单
  - 不再只按单个 `focus_key` 硬切
  - 新增“同 scope + 同 pack + 共享锚点”的 pair suggestion 生成
  - 新增 subset suggestion 剪枝，避免被大组完全覆盖的小组重复出现
  - 改善 group focus key，像 `google ads` 这类双词焦点能保留下来
- `backend/tests/services/hotpost/test_breakdown_candidate_clusterer.py`
  - 新增 `paid-economics` pair 成团测试
  - 回归 listing title anchor 分组仍成立

### 验证

- `cd backend && pytest tests/services/hotpost/test_breakdown_candidate_clusterer.py tests/services/hotpost/test_breakdown_draft_materializer.py -q`
  - `8 passed`
- `python -m py_compile backend/app/services/hotpost/breakdown_candidate_clusterer.py`
  - 通过

### 真实结果

- `list_breakdown_suggestions(limit=20)`：
  - `1 -> 4`
- `python backend/scripts/hotpost/materialize_breakdown_drafts.py`
  - `materialized = 3`
  - `skipped_existing = 1`
- 新增 3 张 `breakdown draft`：
  - `draft-group-business-growth-ops-ef59fab839`
  - `draft-group-ai-automation-42998d1696`
  - `draft-group-ai-automation-bbdd9eccfb`
- 这 3 张稿已人工收成更像人话的版本并全部发布。

### 发布结果

- 已发布总卡：`99 -> 102`
- 新增发布：
  - `Google Ads 新手一发帖，评论区先涌出来的不是教程，是一堆想接单的人`
  - `做自动化代理时，大家重新算的不是功能，而是谁来背后面的维护账`
  - `AI 写代码最容易翻车的，不是写不出来，而是越写越把项目带乱`

### 当前真实窗口

- 最近 `30` 张：
  - `signal = 18`
  - `hot = 8`
  - `breakdown = 4`
- 最近 `30` 张领域：
  - `AI = 14`
  - `增长 = 10`
  - `电商 = 6`

## 下一步系统性的计划是什么？

1. 不再补 `signal`
2. 优先补 `电商`
3. 继续补 `hot`
4. 把最近 `30` 张的领域从 `14 / 10 / 6` 继续往 `10 / 10 / 10` 拉
5. 单独追分发异常：`push_mini_snapshot.py` 输出新 release，但 `latest.json` 仍显示旧 release

## 这次执行的价值是什么？

- 这次不是只把 `breakdown` 从 `1` 拉到 `4`。
- 更关键的是把 `1.0` 窗口目标第一次真正拉到了：
  - `18 / 8 / 4`
- 说明现在主系统已经能按新合同跑出结果，不再只是制度层共识。

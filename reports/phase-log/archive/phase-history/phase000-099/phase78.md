# phase78 - B 组评估与回填闭环修复

## 目标
- 让 B 组社区评估可正常执行
- B 组分流：达标进 12 个月回填，不达标停用
- 评论回填触发标签/清洗闭环

## 发现的问题 / 根因
- 评估阶段 DB 查询使用 `:days || ' days'`，asyncpg 期望字符串，导致报错
- 评估通过后插入 community_pool 缺 `description_keywords` / `semantic_quality_score`，触发 NOT NULL
- `_fetch_sample_posts` 使用 `lstrip("r/")` 导致 `r/reeftank` 变成 `eeftank`，且调用了不存在的 `get_subreddit_posts`

## 精确定位
- `backend/app/services/discovery/evaluator_service.py`

## 修复方法
- 使用 `:days * INTERVAL '1 day'` 替代字符串拼接
- 插入 community_pool 时补齐 `description_keywords` 与 `semantic_quality_score`
- 统一社区名规范化，改用 `fetch_subreddit_posts`

## 变更点
- `backend/app/services/discovery/evaluator_service.py`
- `backend/tests/services/test_evaluator_service.py`

## 运行与结果
- B 组评估结果：
  - approved：r/hvac, r/lawncare, r/automation, r/justrolledintotheshop, r/airfryer
  - rejected：r/cozyplaces, r/desksetup, r/reeftank（已 is_active=false）
- 12 个月 posts 回填（B 组 approved）
  - run_id: `c9a22fe6-1aa5-4d19-8fe6-4e4c339754e9`
  - targets: 65
- 评论样本回填（触发标签/清洗）
  - run_id: `5a09e8cf-f21f-44af-9c0a-cd0f5c346de3`
  - targets: 100

## 测试
- `python -m pytest backend/tests/services/test_evaluator_service.py`

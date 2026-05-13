# Phase 273 - P0-P2 方案验收与 Dev 库评论标签量级复算

时间：2026-03-14

## 本次目标

1. 验收 Claude 按 `P0-P2技术债执行计划.md` 落地的代码与测试状态
2. 用 Dev 库真实数据复算评论 LLM 打标签量级

## 验收命令

### 1) 定向测试

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/tasks/test_llm_label_task.py \
  tests/services/community/test_community_governance_service.py \
  tests/api/test_admin_community_pool.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/analysis/test_t1_market_agent_llm.py -q
```

结果：
- `23 passed`
- `4 failed`

失败项：

1. `tests/services/community/test_community_governance_service.py::test_build_snapshot_historical_shells_have_touch_policy`
   - 失败原因：测试 fixture 往 `community_pool.priority` 传了整数 `50`
   - 当前 schema 期望是字符串，属于测试构造参数错误，不是治理服务主逻辑失败

2. `tests/services/report/test_report_service_market_mode.py::test_report_service_market_mode_uses_market_template`
   - 仍是 phase271 里已记录的旧失败
   - 当前实际返回：`<html>demo</html>`
   - 测试仍断言应包含“执行摘要”

3. `tests/services/analysis/test_t1_market_agent_llm.py::test_t1_market_agent_uses_llm_when_premium`
4. `tests/services/analysis/test_t1_market_agent_llm.py::test_t1_market_agent_fallback_when_standard`
   - 仍是 phase271 里已记录的旧失败
   - `CommunityStat` fixture 未补齐新增参数：
     - `pain_count`
     - `solution_count`
     - `recent_posts_30d`
     - `recent_comments_30d`

### 2) 总门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：
- `27 passed`
- 通过

说明：
- P0-P2 这次改动没有打坏现有主门禁
- 但“P0-P2 计划已全部验收通过”这个说法不成立，因为上面的 4 条定向测试还没清完

## Dev 库复算

数据库：
- `reddit_signal_scanner_dev`

连接确认：

```bash
cd backend && python - <<'PY'
from app.core.config import settings
print(settings.database_url)
PY
```

结果：
- `postgresql+asyncpg://.../reddit_signal_scanner_dev`

### 1) 原始总量口径

复算结果：

| 指标 | 数量 |
|---|---:|
| 总评论数 | 2,337,416 |
| 已打标签 | 686,026 |
| 未打标签（原始） | 1,651,390 |
| 短评论过滤（body < 20） | 111,862 |
| 短评论过滤后剩余 | 1,539,528 |

说明：
- 上面 4 个数与 Claude 提供的前三项完全一致

### 2) “低分过滤 -4” 复核结果

结论：
- **没有复算出 `-4`**
- 按当前代码真实口径，短评论过滤之后：
  - `value_score <= 0` 的显式评论数：`0`
  - **没有 score 记录** 的评论数：`162,939`

也就是说：
- Claude 的 `-4` 不是当前在线任务真实口径
- 真正需要单独说明的是：有一大批评论根本没有 score 行，所以不会进入在线候选集

### 3) 全库 backlog 口径

如果按“全库未标评论，且 body>=20，且有 score 且 score>0”来算：

| 指标 | 数量 |
|---|---:|
| Phase A 规则后仍需处理（全库口径） | 1,376,589 |
| 其中按 `md5(lower(trim(body)))` 去重后的唯一文本数 | 1,341,749 |
| 去重可直接减少 | 34,840 |

说明：
- 这组数更接近“离线批量补标 backlog”
- 不是当前在线 Celery 任务一次会吃掉的量

### 4) 当前在线任务真实候选口径

按 `llm_label_task._fetch_comment_candidates()` 当前真实 SQL 口径复算：

条件：
- `lookback_days = 90`
- `business_pool IN ('core','lab')`
- `JOIN comment_scores_latest_v`
- `JOIN posts_raw (is_current = TRUE)`
- `value_score > 2.0`
- 未打标签

结果：

| 指标 | 数量 |
|---|---:|
| 90 天在线候选（规则前） | 99 |
| 90 天在线候选（短评论过滤后） | 99 |
| 90 天在线候选（按 body hash 去重后） | 99 |
| 其中 core | 4 |
| 其中 lab | 95 |

补充：
- 如果把时间范围放大到全量历史，但仍按当前在线 SQL 口径要求 `posts_raw.is_current = TRUE`：
  - 候选数：`78,033`
  - 去重后：`77,972`

## 结论

### 验收结论

- **不能算“全部验收通过”**
- 当前更准确的状态是：
  - `P0 Phase A` 规则层止血已落地，相关测试通过
  - `P0/P1 Phase B` 主逻辑已落地，但有 1 条测试 fixture 需要修正
  - `P1 Phase C` 计划中的 3 条遗留测试失败仍未修完
  - `P2 Phase D` 本次未做正式 warning 清理验收

### 数量结论

- Claude 给的前 4 个大数是对的：
  - 总评论
  - 已打标签
  - 未打标签
  - 短评论过滤量
- 但 **“低分过滤 -4” 这个数不成立**
- 当前应该分成两套口径看：

1. **离线 backlog 口径**
   - 真正大盘仍有 `1,376,589` 条
   - 去重后约 `1,341,749` 条唯一文本

2. **当前在线任务口径**
   - 真实只会碰到 `99` 条 90 天高价值候选

### 建议口径

- 不要再把 `1,539,524` 直接叫成“Phase A 后真实需打标签”
- 更准确的表达应该是：
  - `1,539,528`：只是“短评论过滤后的原始未标评论”
  - `1,376,589`：是“再扣掉无 score / 无法进入当前评分候选后的全库 backlog”
  - `99`：是“当前在线任务 90 天真实会触达的候选量”

# Phase 276 - P0 评论历史价值激活 v1 落地

> 时间：2026-03-14
> 范围：`llm_label_task` 在线增量语义收紧 + `export_llm_label_candidates.py` 历史激活导出 + 共享 prefilter
> 原则：各模块职责清楚，通过统一接口协同，彼此少牵连，整条链路顺畅可控。

---

## 1. 发现了什么？

这次真正的根问题不是“165 万评论怎么便宜打完”，而是原来的执行口径本身说错了：

- `1,651,390` 是**全库未标评论库存**
- 它不是“本轮真实需打标签量”

我先做了只读核查，确认了 3 个关键事实：

1. 如果历史离线导出硬卡 `core/lab`，当前 Dev 库只有 `78,033` 条 scored 候选，根本凑不出计划里的 `10-15 万`
2. 当前有效社区 + 近 365 天 + 规则层过滤后，真实可激活历史评论池是 `155,227`
3. 在线 `llm_label_task` 当前 90 天真实增量候选仍然很小，应该继续保持 `incremental_only`

所以这轮把口径收成：

- 在线链：只做小增量
- 离线链：做历史价值激活
- `core/lab` 对在线链是硬门槛，对离线链改成排序加分项，不再是硬门槛

---

## 2. 是否需要修复？

需要，而且已经落地。

本轮改动：

- 新增共享 prefilter：
  - `backend/app/services/llm/label_prefilter.py`
- 收紧在线评论标签任务：
  - `backend/app/tasks/llm_label_task.py`
- 改造离线导出脚本为“历史价值激活模式”：
  - `backend/scripts/report/export_llm_label_candidates.py`
- 新增/更新测试：
  - `backend/tests/services/llm/test_label_prefilter.py`
  - `backend/tests/scripts/test_export_llm_label_candidates.py`
  - `backend/tests/tasks/test_llm_label_task.py`
- 同步执行计划口径：
  - `P0-P2技术债执行计划.md`

这轮没有：

- 改数据库表结构
- 新增 migration
- 把 Codex OAuth 接进服务端运行时
- 改 `codex_batch_labeler.py` / `import_client_llm_labels.py` 主逻辑

---

## 3. 精确修复方法？

### 3.1 在线链：只保留 incremental-only

`llm_label_task.py` 现在明确带：

- `task_scope = incremental_only`

并复用共享 prefilter，统一处理：

- 短评论过滤（`<20`）
- body hash 去重
- `core/lab` 过滤
- 在线预算上限 `500`

也就是说，在线任务现在只负责：

- 新评论
- 高价值
- 小批量

不再承担历史 backlog 清理。

### 3.2 离线链：把“历史价值激活”真正做成导出能力

`export_llm_label_candidates.py` 新增：

- `--historical-activation`
- `--activation-target`
- `--activation-base-quota`
- `--activation-first-batch-size`
- `--activation-batch-size`

历史激活模式固定口径：

- 只导 `comments`
- 默认 `365 days`
- 只取当前有效社区
- 排除 `noise`
- 先做规则过滤：
  - body 长度
  - 规范化去重
- 再按 8 领域配额导出：
  - 每个领域先保底
  - 剩余额度按当前生效社区数量加权分配

### 3.3 共享 prefilter 正式成为唯一规则口径

新模块 `label_prefilter.py` 提供了：

- `normalize_comment_body`
- `build_comment_body_hash`
- `prefilter_comment_rows`
- `allocate_domain_quotas`
- `select_activation_rows`
- `build_batch_plan`

这样以后：

- 在线链
- 离线导出
- 统计口径

都能复用同一套规则，不再各写各的。

---

## 4. 下一步系统性的计划是什么？

下一步不用回头重做这轮，而是直接继续 Phase A 的剩余部分：

1. 用这套历史激活导出，跑第一批 `20,000`
2. 用现有离线链：
   - export
   - Codex OAuth
   - import
   - semantic sync
3. 看第一批实际产出：
   - 8 领域覆盖
   - pain / brand / purchase 信号非空率
   - 导入成功率
4. 再决定是否继续放量到 `120,000`

如果后面再继续做 Phase A v2，才考虑：

- 小模型层
- 更精细的价值打分
- 更长时间窗的历史扩展

---

## 5. 这次执行的价值是什么？达到了什么目的？

这次最大的价值不是“又多了个脚本参数”，而是把打标签这件事第一次说人话说清楚了：

- `165 万` 是库存，不是执行量
- 当前有效社区近 365 天、规则层过滤后，真正可激活的是 `155,227`
- 在线链继续只处理小增量
- 历史激活交给离线链

一句大白话收口：

**这轮把“全量库存焦虑”，收成了“先激活最有价值的那一层”。**

---

## 验证

### 定向测试

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_label_prefilter.py \
  tests/scripts/test_export_llm_label_candidates.py \
  tests/tasks/test_llm_label_task.py -q
```

结果：

- `10 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### Dev 库真实导出验证

```bash
cd backend && PYTHONPATH=. python scripts/report/export_llm_label_candidates.py \
  --historical-activation \
  --comments-only \
  --lookback-days 365 \
  --activation-target 5000 \
  --activation-base-quota 500 \
  --activation-first-batch-size 2500 \
  --activation-batch-size 2500 \
  --output-dir ../reports/llm-client-activation-test
```

真实输出（节选）：

- `raw_unlabeled_comments = 1,651,390`
- `raw_unlabeled_comments_window = 1,309,556`
- `eligible_comment_pool = 155,227`
- `activation_backlog = 5,000`
- `domain_distribution` 8 个领域全部有量
- `pool_distribution`：
  - `core = 4`
  - `lab = 95`
  - `unscored = 4,901`

结论：

- 历史价值激活模式已真实跑通
- 当前 Dev 库下，离线历史激活不能再用 `core/lab-only` 口径描述

# Phase 284 - 语义/标签模块第一轮整治：任务级合同统一

## 1. 发现了什么？

这轮先没有动算法本身，而是先把语义/标签模块里三条子链的“说话方式”统一：

- 语义候选抽取：`semantic_task.extract_semantic_candidates_weekly`
- LLM 候选词回流：`semantic_task.sync_llm_candidates`
- 默认补分：`scoring_task.score_new_posts_v1 / score_new_comments_v1`

之前最深的问题不是“哪条链跑不起来”，而是：

- 有的只返回 `status`
- 有的只带 `source`
- 有的只带 `score_source`
- 有的失败时会回空结果，但不说明这是哪个任务范围

这会导致下游和运维很难判断：

- 这次到底是语义候选任务、LLM 候选回流，还是默认补分任务在起作用
- 是完整成功、降级成功，还是任务失败

一句大白话：

**这个模块里几条子链都在产出结构化结果，但它们之前不是用同一种话在汇报。**

---

## 2. 是否需要修复？

需要，而且这轮已经修完。

这次修复的原则是：

- 不碰算法
- 不改库表
- 不继续把逻辑塞进更大的 God module
- 只把任务级合同统一

统一后的公共口径是：

- `status`
- `task_scope`
- `degraded_reasons`

各条子链继续保留自己的专属来源字段：

- 语义候选抽取：`extraction_source / extraction_status`
- LLM 候选回流：`candidate_source / sync_status`
- 默认补分：`score_source / score_target`

---

## 3. 精确修复方法？

### 3.1 `semantic_task.py`

新增统一 helper：

- `_with_status(...)`

固定补齐：

- `status`
- `task_scope`
- `degraded_reasons`

#### 语义候选抽取

`_run_extract_semantic_candidates()` 现在会明确区分：

- `completed`
- `degraded`：当评论库失败，退到 `posts_fallback`
- `failed`：评论库和 fallback 都失败

并补出：

- `extraction_source`
- `extraction_status`
- `extraction_error`
- `task_scope = semantic_candidate_extract`

#### LLM 候选回流

`_run_llm_candidate_sync()` 现在会明确补出：

- `candidate_source = llm_labels`
- `sync_status`
  - `no_candidates`
  - `pending_only`
  - `auto_approved_only`
  - `synced`
- `task_scope = semantic_candidate_sync`

失败时不再只剩 `sync_failed`，而是带完整任务范围。

#### 语义打标任务

`tag_post_semantics()` 和 `tag_posts_batch()` 也统一补上：

- `task_scope`
- `semantic_source = semantic_tagger`

避免这两条任务继续做“孤岛返回值”。

---

### 3.2 `scoring_task.py`

新增统一 helper：

- `_with_score_status(...)`

固定补齐：

- `status`
- `task_scope = default_score_backfill`
- `score_source = rulebook_v1_default_fill`
- `score_target = posts / comments`
- `degraded_reasons`

这样默认补分现在终于开始说清楚：

- 这是不是默认补分
- 补的是帖子还是评论
- 任务范围是什么

---

### 3.3 测试

新增/更新测试：

- `backend/tests/tasks/test_semantic_task.py`
- `backend/tests/tasks/test_scoring_task.py`

补的重点不是算法正确性，而是合同正确性：

- wrapper 会不会补齐 `task_scope`
- 失败时会不会继续说清楚任务范围
- 默认补分会不会继续明确 `score_target`

---

## 4. 这轮结果是什么？

这轮的本质不是“语义效果更准了”，而是：

**语义/标签模块里几条核心任务链，终于开始用同一种协议对外说话。**

现在这个模块的任务级合同更统一了：

- 任务做的是什么：`task_scope`
- 任务结果怎么样：`status`
- 有没有降级：`degraded_reasons`
- 具体是哪条子链：专属 source/status 字段

这更符合系统总整治的准则：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

---

## 5. 验证结果

### 定向任务合同回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/tasks/test_semantic_task.py \
  tests/tasks/test_scoring_task.py \
  tests/tasks/test_llm_label_task.py -q
```

结果：

- `11 passed`

### 更接近真实链路的补充回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/semantic/test_candidate_extractor.py \
  tests/tasks/test_semantic_task.py \
  tests/tasks/test_scoring_task.py -q
```

结果：

- `9 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 6. 下一步系统性的计划是什么？

按《系统总整治执行计划》的顺序，下一步进入：

- **分析模块**

也就是从“理解层”继续往下，开始收分析模块的职责边界、任务合同和高耦合点。

一句话：

**语义/标签模块第一轮先把任务合同说清楚了，下一轮继续往分析模块推进。**

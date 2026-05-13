# Phase 277 - P0 历史评论价值激活首批执行验证

> 时间：2026-03-14
> 范围：`20,000` 历史激活导出 + `100` 条 Codex OAuth 小样本全链路验证
> 数据库：`reddit_signal_scanner_dev`

---

## 1. 发现了什么？

这次先没有把整批 `20,000` 直接全送去 Codex，而是按更稳的节奏执行：

1. 先导出第一批 `20,000`
2. 再拿其中 `100` 条跑完整离线链
3. 确认：
   - OAuth 可用
   - prompt 可用
   - 导回 Dev 可用
   - semantic sync 可用

真实执行结果：

- 历史激活第一批导出：`20,000`
- 文件数：`4`
- 每个批次：`5,000`
- 小样本 Codex 标注：`100/100`
- 小样本导回 Dev：`100/100`
- `semantic-llm-sync`：成功

---

## 2. 是否需要修复？

这次不是修代码，而是执行验证。

不过执行里确认了一个很关键的合同事实：

- 现有 `codex_batch_labeler.py` 输出的是“瘦标签”
- 它默认不直接给出：
  - `entities`
  - `crossborder_signals`

但这次没有挡住导入，因为：

- `import_client_llm_labels.py` 会走 `_normalize_comment_analysis()`
- 缺的字段会补成默认值

所以当前结论是：

- 这条离线链能跑
- 但它输出的是“可导入、可补默认值”的 schema
- 不是“和正式在线 LLM 返回一模一样的富标签 schema”

---

## 3. 精确执行结果

### 3.1 历史激活 20,000 导出

命令：

```bash
cd backend && PYTHONPATH=. python scripts/report/export_llm_label_candidates.py \
  --historical-activation \
  --comments-only \
  --lookback-days 365 \
  --activation-target 20000 \
  --activation-base-quota 2000 \
  --activation-first-batch-size 5000 \
  --activation-batch-size 5000 \
  --output-dir ../reports/llm-client-activation-batch1
```

真实输出：

- `raw_unlabeled_comments = 1,651,390`
- `raw_unlabeled_comments_window = 1,309,551`
- `eligible_comment_pool = 155,227`
- `activation_backlog = 20,000`

8 领域分布：

- `Home_Lifestyle = 2,851`
- `Family_Parenting = 2,539`
- `Tools_EDC = 2,567`
- `Food_Coffee_Lifestyle = 2,369`
- `Minimal_Outdoor = 2,539`
- `Frugal_Living = 2,397`
- `AI_Workflow = 2,142`
- `Ecommerce_Business = 2,596`

批次计划：

- Batch 1: `5,000`
- Batch 2: `5,000`
- Batch 3: `5,000`
- Batch 4: `5,000`

### 3.2 Codex OAuth 小样本 100 条

命令：

```bash
cd backend && PYTHONPATH=. python scripts/import/codex_batch_labeler.py \
  --input ../reports/llm-client-activation-batch1/comments_activation_batch_001.jsonl \
  --output ../reports/llm-client-activation-batch1/client_llm_labels_comments_sample100.jsonl \
  --model gpt-5.3-codex \
  --reasoning low \
  --batch-size 10 \
  --rpm 20 \
  --max-items 100
```

真实结果：

- `100/100` 成功
- `0` 错误
- 总耗时约 `284s`

### 3.3 导回 Dev 库

命令：

```bash
cd backend && PYTHONPATH=. python scripts/import/import_client_llm_labels.py \
  --comments ../reports/llm-client-activation-batch1/client_llm_labels_comments_sample100.jsonl \
  --model-name gpt-5.3-codex \
  --prompt-version codex-oauth-v1
```

结果：

- `[comments] imported 100/100`

数据库核查：

- `comment_llm_labels` 中：
  - `model_name = gpt-5.3-codex`
  - `prompt_version = codex-oauth-v1`
  - 当前记录数：`100`

### 3.4 semantic sync

命令：

```bash
make semantic-llm-sync
```

结果：

```json
{"candidates": 5214, "auto_approved": 1, "pending": 5213, "status": "completed"}
```

---

## 4. 下一步系统性的计划是什么？

现在已经确认这条链：

- 导得出来
- 标得出来
- 导得回去
- semantic sync 跑得通

所以下一步就不再是“能不能跑”，而是二选一：

1. 继续把第一批 `20,000` 全量送去 Codex
2. 先抽查这 `100` 条标签质量，再决定是否放量

如果偏保守，我建议先走第 2 条。
如果偏效率，现在也已经具备直接开打 `20,000` 的条件。

---

## 5. 这次执行的价值是什么？达到了什么目的？

这次最大的价值，不是“又导出了一批 JSONL”，而是：

**我们已经把历史评论价值激活这条离线链，从“设计方案”变成了“真实能跑的执行链”。**

一句大白话收口：

- 20,000 的历史激活批次已经准备好
- 100 条小样本已经验证整条链打通
- 现在差的不是技术可行性，而是你要不要开始正式放量

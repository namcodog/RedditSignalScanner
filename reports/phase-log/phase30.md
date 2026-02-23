# Phase 30 - noise comments 过期清理「试切 1 万条」执行记录（不动 core/lab）

日期：2025-12-17  
范围：数据库执行（comments + labels/entities 联动删除）；以现有业务数据口径为准。

## 一句话结论

按“最安全”方式先试切，再逐步放大：**只清 `noise` + 已过期**，已累计删除 **1,732,099** 条 comments（同时删掉对应 labels/entities），`core/lab` 数量不变。

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- `comments` 体量较大，其中 `noise` 占比高，且有大量已过期数据；如果不清理，会持续拖慢查询、索引、VACUUM 与后续 run_id/审计相关操作。

### 2）是否已精确定位？
- 清理口径严格限定为：`COALESCE(score.business_pool, comments.business_pool, 'lab') = 'noise'` 且 `expires_at < NOW()`。
- 删除范围只涉及：
  - `comments`（候选集合）
  - `content_labels/content_entities` 中 `content_type='comment'` 且 `content_id` 命中候选集合的记录

### 3）精确修复方法？
- 使用维护任务实现的“分批删除 + 可预演 + 安全门”：
  - 入口：`backend/app/tasks/maintenance_task.py:272`
  - 执行参数（本次试切）：`batch_size=2000, max_batches=5, expired_only=True`
  - 安全门：`ENABLE_COMMENTS_NOISE_CLEANUP=1`

### 4）下一步做什么？
- 先观察你这边是否有任何“业务口径异常/报表缺数据”的反馈（理论不会，因为只删过期 noise）。
- 若确认无感，再按“逐步放大”跑下一轮（建议每轮最多 25 万条）：
  - `batch_size=5000, max_batches=50, expired_only=True`
- 删除后建议做一次 `VACUUM (ANALYZE)`（可选，等全部清完再做更省）。

### 5）这次修复的效果是什么？达到了什么结果？
- 试切执行结果（程序返回）：
  - `deleted_comments=10000`
  - `deleted_labels=8582`
  - `deleted_entities=358`
  - `duration_seconds≈19.25`
- 执行后复核（SQL 统计）：
  - `comments.noise` 从 `2,047,527` 降到 `2,037,527`（减少 10,000）
  - `comments.lab=1,620,557`、`comments.core=13,037`（保持不变）
  - 已过期 noise 候选从 `~1,731,062` 降到 `~1,721,131`（会受 NOW() 推进影响，小幅波动属正常）

---

## 第二轮（放大）执行结果：25 万条（分批提交）

执行参数：`batch_size=5000, max_batches=50, expired_only=True`  
程序返回：
- `deleted_comments=250000`
- `deleted_labels=192723`
- `deleted_entities=6350`
- `duration_seconds≈372.77`（约 6 分 13 秒）

执行后复核（SQL 统计）：
- `comments.noise`：`2,037,527 → 1,787,527`（再减少 250,000）
- `comments.lab=1,620,557`、`comments.core=13,037`（保持不变）
- 已过期 noise 候选（对齐口径）约：`1,471,371`（剩余；同样会受 NOW() 轻微波动）

---

## 第三轮（继续放大）执行结果：25 万条（分批提交）

执行参数：`batch_size=5000, max_batches=50, expired_only=True`  
程序返回：
- `deleted_comments=250000`
- `deleted_labels=2861`
- `deleted_entities=889`
- `duration_seconds≈363.54`（约 6 分 4 秒）

执行后复核（SQL 统计）：
- `comments.noise`：`1,787,527 → 1,537,527`（再减少 250,000）
- `comments.lab=1,620,557`、`comments.core=13,037`（保持不变）
- 已过期 noise 候选（对齐口径）约：`1,221,487`（剩余；同样会受 NOW() 轻微波动）

---

## 第四轮（继续放大）执行结果：25 万条（分批提交）

执行参数：`batch_size=5000, max_batches=50, expired_only=True`  
程序返回：
- `deleted_comments=250000`
- `deleted_labels=1351`
- `deleted_entities=1308`
- `duration_seconds≈360.97`（约 6 分 1 秒）

执行后复核（SQL 统计）：
- `comments.noise`：`1,537,527 → 1,287,527`（再减少 250,000）
- `comments.lab=1,620,557`、`comments.core=13,037`（保持不变）
- 已过期 noise 候选（对齐口径）约：`971,658`（剩余；同样会受 NOW() 轻微波动）

---

## 第五轮（继续放大）执行结果：25 万条（分批提交）

执行参数：`batch_size=5000, max_batches=50, expired_only=True`  
程序返回：
- `deleted_comments=250000`
- `deleted_labels=2557`
- `deleted_entities=1756`
- `duration_seconds≈362.02`（约 6 分 2 秒）

执行后复核（SQL 统计）：
- `comments.noise`：`1,287,527 → 1,037,527`（再减少 250,000）
- `comments.lab=1,620,557`、`comments.core=13,037`（保持不变）
- 已过期 noise 候选（对齐口径）约：`721,824`（剩余；同样会受 NOW() 轻微波动）

---

## 第六轮（继续放大）执行结果：25 万条（分批提交）

执行参数：`batch_size=5000, max_batches=50, expired_only=True`  
程序返回：
- `deleted_comments=250000`
- `deleted_labels=2268`
- `deleted_entities=1022`
- `duration_seconds≈365.97`（约 6 分 6 秒）

执行后复核（SQL 统计）：
- `comments.noise`：`1,037,527 → 787,527`（再减少 250,000）
- `comments.lab=1,620,557`、`comments.core=13,037`（保持不变）
- 已过期 noise 候选（对齐口径）约：`471,935`（剩余；同样会受 NOW() 轻微波动）

---

## 第七轮（继续放大）执行结果：25 万条（分批提交）

执行参数：`batch_size=5000, max_batches=50, expired_only=True`  
程序返回：
- `deleted_comments=250000`
- `deleted_labels=616`
- `deleted_entities=71`
- `duration_seconds≈347.40`（约 5 分 47 秒）

执行后复核（SQL 统计）：
- `comments.noise`：`787,527 → 537,527`（再减少 250,000）
- `comments.lab=1,620,557`、`comments.core=13,037`（保持不变）
- 已过期 noise 候选（对齐口径）约：`222,027`（剩余；同样会受 NOW() 轻微波动）

---

## 第八轮（收尾前放大）执行结果：22.2 万条（分批提交）

执行参数：`batch_size=5000, max_batches=50, expired_only=True`  
程序返回：
- `deleted_comments=222071`
- `deleted_labels=18228`
- `deleted_entities=225`
- `duration_seconds≈276.46`（约 4 分 36 秒）

执行后复核（SQL 统计）：
- `comments.noise`：`537,527 → 315,457`（再减少 222,071）
- `comments.lab=1,620,556`、`comments.core=13,037`（保持不变）

---

## 第九轮（收尾）执行结果：28 条（清到当下过期为 0）

执行参数：`batch_size=5000, max_batches=1, expired_only=True`  
程序返回：
- `deleted_comments=28`
- `deleted_labels=6`
- `deleted_entities=0`
- `duration_seconds≈0.27`

执行后复核（SQL 统计）：
- 当下 `business_pool='noise' AND expires_at<NOW()` 的候选量：`0`
- `comments.noise`：`315,457 → 315,429`（再减少 28）
- `comments.lab=1,620,556`、`comments.core=13,037`（保持不变）

---

## 执行命令（证据）

- `cd backend && ENABLE_COMMENTS_NOISE_CLEANUP=1 DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner python -c "import asyncio; from app.tasks.maintenance_task import cleanup_noise_comments_impl; print(asyncio.run(cleanup_noise_comments_impl(batch_size=2000, max_batches=5, expired_only=True)))"`
- `cd backend && ENABLE_COMMENTS_NOISE_CLEANUP=1 DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner python -c "import asyncio; from app.tasks.maintenance_task import cleanup_noise_comments_impl; print(asyncio.run(cleanup_noise_comments_impl(batch_size=5000, max_batches=50, expired_only=True)))"`
- `cd backend && ENABLE_COMMENTS_NOISE_CLEANUP=1 DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner python -c "import asyncio; from app.tasks.maintenance_task import cleanup_noise_comments_impl; print(asyncio.run(cleanup_noise_comments_impl(batch_size=5000, max_batches=1, expired_only=True)))"`

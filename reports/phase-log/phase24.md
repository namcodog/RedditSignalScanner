# Phase 24 - 修复 community_pool “发号器”失步（Sequence Out of Sync）+ 新增 AI_Workflow 社区

日期：2025-12-17  
代码基线：`main@fbc5a89`（工作区 dirty；以当前代码与现有数据为准）

## 一句话结论

**不动任何现有业务数据，只把 community_pool 的自增序列修到正确位置**，让新增社区不再撞主键；同时用“只新增、不覆盖”的方式把 AI_Workflow 相关社区补进社区池与缓存表。

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- 新增社区时报 `duplicate key value violates unique constraint "pk_community_pool"`，例如试图插入 `(id)=(9)` 但 9 已存在。
- 根因：**PostgreSQL 的自增序列（取号机）落后了**。真实数据最大 id 已经很大，但序列还停在很小的数字，继续发旧号就必撞车。

### 2）是否已精确定位？
- 已定位到：`public.community_pool.id` 的序列 `community_pool_id_seq`。
- 现场证据（本地 dev 库）：
  - `MAX(id)=1383`
  - `community_pool_id_seq.last_value=11` 且 `is_called=true`（下一次会发 12，必撞）

### 3）精确修复方法？
- 核心策略：**只把 next 往前推，绝不往回拉**（避免复用历史 id，降低对现有业务的潜在影响）。
- 计算方式：
  - `table_max = MAX(id)`
  - `seq_next = (is_called ? last_value+1 : last_value)`
  - `target_next = max(table_max+1, seq_next)`
  - `setval(seq, target_next, false)`

### 4）下一步做什么？
- 线上/生产最小风险做法：直接执行独立 SQL：`repair_community_pool_id_sequence.sql`（只修序列，不跑其他迁移）。
- 然后再新增社区（两种方式任选其一）：
  - 跑脚本：`backend/david_add_giants_final.py`（已改成“只新增，不覆盖”）
  - 或走你现有的 Admin 导入/新增流程（现在不会再因为序列失步而撞主键）

### 5）这次修复的效果是什么？达到了什么结果？
- 修复后：新增 `community_pool` 记录不会再因为“发号器落后”撞主键。
- 已补齐：AI_Workflow 相关社区（如 `r/localllama`, `r/chatgpt` 等）可正常插入，并且同步补了 `community_cache` stub。

---

## 我做了哪些改动（以不影响现有数据为原则）

### 1) 可复用的“序列修复”能力（不改表数据）
- 代码函数：`backend/app/db/sequence_repair.py`
  - `repair_serial_pk_sequence(...)`：只修 sequence 的 next 值（只增不减）
- 独立 SQL（最小风险、可直接线上执行）：`repair_community_pool_id_sequence.sql`

### 2) 可回归的测试（先复现、再修复）
- 测试用例：`backend/tests/migrations/test_community_pool_sequence_repair.py`
  - 先把序列故意打回去复现冲突
  - 再调用修复函数验证插入恢复正常
- 我实际跑过的命令：
  - `cd backend && PYTEST_RUNNING=1 APP_ENV=test ENABLE_CELERY_DISPATCH=0 DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q tests/migrations/test_community_pool_sequence_repair.py`

### 3) Alembic 迁移（用于“已经在升级链路里”的环境）
- 迁移文件：`backend/alembic/versions/20251217_000003_fix_community_pool_id_sequence.py`
- 注意：如果你的库当前没升级到最新 head，**不建议为了这个问题强行 upgrade head**（会顺带跑其他迁移）。此时请优先用独立 SQL 文件。

### 4) 新增社区 + AI_Workflow 领域（只新增、不覆盖）
- 更新脚本：`backend/david_add_giants_final.py`
  - 先修序列
  - 再按名单插入缺失社区（存在就跳过，不覆盖任何现有配置）
  - categories 会写成 `["AI_Workflow"]`，vertical 也写成 `AI_Workflow`（便于后续按领域跑计划）


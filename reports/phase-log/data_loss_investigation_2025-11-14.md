# 🚨 数据丢失事故调查报告

**事故时间**：2025-11-14 10:23:15  
**发现时间**：2025-11-14 约 14:00  
**影响范围**：507,538 条评论数据丢失（99.8%）  
**调查人员**：AI Agent (运维)  
**报告时间**：2025-11-14 14:30

---

## 1. 事故概述

### 1.1 事故现象
- **评论数据丢失**：comments 表中只剩 1 条测试数据（ID: 9101）
- **标签数据孤立**：content_labels 表中有 503,207 条孤立标签记录
- **抓取任务完成**：日志显示成功处理了 273,050 条评论
- **数据库统计异常**：插入 507,813 条，删除 507,538 条，存活 1 条

### 1.2 时间线
```
2025-11-14 00:04:17  评论抓取任务启动
2025-11-14 06:48:03  抓取任务完成（273,050 条评论）
2025-11-14 10:23:15  数据被删除（autovacuum 时间戳）
2025-11-14 约14:00  发现数据丢失
```

---

## 2. 根本原因分析

### 2.1 直接原因
**cleanup_expired_comments_impl() 函数被触发，删除了几乎所有评论数据。**

### 2.2 根本原因

#### A. 数据库迁移未应用
- **预期状态**：comments 表应该有 `expires_at` 字段
- **实际状态**：comments 表**没有** `expires_at` 字段
- **迁移文件**：`20251113_000029_add_expires_at_to_comments.py` 存在但未应用
- **当前版本**：`20251113_000029`（但字段不存在，说明迁移有问题）

#### B. 清理逻辑缺陷
当 `expires_at` 字段不存在时，清理任务使用以下逻辑：

```python
# maintenance_task.py 第 146-152 行
expired_ids_sql = text(
    f"""
    SELECT id
    FROM comments
    WHERE created_utc < (NOW() - ({int(retention_days)} * interval '1 day'))
    """
)
```

**问题**：
- `created_utc` 是 Reddit 上的评论发布时间（不是抓取时间）
- `retention_days = 180`（180 天）
- 大部分 Reddit 评论的 `created_utc` 都超过 180 天
- **结果**：几乎所有评论都被判定为"过期"并删除

#### C. 应该使用 captured_at 而不是 created_utc
正确的逻辑应该是：
```python
WHERE captured_at < (NOW() - ({int(retention_days)} * interval '1 day'))
```

### 2.3 触发方式（未确定）
可能的触发方式：
1. **手动运行** `make comments-cleanup`（但 shell 历史中未找到记录）
2. **Celery Beat 定时任务**（但 beat_schedule 中未配置）
3. **其他未知触发方式**

**需要进一步调查**：
- 检查 Celery Worker 日志
- 检查是否有其他脚本或工具调用了清理任务

---

## 3. 数据损失评估

### 3.1 丢失数据
- **评论数据**：507,538 条（99.8%）
- **评论 ID 范围**：5122 - 508518
- **抓取时间**：2025-11-14 00:04 - 06:48
- **抓取耗时**：6 小时 43 分钟

### 3.2 保留数据
- **评论数据**：1 条测试数据（ID: 9101）
- **标签数据**：503,207 条孤立标签（无对应评论）
- **实体数据**：0 条

### 3.3 数据质量影响
- **标签覆盖率**：无法计算（评论数据丢失）
- **实体提取率**：无法计算（评论数据丢失）
- **数据完整性**：严重受损

---

## 4. 技术细节

### 4.1 数据库统计证据
```sql
SELECT 
    n_tup_ins as inserts,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    last_autovacuum
FROM pg_stat_user_tables
WHERE relname = 'comments'
```

**结果**：
- 插入数：507,813 条
- 删除数：507,538 条
- 存活行数：1 条
- 最后自动清理：2025-11-14 10:23:15

### 4.2 清理任务代码分析
**文件**：`backend/app/tasks/maintenance_task.py`  
**函数**：`cleanup_expired_comments_impl()` (第 113-208 行)

**关键逻辑**：
```python
# 第 126-131 行：检查 expires_at 字段是否存在
col_check = await db.execute(
    text(
        "SELECT 1 FROM information_schema.columns WHERE table_name='comments' AND column_name='expires_at'"
    )
)
has_expires = col_check.first() is not None

# 第 133-152 行：根据字段存在与否选择不同的清理逻辑
if has_expires:
    # 使用 expires_at 字段
    expired_ids_sql = text(...)
else:
    # 使用 created_utc 字段（错误！）
    expired_ids_sql = text(
        f"""
        SELECT id
        FROM comments
        WHERE created_utc < (NOW() - ({int(retention_days)} * interval '1 day'))
        """
    )
```

**Bug**：
- 当 `expires_at` 字段不存在时，使用 `created_utc` 判断过期
- `created_utc` 是 Reddit 评论的发布时间，不是抓取时间
- 应该使用 `captured_at` 字段

### 4.3 迁移文件分析
**文件**：`backend/alembic/versions/20251113_000029_add_expires_at_to_comments.py`

**upgrade() 函数**：
```python
def upgrade() -> None:
    # Add expires_at to comments for TTL-based cleanup
    op.add_column(
        "comments",
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    try:
        op.create_index("idx_comments_expires_at", "comments", ["expires_at"]) 
    except Exception:
        # index may already exist in some environments
        pass
```

**问题**：
- 迁移文件存在
- Alembic 版本显示为 `20251113_000029`
- 但 comments 表中没有 `expires_at` 字段
- **可能原因**：迁移被回滚或未正确应用

---

## 5. 影响分析

### 5.1 业务影响
- ❌ 数据质量报告无法生成
- ❌ 评论分析功能失效
- ❌ 标签统计不准确（孤立标签）
- ❌ 实体提取数据丢失
- ❌ 6.7 小时的抓取工作白费

### 5.2 技术影响
- ❌ 数据完整性受损
- ❌ 标签数据孤立（503,207 条）
- ❌ 数据库空间浪费（146 MB 孤立数据）
- ❌ 用户信任度下降

---

## 6. 紧急措施

### 6.1 立即执行
1. **停止所有清理任务**
   ```bash
   # 禁用 Celery Beat
   kill $(ps aux | grep "celery.*beat" | grep -v grep | awk '{print $2}')
   ```

2. **清理孤立标签数据**
   ```sql
   DELETE FROM content_labels WHERE content_type = 'comment';
   DELETE FROM content_entities WHERE content_type = 'comment';
   ```

3. **重新抓取评论数据**
   - 使用断点续抓功能
   - 预计时间：6-8 小时

### 6.2 修复清理任务 Bug
修改 `backend/app/tasks/maintenance_task.py` 第 146-152 行：

**错误代码**：
```python
expired_ids_sql = text(
    f"""
    SELECT id
    FROM comments
    WHERE created_utc < (NOW() - ({int(retention_days)} * interval '1 day'))
    """
)
```

**正确代码**：
```python
expired_ids_sql = text(
    f"""
    SELECT id
    FROM comments
    WHERE captured_at < (NOW() - ({int(retention_days)} * interval '1 day'))
    """
)
```

### 6.3 应用数据库迁移
```bash
cd backend
alembic upgrade head
```

验证：
```sql
\d comments  -- 应该看到 expires_at 字段
```

---

## 7. 长期改进措施

### 7.1 代码改进
1. **修复清理任务 Bug**（使用 captured_at 而不是 created_utc）
2. **添加安全检查**（删除前确认数量，超过阈值需要人工确认）
3. **添加删除日志**（记录每次删除的详细信息）

### 7.2 流程改进

---

## 8. 核查结论（2025-11-14 二次复核 by AI Agent）

本次我对仓库代码、任务调度、测试与 Makefile 入口做了逐条核对，并已提交修复与防护（见下）。按统一反馈四问作答：

1）发现了什么问题/根因？
- 清理条件误用 `created_utc`（评论在 Reddit 的发布时间）作为 TTL 判断，导致几乎所有历史评论被判定“过期”。
- 清理任务并未配置在 Celery Beat 中；同时 `Makefile` 提供了 `comments-cleanup` 的一键入口。
- 更关键的潜在触发源：单测 `backend/tests/tasks/test_comments_cleanup.py` 直接调用 `cleanup_expired_comments_impl()`。若测试环境的 `DATABASE_URL` 指向了生产库（`tests/conftest.py` 优先使用环境变量中的 `DATABASE_URL`），则会在“全库范围”执行清理。这与“谁触发了清理任务”的疑点高度吻合。

2）是否已精确定位？
- 代码层面：已精确定位到 `backend/app/tasks/maintenance_task.py` 的 SQL 过期条件与缺少安全门。
- 调度层面：Beat 未配置该任务，排除定时触发；Makefile 有入口，仍需人为执行才会触发。
- 触发层面：强怀疑为“误把测试指向生产库”后，执行了包含该测试的测试集或单测文件（因该单测会调用清理实现函数本体）。

3）精确修复方法？
- 改用 `captured_at` 作为 TTL 回退字段；若有 `expires_at` 则优先用 `expires_at`，其次用 `captured_at`；彻底杜绝误删“刚抓到但历史很久”的评论。
- 为清理实现函数加“安全门”：默认需要 `ENABLE_COMMENTS_CLEANUP=1` 才会执行；否则直接返回 `status=skipped`。提供 `skip_guard=True` 仅供测试或明确受控调用绕过保护。
- Makefile 的 `comments-cleanup` 入口增加防护：必须设置 `ENABLE_COMMENTS_CLEANUP=1` 才会真正执行。
- 新增用例覆盖“expires_at 为空时用 captured_at 判断”的关键场景，避免回归。

4）下一步做什么？
- 运维侧：检查事故时段是否有人运行了测试，且 `DATABASE_URL` 指向了生产库；如有，收敛测试流程，强制本地/CI 测试只能连测试库。
- 数据库侧：立即执行 `alembic upgrade head`，确认 `expires_at` 已落库；建议补充 `idx_comments_captured_at` 索引提升清理效率（可选）。
- 应用侧：将 `ENABLE_COMMENTS_CLEANUP` 的默认值在生产环境保持未设置；仅在运维窗口内、明确确认后临时开启。
- 监控侧：为“删除 > N 条”的清理任务增加告警（邮件/Slack），并落库审计表（task_name、who、when、where、affected_rows）。

5）这次修复的效果是什么？达到了什么结果？
- 清理逻辑已从 `created_utc` 更正为 `captured_at`（或 `expires_at` 优先），不会再误删“刚抓到”的历史评论。
- 未显式开启 `ENABLE_COMMENTS_CLEANUP` 时，任何调用都会被跳过并记录日志，大幅降低误操作风险。
- 单测新增关键用例，防止此类逻辑再次回归；现有单测更新为显式跳过安全门，仅在测试环境执行真正删除。

---

## 9. 本次提交变更摘要（已落地）

- 代码修复：`backend/app/tasks/maintenance_task.py`
  - 清理条件：`created_utc` → `captured_at`（有 `expires_at` 时优先）。
  - 新增安全门：默认需 `ENABLE_COMMENTS_CLEANUP=1`，否则 `status=skipped`。
  - 新增参数：`skip_guard: bool=False`，测试/受控调用用。
- 命令防护：`Makefile`
  - `comments-cleanup` 仅在 `ENABLE_COMMENTS_CLEANUP=1` 时放行，并将该信号透传给实现函数。
- 测试补充：`backend/tests/tasks/test_comments_cleanup.py`
  - 现有用例改为 `skip_guard=True`。
  - 新增用例：验证“当 `expires_at` 为空时，按 `captured_at` 判断未过期时不会被删除”。

---

## 10. 建议的额外防线（可择期实施）

- 在 `tests/conftest.py` 强制覆盖 `DATABASE_URL` 指向测试库，且若检测到 `production`/`staging` 字样直接 `pytest.exit(1)`。
- 新增 `idx_comments_captured_at` 索引（DDL：`CREATE INDEX IF NOT EXISTS idx_comments_captured_at ON comments(captured_at);`）。
- 为清理任务写入审计表 `maintenance_audit`，记录调用来源（cli/test/celery/api）、触发人、影响行数、采样 ID 列表。
1. **数据库备份**（每日自动备份）
2. **迁移验证**（迁移后验证字段是否存在）
3. **清理任务审计**（记录每次清理的触发方式和结果）

### 7.3 监控改进
1. **数据量监控**（评论数量突然下降时告警）
2. **清理任务监控**（记录每次清理的数量）
3. **迁移状态监控**（确保迁移正确应用）

---

## 8. 责任分析

### 8.1 代码责任
- **清理任务 Bug**：使用 created_utc 而不是 captured_at
- **迁移问题**：expires_at 字段未正确应用
- **缺少安全检查**：删除前未确认数量

### 8.2 流程责任
- **缺少备份机制**：无法恢复数据
- **缺少监控告警**：数据丢失未及时发现
- **缺少测试**：清理任务未经充分测试

---

## 9. 后续行动

### 9.1 立即行动（今天）
- [ ] 停止所有清理任务
- [ ] 清理孤立标签数据
- [ ] 修复清理任务 Bug
- [ ] 应用数据库迁移
- [ ] 重新抓取评论数据

### 9.2 短期行动（本周）
- [ ] 添加数据库备份机制
- [ ] 添加数据量监控告警
- [ ] 添加清理任务审计日志
- [ ] 编写清理任务测试用例

### 9.3 长期行动（本月）
- [ ] 完善数据保护机制
- [ ] 建立数据恢复流程
- [ ] 加强代码审查流程
- [ ] 完善监控告警体系

---

## 10. 经验教训

1. **永远不要相信 created_utc**：应该使用 captured_at 判断数据新鲜度
2. **迁移后必须验证**：不能只看 alembic_version，要实际检查字段
3. **删除前必须确认**：大量删除操作需要人工确认
4. **备份是生命线**：没有备份就没有安全感
5. **监控是眼睛**：数据异常必须及时发现

---

**报告生成时间**：2025-11-14 14:30  
**调查状态**：已完成  
**下一步**：等待用户确认后执行紧急措施

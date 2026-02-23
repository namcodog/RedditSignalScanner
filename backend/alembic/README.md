# Alembic Database Migrations

本目录包含 RedditSignalScanner 项目的所有数据库迁移脚本，使用 Alembic 进行版本管理。

## 迁移脚本目录结构

```
alembic/
├── versions/           # 迁移脚本存放目录
├── env.py             # Alembic 环境配置
├── script.py.mako     # 迁移脚本模板
└── alembic.ini        # Alembic 配置文件
```

---

## 语义库迁移 (semantic-db-migration spec)

### 迁移列表

以下迁移脚本实现了语义库从 YAML 到数据库的完整迁移：

| 脚本文件 | 版本号 | 描述 | 状态 |
|---------|--------|------|------|
| `20251116_000032_add_semantic_tables.py` | 20251116_000032 | 创建 semantic_terms、semantic_candidates、semantic_audit_log 三张表，并从 YAML 导入初始数据 | ✅ |
| `20251116_000033_rename_quality_score_fields.py` | 20251116_000033 | 重命名 community_pool.quality_score → semantic_quality_score<br>重命名 community_cache.quality_score → crawl_quality_score | ✅ |
| `20251116_000034_add_community_foreign_keys.py` | 20251116_000034 | 添加外键约束：<br>- community_cache.community_name → community_pool.name (CASCADE)<br>- discovered_communities.name → community_pool.name (SET NULL) | ✅ |
| `20251116_000035_add_comments_tiered_ttl.py` | 20251116_000035 | 为 comments 表添加基于 score 的分级 TTL 策略（30/180/365天） | ✅ |

### 迁移依赖关系

```
20251114_000031 (之前的迁移)
    ↓
20251116_000032 (语义表)
    ↓
20251116_000033 (字段重命名) ← 独立，不依赖语义表
    ↓
20251116_000034 (外键约束) ← 独立，不依赖语义表
    ↓
20251116_000035 (评论TTL) ← 独立，不依赖语义表
```

---

## 执行迁移

### 前置条件

1. **数据库连接配置**
   ```bash
   # 确保环境变量已设置
   export DATABASE_URL="postgresql://user:pass@localhost:5432/reddit_signal_scanner_dev"
   # 如需对照金库，请显式切库并评估风险
   # export DATABASE_URL="postgresql://user:pass@localhost:5432/reddit_signal_scanner"
   ```

2. **备份数据库** (生产环境必须!)
   ```bash
   pg_dump -U user -d reddit_signal_scanner_dev -F c -b -v -f backup_$(date +%Y%m%d_%H%M%S).dump
   ```

### 升级到最新版本

```bash
cd backend

# 查看当前版本
alembic current

# 查看待执行的迁移
alembic history

# 执行所有待迁移脚本
alembic upgrade head

# 验证迁移结果
python scripts/validate_semantic_migration.py
```

### 升级到指定版本

```bash
# 升级到指定版本
alembic upgrade 20251116_000032

# 或相对升级（升级 2 个版本）
alembic upgrade +2
```

### 查看迁移状态

```bash
# 查看当前数据库版本
alembic current

# 查看迁移历史
alembic history --verbose

# 查看待执行的迁移
alembic show head
```

---

## 回滚迁移

### ⚠️ 回滚注意事项

- **数据丢失风险**: 部分迁移回滚会导致数据丢失（如删除表、删除列）
- **生产环境**: 回滚前务必备份数据库
- **测试验证**: 在测试环境验证回滚流程

### 回滚命令

```bash
# 回滚一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade 20251114_000031

# 回滚所有迁移（危险！）
alembic downgrade base
```

### 语义库迁移回滚影响

| 回滚目标 | 影响 |
|---------|------|
| 20251116_000034 → 20251116_000033 | 删除外键约束，数据保留 |
| 20251116_000033 → 20251116_000032 | 恢复 quality_score 字段名，数据保留 |
| 20251116_000032 → 20251114_000031 | **删除语义表**（semantic_terms、semantic_candidates、semantic_audit_log），**数据全部丢失** |

### 回滚恢复流程

如果回滚后需要恢复数据：

```bash
# 1. 从备份恢复
pg_restore -U user -d reddit_scanner backup_20251116.dump

# 2. 重新执行迁移
alembic upgrade head

# 3. 验证数据完整性
python scripts/validate_semantic_migration.py
```

---

## 迁移验证

### 自动验证脚本

```bash
cd backend

# 运行验证脚本（只读检查）
python scripts/validate_semantic_migration.py
```

**验证项**:
1. ✅ semantic_terms 记录数匹配 YAML 术语数
2. ✅ YAML 中的所有 canonical 术语存在于数据库
3. ✅ community_pool.semantic_quality_score 非空
4. ✅ community_cache.crawl_quality_score 非空
5. ✅ 无孤儿记录（community_cache 外键完整性）
6. ✅ comments.expires_at 全部设置
7. ✅ 高分评论 TTL 正确（>180 天）

### 手动验证查询

```sql
-- 检查语义表记录数
SELECT COUNT(*) FROM semantic_terms;

-- 检查候选词状态分布
SELECT status, COUNT(*) FROM semantic_candidates GROUP BY status;

-- 检查审计日志
SELECT action, COUNT(*) FROM semantic_audit_log GROUP BY action;

-- 检查 quality_score 字段重命名
\d community_pool   -- 应该有 semantic_quality_score
\d community_cache  -- 应该有 crawl_quality_score

-- 检查外键约束
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('community_cache', 'discovered_communities');
```

---

## 创建新迁移

### 自动生成迁移脚本

```bash
# Alembic 自动检测模型变更
alembic revision --autogenerate -m "description of changes"

# 手动创建空白迁移脚本
alembic revision -m "description of changes"
```

### 迁移脚本命名规范

格式: `YYYYMMDD_NNNNNN_description.py`

- `YYYYMMDD`: 日期（如 20251116）
- `NNNNNN`: 6 位序号（如 000032）
- `description`: 简短描述（snake_case）

**示例**:
- ✅ `20251116_000032_add_semantic_tables.py`
- ✅ `20251116_000033_rename_quality_score_fields.py`
- ❌ `add_new_column.py` (缺少日期和序号)

### 迁移脚本模板

```python
"""brief description

Revision ID: YYYYMMDD_NNNNNN
Revises: previous_revision
Create Date: YYYY-MM-DD HH:MM:SS.mmmmmm
"""

from alembic import op
import sqlalchemy as sa


revision = 'YYYYMMDD_NNNNNN'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级逻辑"""
    pass


def downgrade() -> None:
    """回滚逻辑"""
    pass
```

---

## 最佳实践

### 迁移开发

1. **小步迭代**: 每个迁移专注一个功能点
2. **可逆性**: 所有迁移必须提供 downgrade() 方法
3. **幂等性**: 迁移脚本应支持重复执行（使用 `checkfirst=True`）
4. **数据安全**:
   - 删除列前先备份数据
   - 重命名字段使用 3 步法（add → copy → drop）
5. **测试验证**: 在测试环境充分验证后再部署生产

### 生产部署

1. **备份优先**: 迁移前备份数据库
2. **停机窗口**: 评估是否需要停机（大表 DDL 操作）
3. **分阶段执行**:
   - Stage 1: 测试环境验证
   - Stage 2: 生产环境小流量验证
   - Stage 3: 全量部署
4. **监控指标**:
   - 迁移执行时间
   - 数据库锁等待
   - 应用错误率
5. **回滚准备**: 准备好回滚脚本和流程

### 常见问题

**Q: 迁移执行很慢怎么办？**
A:
- 检查是否在大表上添加索引（考虑 CONCURRENTLY）
- 批量数据更新改为分批执行
- 考虑在低峰期执行

**Q: 迁移失败如何处理？**
A:
1. 检查错误日志
2. 手动修复数据库状态
3. 更新 alembic_version 表到正确版本
4. 重新执行迁移或回滚

**Q: 多人协作如何避免迁移冲突？**
A:
- 迁移前先拉取最新代码
- 使用 `alembic merge` 合并分支
- 统一迁移序号管理

---

## 相关文档

- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [语义库迁移设计文档](../../.spec-workflow/specs/semantic-db-migration/design.md)
- [语义库使用指南](../../docs/semantic-library-guide.md)
- [数据库架构文档](../../docs/database-schema.md)

---

## 联系与支持

- **Issue 追踪**: GitHub Issues
- **迁移问题**: 查看 `backend/logs/alembic.log`
- **数据库备份**: 联系 DBA 团队

---

**最后更新**: 2025-11-17
**维护者**: RedditSignalScanner Team

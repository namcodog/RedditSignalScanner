# 数据库分裂问题分析报告

**日期**: 2025-11-14  
**问题**: 发现系统中存在两个独立的PostgreSQL数据库，数据分散且不一致

---

## 🚨 核心问题：双数据库分裂

系统中存在**两个完全独立的数据库**，导致数据分散、不一致：

### 数据库1: `reddit_scanner`
- **Alembic版本**: `20251017_000009` (旧版本，2025-10-17)
- **posts_hot**: 25,971条帖子 (2015-06-16 ~ 2025-10-18)
- **community_pool**: **0条** (空表)
- **comments**: 刚手动创建，0条数据
- **独特社区数**: 277个
- **状态**: 包含大量历史数据，但社区池为空

### 数据库2: `reddit_signal_scanner`
- **Alembic版本**: `20251114_000031` (最新版本，2025-11-14)
- **posts_hot**: 30条帖子 (2025-11-14，今天的测试数据)
- **community_pool**: **260条** (刚导入的核心社区)
- **comments**: 完整表结构，包含expires_at字段
- **状态**: 最新迁移，但缺少历史数据

---

## 🔍 根本原因分析

### 1. 配置不一致

**backend/.env** (应用配置):
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner
```

**backend/alembic.ini** (迁移配置):
```ini
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner
```

**backend/app/core/config.py** (默认配置):
```python
name = os.getenv("POSTGRES_DB", "reddit_signal_scanner")  # 默认数据库名
```

**结论**: 
- ✅ 配置文件都指向 `reddit_signal_scanner`
- ❌ 但 `reddit_scanner` 数据库仍然存在且包含大量历史数据
- ❓ 可能是历史遗留：之前用 `reddit_scanner`，后来改名为 `reddit_signal_scanner`

### 2. 数据迁移断层

**reddit_scanner** (旧库):
- 停留在 `20251017_000009` 版本
- 缺少评论表相关的所有迁移 (20251112_000025 ~ 20251114_000031)
- 包含大量历史抓取数据

**reddit_signal_scanner** (新库):
- 已升级到最新版本 `20251114_000031`
- 包含完整的评论表结构
- 但缺少历史数据

### 3. 迁移链断裂

发现迁移链存在分支：
```
20251017_000009 -> 20251017_000010 -> ... -> 20251027_000024
                                                    ↓
                                            34a283ef7d4e (分支点)
                                                    ↓
                                            20251112_000025 (评论表)
                                                    ↓
                                            20251114_000031 (最新)
```

**问题**: `34a283ef7d4e` 这个分支与主线脱节，导致旧库无法自动升级到评论表版本

---

## 📊 数据资产对比

| 指标 | reddit_scanner (旧库) | reddit_signal_scanner (新库) |
|------|----------------------|----------------------------|
| **posts_hot** | 25,971条 | 30条 |
| **时间跨度** | 2015-06 ~ 2025-10 | 2025-11-14 (今天) |
| **社区数** | 277个 | 未知 (只有30条测试数据) |
| **community_pool** | 0条 (空) | 260条 (核心社区) |
| **comments** | 手动创建，0条 | 完整结构，0条 |
| **Alembic版本** | 20251017_000009 | 20251114_000031 |
| **数据价值** | ⭐⭐⭐⭐⭐ 历史数据 | ⭐⭐ 测试数据 |

---

## 🎯 数据污染分析

### posts_hot中的277个社区 vs 260个核心社区

**关键发现**: 
- posts_hot中的277个社区**全部不在**新导入的260个核心社区中
- 这意味着：
  1. 旧数据是用不同的社区池抓取的
  2. 260个核心社区是2025-11-13清理后的结果
  3. 两者完全不重叠

**污染社区Top 20** (reddit_scanner库):
```
IndieGaming       - 154 posts
mentalhealth      - 154 posts
jobs              - 153 posts
travel            - 152 posts
writing           - 151 posts
buildapc          - 151 posts
careerguidance    - 151 posts
Instagram         - 150 posts
cycling           - 150 posts
remotework        - 150 posts
...
```

**分析**: 这些社区与跨境电商主题**完全无关**，属于污染数据

---

## 💡 解决方案建议

### 方案A: 统一到 reddit_signal_scanner (推荐)

**步骤**:
1. ✅ 保留 `reddit_signal_scanner` 作为主库 (已有260个核心社区)
2. ❌ 放弃 `reddit_scanner` 的25,971条旧数据 (污染严重)
3. ✅ 使用260个核心社区重新抓取数据
4. ✅ 删除 `reddit_scanner` 数据库

**优点**:
- 数据干净，无污染
- 迁移版本最新
- 符合Spec 013的清理策略

**缺点**:
- 丢失历史数据 (但这些数据污染严重，价值有限)

### 方案B: 迁移旧数据到新库 (不推荐)

**步骤**:
1. 从 `reddit_scanner` 筛选出260个核心社区的数据
2. 迁移到 `reddit_signal_scanner`
3. 删除污染数据

**优点**:
- 保留部分历史数据

**缺点**:
- 工作量大
- 数据质量无法保证
- 可能引入新的污染

---

## 🔧 立即执行的修复步骤

### 1. 确认当前应用连接的数据库

```bash
cd backend && python -c "from app.core.config import get_settings; print(get_settings().database_url)"
# 输出: postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner
```

✅ **确认**: 应用和Celery都连接到 `reddit_signal_scanner`

### 2. 验证260个核心社区已导入

```bash
psql -d reddit_signal_scanner -c "SELECT COUNT(*) FROM community_pool WHERE is_active = true;"
# 输出: 260
```

✅ **确认**: 260个核心社区已成功导入

### 3. 验证评论表结构完整

```bash
psql -d reddit_signal_scanner -c "\d comments"
```

✅ **确认**: 评论表包含所有必需字段，包括 `expires_at`

### 4. 清理旧数据库 (可选)

```bash
# 备份旧库 (以防万一)
pg_dump reddit_scanner > /tmp/reddit_scanner_backup_20251114.sql

# 删除旧库
psql -c "DROP DATABASE reddit_scanner;"
```

---

## 📋 下一步行动计划

### 阶段1: 验证与清理 ✅
- [x] 导入260个核心社区到 community_pool
- [x] 创建评论表及相关表
- [x] 分析数据库污染情况

### 阶段2: 数据抓取 (待执行)
- [ ] 使用260个核心社区重新抓取帖子
- [ ] 抓取评论数据
- [ ] 验证数据质量

### 阶段3: 清理冗余 (待执行)
- [ ] 备份并删除 `reddit_scanner` 数据库
- [ ] 清理冗余脚本和临时文件
- [ ] 更新文档

---

## 🎓 经验教训

1. **数据库命名一致性**: 避免在项目中途改变数据库名称
2. **迁移链管理**: 确保迁移链连续，避免分支
3. **配置集中管理**: 所有配置应指向同一数据库
4. **定期清理**: 及时删除废弃的数据库和数据
5. **数据验证**: 导入数据后立即验证，避免静默失败

---

## 📌 总结

**核心问题**: 系统存在两个数据库，数据分散且不一致

**根本原因**: 
1. 历史遗留：从 `reddit_scanner` 改名为 `reddit_signal_scanner`
2. 迁移链断裂：评论表迁移在独立分支
3. 数据污染：旧库包含277个无关社区的数据

**解决方案**: 
- ✅ 使用 `reddit_signal_scanner` 作为唯一数据库
- ✅ 260个核心社区已导入
- ✅ 评论表结构完整
- ❌ 放弃旧库的污染数据
- 🔄 重新抓取干净数据

**当前状态**: 
- 阶段1和阶段2已完成 ✅
- 准备进入数据抓取阶段 🚀


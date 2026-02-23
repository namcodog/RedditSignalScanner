# 数据库开发与使用规范 SOP

**项目**: Reddit Signal Scanner  
**版本**: 1.9  
**生效日期**: 2025-12-01  
**适用对象**: 后端开发、数据工程师、运维人员

---

## 1. 核心原则 (Core Principles)

1.  **环境隔离**：严禁在本地开发环境连接生产库。生产库操作必须经过 Review 和备份。
2.  **读写分离（逻辑层）**：重型分析查询（OLAP）应尽量避免阻塞实时写入（OLTP）。
3.  **计算存储分离**：数据库仅做存储和检索，**严禁**在数据库内执行复杂的文本清洗、Embedding 计算或 Python 逻辑。
4.  **Schema 即代码 (Source of Truth)**：
    *   `current_schema.sql` 是数据库架构的**唯一事实来源**。
    *   所有生产环境的变更，必须在执行后立即反向同步更新此文件 (`make db-sync-schema`)。
    *   禁止手动在 GUI 工具中修改表结构而不提交代码。
5.  **Database as Source of Truth**：数据一致性必须由数据库约束强制保证，不能仅依赖应用层自觉。

---

## 2. 连接与配置规范

### 2.1 数据库识别
为防止“连错库”事故，应用启动时**必须**执行自检：

*   **生产库名称**: `reddit_signal_scanner`
*   **测试库名称**: `reddit_signal_scanner_test`

**代码要求**：
后端服务启动时，必须校验 `SELECT current_database()` 的结果是否与配置预期一致。不一致则拒绝启动。

### 2.2 环境变量
所有连接信息必须通过 `.env` 管理，禁止硬编码。
```bash
# 标准配置示例
POSTGRES_DB=reddit_signal_scanner
POSTGRES_USER=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 2.3 推荐本地配置 (Local Optimization) 🆕
为提升开发体验和测试速度，建议在本地环境优化以下参数：
*   `work_mem`: **16MB** (默认 4MB 太小，易导致磁盘排序)。
    *   设置命令: `ALTER SYSTEM SET work_mem = '16MB';`
*   **插件精简**: 移除无用的 `uuid-ossp` 等旧插件，保持环境纯净。

---

## 3. 命名规范 (Naming Convention)

为了保持 Schema 清洁，所有新创建的对象必须遵守以下命名规则：

| 对象类型 | 命名格式 | 示例 |
| :--- | :--- | :--- |
| **表 (Table)** | `snake_case`, 复数名词 | `posts_raw`, `community_cache` |
| **主键 (PK)** | `pk_<table_name>` | `pk_posts_raw` |
| **外键 (FK)** | `fk_<table_name>_<ref_table>` | `fk_comments_posts_raw` |
| **普通索引** | `idx_<table_name>_<columns>` | `idx_posts_raw_created_at` |
| **唯一索引** | `uq_<table_name>_<columns>` | `uq_posts_hot_source_post` |
| **Check 约束** | `ck_<table_name>_<condition_summary>` | `ck_community_cache_ttl_positive` |
| **触发器** | `trg_<table_name>_<action>` | `trg_posts_raw_enforce_scd2` |

**禁止项**：
*   禁止使用形如 `ck_table_ck_table_col_condition` 的冗余前缀。
*   禁止使用驼峰命名法。

---

## 4. 数据模型设计模式

### 4.1 社区命名规范 (Community Naming) 🆕
**强制标准**：
*   **前缀**: 必须以 `r/` 开头。
*   **大小写**: **强制全小写 (Lowercase)**。严禁大写字母。

**软硬配合机制 (Crucial)**：
*   **数据库层 (The Gatekeeper)**:
    *   Check 约束 `CHECK (name ~ '^r/[a-z0-9_]+$')` 充当**防火墙**。
    *   **注意**: 数据库**不会自动转换**数据，只会**拒绝并报错** (Reject & Error)。
*   **应用层 (The Cleaner)**:
    *   写入前必须调用 `normalize_subreddit_name`。
    *   该函数负责将 `r/Apple` 转换为 `r/apple`，确保能通过数据库安检。

### 4.2 社区生命周期管理规范 (Lifecycle Management) 🆕
**原则**: 防止社区表虚胖。
*   **判定标准**: `last_crawled_at` 为 NULL，或 `is_active=false` 且长期无流量。
*   **处理策略**:
    *   **软删除**: 不执行物理 `DELETE`。
    *   **状态标记**: `is_active=false`, `tier='archived'`, `health_status='archived'`。
    *   **定期归档**: 每季度运行一次归档脚本，将新发现但无效的社区移入冷宫。

### 4.3 拉链表 (SCD2) 设计规范
**适用场景**: `posts_raw` (长期归档表)
**核心逻辑**: 只有**实质性内容变更**才生成新版本。

*   **触发生成新版本的字段 (INSERT)**: `title`, `body` (内容发生变化)
*   **仅原地更新 (UPDATE)**: `score`, `num_comments`, `updated_at`, `metadata` (仅热度/统计数据变化)
*   **实现方式**: 必须使用 `trg_posts_raw_enforce_scd2` 触发器强制执行。
    *   应用层统一执行 `UPDATE` 语句。
    *   数据库触发器根据字段差异决定是 `INSERT` 新版本还是 `UPDATE` 旧版本。

### 4.4 用户画像关联规范 (User Profile) 🆕
**原则**: 消除孤岛数据。
*   **Authors 表**: 作为用户单一事实来源 (Source of Truth)。
*   **关联**: `posts_raw.author_id` 必须通过外键 `fk_posts_raw_author` 关联到 `authors.author_id`。
*   **空值处理**: 匿名用户存为 `NULL`，严禁存储空字符串 `''`。

### 4.5 分析模型规范 (Analysis Model) 🆕
*   **结构化字段**: 关键指标（如 `sentiment_score`, `recommendation`）必须提取为实体列，建立索引，禁止仅存 JSONB。
*   **多版本支持**: 允许同一 Task 存在多个 Analysis 版本。
    *   约束: `UNIQUE(task_id, analysis_version)`。

### 4.6 AI 向量存储规范 (AI Vector Storage) 🆕
**启用插件**: `pgvector`
**存储策略**: **垂直分表 (Vertical Partitioning)**

*   **主表**: 存文本 (`posts_raw`)
*   **向量表**: 存 Embedding (`post_embeddings`)
    *   **主键**: `(post_id, model_version)` (联合主键，支持多模型版本)
    *   **关联**: `post_id` (FK ON DELETE CASCADE)
    *   **模型标准**: 默认为 **BAAI/bge-m3** (1024 dim)。(Updated 2025-12-01)
    *   **索引**: 必须使用 **HNSW** 索引 (`vector_cosine_ops`)，参数推荐 `m=16, ef_construction=128`。

### 4.7 全文检索规范 (Full-Text Search) 🆕
**目标**: 支持秒级关键词检索。
*   **实现方式**: 使用 Postgres Generated Column (`content_tsvector`)。
*   **公式**: `to_tsvector('english', title || ' ' || body)`。
*   **索引**: 必须建立 `GIN` 索引。
*   **应用**: 前端关键词搜索应使用 `@@` 操作符，而非 `LIKE`。

---

## 5. 变更管理流程 (Migration Workflow)

### 5.1 正常变更
1.  **本地开发**: 在 `reddit_signal_scanner_test` 上编写并测试 SQL。
2.  **脚本化**: 将验证过的 SQL 保存为 `scripts/migrations/YYYYMMDD_description.sql` 或 Alembic 版本文件。
3.  **代码审查**: 提交 PR，由架构师 Review。
4.  **生产执行**:
    *   先备份 (`make db-backup`)。
    *   执行脚本。
    *   验证 (`make db-audit`)。
5.  **架构同步 (Critical)**: ⚠️
    *   生产变更完成后，**必须**立即执行 `make db-sync-schema`。
    *   该命令会自动导出最新的 Schema 到 `current_schema.sql`。
    *   提交该文件到 Git 仓库。

### 5.2 约束收紧型变更 (Deployment Coordination) ⚠️
当执行“收紧约束”（如禁止大写）的操作时，必须严格遵守以下顺序，否则会导致**生产服务崩溃**：
1.  **代码就绪**：确保应用代码已经包含清洗/适配逻辑。
2.  **部署代码**：**先部署并重启**应用服务。
3.  **清洗历史**：在数据库执行 UPDATE 清洗存量脏数据。
4.  **应用约束**：最后执行 `ALTER TABLE ADD CONSTRAINT`。

---

## 6. 性能禁区 (Performance Don'ts)

1.  **严禁延迟约束 (Deferred Constraints)**：所有外键必须是 `IMMEDIATE`，除非有极其特殊的循环依赖理由。
2.  **严禁宽表全表扫描**：对 `posts_raw` 和 `comments` 的查询必须带时间范围 (`created_at`) 或索引列。
3.  **慎用 JSONB 索引**：不要对高频更新的 JSONB 字段建立 GIN 索引，除非查询频率极高。优先将常查字段提取为实体列。
4.  **避免大事务**：数据抓取批次写入应控制在 100-1000 条/批，避免长时间占用锁。

---

## 7. 监控与维护 (Monitoring & Maintenance)

### 7.1 运维工具箱 (Operations Toolkit) 🆕
为简化日常运维，项目已在 `Makefile` 中集成标准化指令：

| 指令 | 功能描述 | 执行频率 |
| :--- | :--- | :--- |
| `make db-audit` | 全面体检（检查Schema、约束、脏数据、监控指标） | 每周一次 / 变更后 |
| `make db-backup` | 生产数据库全量冷备 (Custom Format) | 每日定时 / 变更前 |
| `make db-sync-schema` | 从生产库导出最新架构到 `current_schema.sql` | 生产变更后立即执行 |
| `make db-clean-automod` | 清理 AutoMod 产生的垃圾帖子 | 每周一次 |
| `make db-monitor` | 强制刷新 `quality_metrics` 监控指标 | 每日一次 |

### 7.2 核心监控指标
*   **定期检查**: 每周检查 `posts_raw` 的膨胀率 (Bloat)。
*   **SCD2 审计**: 检查 `quality_metrics.deduplication_rate`，若低于 0.5 说明 SCD2 逻辑可能失效。
*   **一致性审计**: 运行 `make db-audit` 确保 "Banned Uppercase Communities" 为 0。

---

**SOP 维护人**: 数据库架构组
**最后修订**: 2025-12-01

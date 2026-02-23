# 第一阶段执行记录：语义资产初始化与清洗 (Phase 1 Execution Log)

**日期**: 2025-12-04
**执行人**: Eleven (Architect) & Product Manager
**状态**: ✅ 已完成 (Completed)

---

## 1. 阶段目标
本阶段旨在完成 **SOP v5.1** 架构中的“语义资产化”转型，并将历史数据中的显性噪音进行物理切除，为后续的智能分析打下纯净的数据基础。

## 2. 核心里程碑 (Milestones)

### ✅ 2.1 语义库资产化 (Semantic Assetization)
*   **动作**: 创建 `semantic_concepts` 和 `semantic_rules` 表。
*   **成果**: 成功将 YAML 配置文件中的 **148条** 核心规则（痛点词、黑名单、过滤词）迁移至数据库。
*   **价值**: 实现了“配置即资产”，支持了 `hit_count` 统计，为后续算法优化提供了数据支撑。
*   **相关脚本**:
    *   `backend/alembic/versions/20251203_000002_create_semantic_assets.py` (Schema)
    *   `backend/scripts/migrate_semantics.py` (Migration)

### ✅ 2.2 数据库性能加固 (Performance Hardening)
*   **动作**: 针对 `semantic_rules` 表创建了 **部分索引 (Partial Index)**。
*   **SQL**: `CREATE INDEX ... WHERE is_active = true`。
*   **价值**: 确保在规则库膨胀后，核心查询依然保持 0.1ms 级响应。

### ✅ 2.3 毒瘤社区精准切除 (Surgical Purge)
*   **发现**: 通过侦查脚本发现 `r/etsytrafficjamteam` 存在大量 "Daily Thread" 互刷流量行为，严重污染数据。
*   **动作**: 执行物理删除脚本，级联清除该社区的 600+ 帖子及元数据。
*   **教训**: 必须区分“垃圾 Help”（互刷）和“有价值 Help”（痛点求助）。我们成功保住了后者。
*   **相关脚本**: `backend/scripts/purge_toxic_community.sql`

### ✅ 2.4 垃圾词立法封杀 (Spam Legislation)
*   **动作**: 基于侦查结果，新增 **15条** 垃圾过滤规则。
*   **关键词**: `crypto`, `nft`, `onlyfans`, `discount`, `giveaway`, `promo` 等。
*   **权重**: 设定为负分（-0.5 ~ -1.0），在评分时自动降权。
*   **相关脚本**: `backend/scripts/add_spam_rules.py`

---

## 3. 工具链封装 (Toolchain)

为了将临时战果固化为长期能力，我们将以下脚本封装至 `backend/scripts/maintenance/`：

| 脚本名 | 用途 | 运行频率 |
| :--- | :--- | :--- |
| `mine_potential_spam.py` | **深度噪音挖掘**。基于 N-gram 和域名分析发现新垃圾词。 | 每月一次 |
| `seed_spam_rules.py` | **规则导入工具**。将发现的垃圾词批量入库。 | 按需执行 |
| `audit_noise_level.sql` | **SQL 审计模版**。快速统计负分贴和重复标题。 | 每周巡检 |
| `commit_new_spam.sql` | **单点封杀工具**。用于快速将某个域名或关键词加入黑名单。 | 发现即执行 |
| `fix_duplicate_current_v2.sql` | **SCD2 修复神器**。解决并发写入导致的 Duplicate Current Version 问题。 | **仅在数据库连接爆炸时使用** |

## 5. 应急事件记录 (Incident Log 2025-12-04)

*   **事件**: 数据库连接耗尽 (`Too many clients`)，导致回填脚本中断。
*   **根因**: 并发回填引发 Race Condition，导致 `posts_raw` 表出现 1.1万条重复的 `is_current=true` 记录，进而导致 `posts_latest` 物化视图刷新死锁，Celery Worker 无限重试打满连接池。
*   **处置**:
    1.  优雅停止 Celery Worker。
    2.  执行 `backend/scripts/maintenance/fix_duplicate_current_v2.sql` 清洗脏数据。
    3.  手动刷新视图 `REFRESH MATERIALIZED VIEW posts_latest`。
*   **结论**: 在高并发写入场景下，必须警惕 SCD2 触发器的副作用，必要时需手动清洗。

---

## 6. 遗留问题与下一步 (Next Steps)

*   **待优化**: `mine_potential_spam.py` 的算法仍有提升空间（如增加符号密度分析），目前产出主要集中在通用词，需进一步调优。
*   **下一步 (Phase 2)**: 启动 **R-F-E 战略校准**，利用清洗后的 12 个月数据，重新计算社区价值，实施动态调度。

---

**文档维护**: Reddit Signal Scanner Team

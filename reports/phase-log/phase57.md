# phase57：对齐《数据清洗打分规则》到“以代码 + 本地生产库”为准（表/字段可一一对应）

## 这次要解决什么
Key 要求“以代码发现为基准”，把清洗/打分文档补齐到能和当前仓库、当前本地生产库（`localhost:5432/reddit_signal_scanner`）一一对应。

旧文档存在 4 类偏差：
- 把“物理删除”写成真删，但实际是 **拦截进 `posts_quarantine` 留证据**
- 把“Duplicate 直接删”写成触发器行为，但实际是 **后置标记/归并（`is_duplicate/duplicate_of_id`）**
- 把“3 年归档”写成固定规则，但实际是 **按保留期归档 SCD2 历史版本（默认常见 90 天）**
- 没讲清楚“主口径在哪”：下游筛核心/实验优先看 **`post_scores_latest_v`**，不是只看 `posts_raw.value_score`

## 做了什么

### 1) 更新清洗/打分规范（以 DB Atlas 对齐字段名）
- 更新 `docs/sop/数据清洗打分规则v1.0规范.md`
  - 升级到 **v1.2（DB 对齐版）**，并写死“唯一真相”：字段名以 `docs/2025-12-14-database-architecture-atlas.md` 为准
  - 修正 Layer 1：
    - Ghost/Short：明确为“拦截入库 → `posts_quarantine`”，不是“物理删除”
    - Duplicate：明确为“后置标记/归并”，不是触发器当场删
    - Archive：明确为“归档 SCD2 历史版本（is_current=false）按 retention_days”，不是“3 年固定”
  - 修正 Layer 3/4（口径钉死）：
    - 入库粗分：`posts_raw.value_score/business_pool`（触发器写，兼容口径）
    - 正式评分主口径：`post_scores` → `post_scores_latest_v`（下游筛 core/lab/noise 优先看这个）
    - 评论同理：`comments.value_score/business_pool` + `comment_scores_latest_v`（如有数据）
  - 把“自动化机制”补齐为真实三层：
    - DB 触发器：posts/comments 入库守门（含归一化/SCD2）
    - Celery 规则评分：`tasks.analysis.score_new_posts_v1` 写 `post_scores`（rulebook_v1）
    - 可选二次加工：AI 精修脚本（Gemini/OpenRouter/本地 LMStudio）、噪声联动、归档、重复标记
  - 更新查询示例：改为优先使用 `post_scores_latest_v`（主口径）

## 验收点（人工核对）
- `docs/sop/数据清洗打分规则v1.0规范.md` 能回答三句话：
  1) “入库时 DB 做了什么清洗/拦截？”（posts_quarantine/触发器/SCD2）
  2) “下游选 core/lab/noise 应该查哪张表？”（post_scores_latest_v）
  3) “重复/归档/噪声联动是当场做还是后置做？”（后置标记/归档函数/联动脚本）


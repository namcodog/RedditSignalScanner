# Phase 27 - run_id“增强版”（独立列 + 索引）维护窗口评估（只读评估）

日期：2025-12-17  
范围：仅评估，不执行任何线上/生产 DDL；以“**不影响现有正常业务**”为唯一原则。

## 一句话结论

把 run_id 从 `posts_raw.metadata` 升级成独立列（UUID）是好事，而且**可做到几乎零停机**：  
“加列”只需要非常短的表锁；“建索引”用 `CONCURRENTLY` 可在线后台完成，主要成本是 IO/CPU 的额外压力。

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- 现在 run_id 写在 JSONB 的 `metadata` 里：能用，但查询/对账会越来越慢，也不够“硬标准”。
- SOP/运维层面想要稳定对账能力：独立列 + 索引更靠谱。

### 2）是否已精确定位？
- 目标表：`public.posts_raw`（冷库，写入量大，查询也多）。
- 可选扩展：`public.comments`（如果希望把评论也串到同一个 run 里）。

### 3）精确修复方法？
推荐“最小风险、可灰度”的三段式：
1) **先加列（nullable）**：`ALTER TABLE ... ADD COLUMN crawl_run_id uuid NULL;`
2) **再并发建索引（在线）**：`CREATE INDEX CONCURRENTLY ... WHERE crawl_run_id IS NOT NULL;`
3) **最后改写入**：应用侧把新 run_id 同时写进独立列（保留 metadata 兼容一段时间）。

> 不建议一上来就做：NOT NULL、强制外键、全量回填（这些都会把“维护窗口”变长/变危险）。

### 4）下一步做什么？
- 先在目标环境跑“只读评估 SQL”拿到表大小与写入高峰，决定窗口长度。
- 选择上线方案：
  - 只做 `posts_raw`（最小面，最快落地）
  - 或 `posts_raw + comments`（更完整，但 `comments` 更大，索引更久）

### 5）这次评估的效果是什么？
- 给出可落地的“最小停机”路线，和需要关注的唯一风险：并发建索引期间的资源占用。

---

## 本地库体量参考（只读）

> 说明：这些数字来自本地 `reddit_signal_scanner`，生产以实际查询为准。

- `posts_raw`：约 **1.2 GB**（表+索引），行数约 **18.7 万**  
- `comments`：约 **7.8 GB**（表+索引），行数约 **368 万**  
- `posts_hot`：约 **478 MB**

---

## 维护窗口建议（大白话）

### 你真正需要“窗口”的只有两件事
1) **保证没有长事务**（否则 `ALTER TABLE` 拿不到锁，会一直等）。  
2) **尽量暂停写入者**（比如 Celery worker），避免并发建索引期间把 DB 压力叠满。

### 建议窗口长度（保守口径）
- **加列**：一般秒级完成（但会被长事务拖延，所以建议预留 5–10 分钟“排队+确认”）。
- **并发建索引**：不需要停机，但建议放在低峰（可能持续几分钟到几十分钟，取决于表大小/磁盘/写入压力）。

---

## 只读评估 SQL（线上/生产先跑这些再定窗口）

1) 看表大小（决定索引时间的粗上限）
```sql
SELECT
  relname,
  pg_size_pretty(pg_total_relation_size(oid)) AS total_size
FROM pg_class
WHERE relname IN ('posts_raw','comments');
```

2) 看写入是否繁忙（决定要不要先停 Celery）
```sql
SELECT relname, n_live_tup, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE relname IN ('posts_raw','comments');
```

3) 看是否有长事务（决定 `ALTER TABLE` 会不会卡住）
```sql
SELECT pid, state, now()-xact_start AS xact_age, query
FROM pg_stat_activity
WHERE xact_start IS NOT NULL
ORDER BY xact_age DESC
LIMIT 20;
```


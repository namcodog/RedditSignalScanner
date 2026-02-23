# 运维快捷卡（值班/PM 简版）

目的：一页掌握日常必做与紧急处理。

- Day 1 必做（必须打开）
  - 评论抓取：确保 `comments` 表有新增（posts 之外，评论字段/作者/时间）
  - 夜间回填：开启夜间批补，第二天早上验收字段齐全
  - 快检命令：`make dev-golden-path` → `make test-backend` → 查看 `reports/local-acceptance/*`

- 快速验收（报告样本要素）
  - P/S 比：有值（非 None），来自 `content_labels`（评论）
  - 痛点簇：样本≥2 且 ≥80% 有 samples（优先评论）
  - 核心战场推荐：Top 社区≥3（排序已考虑版规友好度/增长等）

- 常见问题与开关
  - Reddit 限流：调低 `REDDIT_RATE_LIMIT` 或延长 `REDDIT_RATE_LIMIT_WINDOW_SECONDS`
  - 评论抓取节流：`GLOBAL_RATE_LIMITER` 参数，必要时夜间加大窗口
  - LLM 不可用：受控摘要会回退，验收分下降但不阻断

- 观察面板（SQL）
  - 最近 24h 评论数（按社区）：`SELECT subreddit, COUNT(*) FROM comments WHERE created_utc>=NOW()-INTERVAL '1 day' GROUP BY subreddit ORDER BY 2 DESC;`
  - 痛点标签分布：`SELECT category, aspect, COUNT(*) FROM content_labels GROUP BY 1,2;`
  - 版规友好度快照：`SELECT subreddit, moderation_score FROM subreddit_snapshots ORDER BY captured_at DESC LIMIT 20;`

- 快速恢复
  - 抓取异常：重启后台 `make dev-backend`，检查 `logs/` 与 `GLOBAL_RATE_LIMITER`
  - DB 不一致：执行 `make db-upgrade`，必要时 `make db-migrate MESSAGE="hotfix"`


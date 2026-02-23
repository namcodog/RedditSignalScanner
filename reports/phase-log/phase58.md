# phase58：把“启动 Celery + 下一步该做什么”做成 DB-aware 的智能工作流（一键可重复）

## 这次要解决什么
Key 需要一个“别靠记忆/别靠口头”的启动方式：看一眼本地生产库（`reddit_signal_scanner`）就能知道：
- 现在是不是断供了（posts_hot / posts_raw 有没有继续往前写）
- 应该起哪些 worker（巡航/回填/探针各自独立，不互抢）
- 启动后该看什么指标来确认“真的恢复供货了”

## 做了什么

### 1) 新增一个“DB 现状 → 启动建议/一键启动”的脚本
- 新增 `backend/scripts/smart_crawler_workflow.py`
  - 默认 dry-run：只读 DB、输出快照 + 建议，不启动任何进程
  - `--apply`：按建议启动 Celery Beat + 分队列 Worker（patrol/bulk/probe）
  - 输出固定的“下一步检查”口径：1~3 分钟后看 `posts_raw.max(fetched_at)`

### 2) 把“启动命令”收口到 Makefile（读者只记 2 条命令）
- 新增 Make 入口：
  - `make crawler-smart-status`
  - `make crawler-smart-start`
- Make 入口优先使用 `.venv/bin/python`（避免系统 python 缺依赖导致跑不起来）

### 3) 防止多 worker 启动时“重复触发巡航 bootstrap”造成重复下单
- 调整 `Makefile`：
  - `start-worker` / `start-worker-bulk` / `start-worker-probe` 默认带 `DISABLE_AUTO_CRAWL_BOOTSTRAP=1`
  - 口径：只有 `patrol_queue` worker 才负责自动触发首轮巡航心跳；其他 worker 不要抢这个动作

### 4) 文档补一段“推荐启动方式”
- 更新 `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`：
  - Runbook 增加“一键智能启动”两条命令（status/start）

### 5) 测试先行：把“建议逻辑”做成可单测的模块
- 新增 `backend/app/services/ops/smart_crawler_workflow.py`
- 新增测试 `backend/tests/services/ops/test_smart_crawler_workflow.py`

## 验收点（人工核对）
- `make crawler-smart-status` 能输出 DB 快照（posts_raw/posts_hot/comments 最新时间、cache/pool 规模、run/targets 是否有数据）
- `make crawler-smart-start` 能在 `logs/` 下生成并追加：
  - `logs/celery_beat.log`
  - `logs/celery_patrol.log`
  - `logs/celery_bulk.log`
  - `logs/celery_probe.log`（只有 probe 需要时才会启动）
- 重复执行 `make crawler-smart-start` 不会疯狂重复起进程（脚本会先检测已有 celery 进程再启动）


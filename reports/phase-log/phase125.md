# Phase 125 - 本地三库制落地：金库 / Dev / Test + 清理临时库（防再混乱）

日期：2026-01-20

## 目标（说人话）
把本地数据库从“很多库混在一起、容易连错、容易污染”收口成 **三库制**：
- **金库**：`reddit_signal_scanner`（稳定底座，不随便写）
- **Dev 库**：`reddit_signal_scanner_dev`（本地抓取/回填/分析都写这里，脏了就推倒重来）
- **Test 库**：`reddit_signal_scanner_test`（只给自动化测试用，随时清空/重建都正常）

并且把之前恢复/核查阶段留下的临时库全部清掉，避免你以后一查库就“眼花 + 心态爆炸”。

## 做了什么（按顺序）
### 1) 评估是否要克隆 Dev
- 金库体量约 **6.1GB**（包含 posts/comments/labels/embeddings 等）。
- 结论：**Dev 库直接从金库克隆**，保证 Dev 一上来就“有真实数据可跑”，同时金库保持稳定不被写脏。

### 2) 创建 Dev 库
- 使用模板克隆：`reddit_signal_scanner` → `reddit_signal_scanner_dev`
- 并补齐本地运行账号的权限（`rss_app` / `app_user` 能正常读写）

### 3) 默认连接切到 Dev（避免误写金库）
- 修改 `backend/.env`：把 `DATABASE_URL` 的库名从 `reddit_signal_scanner` 切到 `reddit_signal_scanner_dev`
- 结果：你本地跑服务/worker 默认就写 Dev，不会把新抓取的数据直接写进金库。

### 4) 删除临时库（只保留三库）
已删除（都是恢复/核查过程用的临时库）：
- `rrs_backup_check_final`
- `rrs_backup_check_phase_e`
- `rss_restore_20251222`
- `temp_restore_db`
- `reddit_signal_scanner_corrupted_20260120_201546`（旧的跑偏库，已删；证据仍在 `backups/local_snapshot_before_restore_20260120_194024.dump`）

## 当前状态（你现在不会再乱）
现在只剩三套项目库（加系统库 `postgres/template0/template1`）：
- `reddit_signal_scanner`（金库，约 6.1GB）
- `reddit_signal_scanner_dev`（Dev，约 6.1GB）
- `reddit_signal_scanner_test`（Test，约 18MB）

并且 `backend/.env` 已默认指向 Dev：
- 本地抓取/回填/分析 → 写到 `reddit_signal_scanner_dev`
- 金库 `reddit_signal_scanner` 只作为“基准对照/验收/回放”

## 建议的工作纪律（防再翻车）
1) **任何会写库的动作**（抓取/回填/打分/生成报告）默认只跑 Dev。
2) 只有当你明确说“这批数据过闸门、可以升金”，才做一次受控升级（Dev → Gold）。
3) 测试永远只用 `reddit_signal_scanner_test`，不要把它当数据资产库。


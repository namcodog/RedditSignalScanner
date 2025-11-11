# Phase 10 — M1 实施记录（Spec 009）

日期：2025-10-30

## 变更摘要
- 数据基线：新增 `backend/data/top1000_subreddits.json`，`CommunityPoolLoader` 支持将 top1000 与 seed 合并去重（seed 优先）。
- 抓取策略外置：新增 `backend/config/crawler.yml` 并在 `crawler_task.py` 读取，生效于批大小/并发/limit/排序/时间窗；新增 `make crawler-dryrun` 打印生效策略。
- 报告端点：`GET /api/report/{task_id}/communities` 现在返回完整 `sources.communities_detail`；导出端点改为 `GET /api/report/{task_id}/communities/export`（JSON）与原 CSV 下载保留。
- 内容门禁：`backend/scripts/content_acceptance.py` 增加中性比例区间（10–40%）与社区纯度断言（Top 类目主类占比≥80%）。
- 前端引导：在 `frontend/src/pages/InputPage.tsx` 增加“自然语言结构化输入”提示文案（不改交互）。

## 验收要点
- Top1000 合并：`make seed-import-json` 后应能看到 Pool 数量≥原始 seed；`admin-pool-count` 可核对数量与优先级。
- 策略外置：`make crawler-dryrun` 能打印生效策略；`make crawl-seeds` 按策略运行（并发/limit/时间窗/排序）。
- 社区清单：`make report-communities TASK_ID=...` 获取的 JSON 为完整清单（非仅 Top 5）。
- 门禁扩展：`make content-acceptance` 输出结果包含 `neutral_range_ok` 与 `purity_ok` 字段，并计入得分。

### 评分流水线（M1 核心）
- 运行命令：`make score-crossborder LIMIT=1000 THEMES=what_to_sell,how_to_sell,where_to_sell,how_to_source TOPN=200`
- 产物：
  - `backend/data/top5000_subreddits_scored.csv`（当前数据行≈1000，含表头共≈1001 行）
  - `reports/local-acceptance/crossborder-what_to_sell-top200.csv`
  - `reports/local-acceptance/crossborder-how_to_sell-top200.csv`
  - `reports/local-acceptance/crossborder-where_to_sell-top200.csv`
  - `reports/local-acceptance/crossborder-how_to_source-top200.csv`
- 配置：
  - `backend/config/crossborder_scoring.yml`（采样/排序、权重、门槛与 spam 关键词）
  - `backend/config/lexicons/cross_border/*.yml`（四主题词袋）
- 客户端稳健化：`backend/app/services/reddit_client.py` 对 403/404 视为空并降级日志；速率/并发/超时均可在 `backend/.env` 调整。

### 测试与质量
- 新增单元测试：
  - `backend/tests/scripts/test_score_crossborder.py`（A/B/C 分项、权重缩放、词袋与输入解析、断点续跑基础）
  - `backend/tests/services/test_reddit_client_robustness.py`（403/404 视为空集）
- 运行：`cd backend && pytest -q tests/scripts/test_score_crossborder.py tests/services/test_reddit_client_robustness.py`


## 统一反馈四问
1) 发现了什么问题/根因？
   - Pool 基线缺 Top1000，策略不可配置，端点只返回 Top 列表，门禁未覆盖中性比例与纯度。
2) 是否已精确定位？
   - 是。对应文件：`community_pool_loader.py`、`crawler_task.py`、`reports.py`、`content_acceptance.py`、`InputPage.tsx`。
3) 精确修复方法？
   - 已按上文落地，均有回退与容错（cfg 缺失走默认、合并失败不阻断）。
4) 下一步做什么？
   - 进入 M2：实体识别流水线与“实体榜单”；门禁增加实体覆盖阈值；并完善导出。

## 验收结果（打分与清单）
- 评分脚本可在本地离线（仅读取种子清单）+ 在线采样混合模式运行；403/404 社区不影响整体。
- 四榜单 CSV 均已生成，门槛参数可在 `crossborder_scoring.yml` 调整（放宽后命中率显著提升）。
- `top5000_subreddits_scored.csv` 数据行>=1000；支持 `--resume` 断点续跑合并写出。

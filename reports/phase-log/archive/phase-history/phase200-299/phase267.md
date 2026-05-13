# Phase 267 - Round 5 深度审计（API 层 + 高风险脚本）

## 目的
- 开始 Round 5，只做只读深审，不改业务代码
- 把 API 层和高风险脚本里“看起来正常、实际上会带歪结果或写错库”的问题一次查清

## 审计范围

### API
- `backend/app/api/v1/endpoints/reports.py`
- `backend/app/api/routes/admin_community_pool.py`
- `backend/app/api/routes/reports.py`

### Scripts
- `backend/scripts/report/`
- `backend/scripts/import/`

## 扫描结果（健康卡片）

### API 层
- `api/v1/endpoints/reports.py`
  - `956` 行
  - `29` 处 `except`
  - `4` 处 `type: ignore`
  - `6` 处 `.execute(`
- `api/routes/admin_community_pool.py`
  - `974` 行
  - `5` 处 `except`
  - `0` 处 `type: ignore`
  - `8` 处 `.execute(`
- `api/routes/reports.py`
  - `838` 行
  - `28` 处 `except`
  - `4` 处 `type: ignore`
  - `6` 处 `.execute(`

### Scripts
- `backend/scripts/report/`
  - `8` 个文件
  - `5,368` 行
  - `35` 处 `except`
  - `26` 处 `.execute(`
  - `100` 处 `print(`
- `backend/scripts/import/`
  - `12` 个文件
  - `2,391` 行
  - `32` 处 `except`
  - `18` 处 `.execute(`
  - `77` 处 `print(`

## 核心发现

### P0 - 报告社区导出会把“整个活跃社区池”冒充成“本次报告社区清单”
- 文件：
  - `backend/app/api/v1/endpoints/reports.py`
  - `backend/app/api/routes/reports.py`
- 证据：
  - `export_communities(scope="all")` 在拿不到真实 `sources.communities_detail` 后，不是明确降级，而是把 `CommunityPool.is_active=true` 的社区全量塞进返回值
  - 代码里自己已经写了“完整导出近似”
- 问题本质：
  - 用户要的是“这份报告实际用了哪些社区”
  - 现在接口可能返回“系统当前有哪些活跃社区”
  - 这会把“报告事实”跟“系统治理状态”混成一类
- 风险：
  - 前端/导出 CSV 会误以为这些社区都参与了当前分析
  - 审计和复盘会被带偏

### P0 - 高风险导入/恢复脚本没有三库护栏，也没有 dry-run
- 文件：
  - `backend/scripts/import/import_166_crossborder_communities.py`
  - `backend/scripts/import/import_hybrid_scores_to_pool.py`
  - `backend/scripts/import/restore_pool_hybrid.py`
- 证据：
  - 都直接走 `SessionFactory()`
  - 没有 `ALLOW_GOLD_DB`
  - 没有校验当前库是不是 `*_dev / *_test`
  - 没有 `--dry-run`
- 问题本质：
  - 这类脚本一旦在错环境跑起来，会直接改池子
  - 跟仓库现在已经定下的“三库规则”不一致
- 风险：
  - 可以误写金库
  - 可以在没有审阅的情况下大批量改 `community_pool`

### P0 - `restore_pool_hybrid.py` 会把 ghost 社区重新拉回池子，直接冲撞 Round 3 治理口径
- 文件：
  - `backend/scripts/import/restore_pool_hybrid.py`
- 证据：
  - 脚本明确写了“DB 中有但 CSV 没有的社区（Ghost Communities）也进行抢救性恢复”
  - 规则是 `posts_raw` 里帖子数大于 100 就恢复为 `semantic`
- 问题本质：
  - Round 3 刚把“历史垃圾 / 历史壳 / 候选社区 / 生效社区”分清
  - 这个脚本却允许仅凭 `posts_raw` 数据量把 ghost 社区重新写回 `community_pool` / `community_cache`
- 风险：
  - 会重新污染社区池
  - 会把“历史数据存在”错误地解释成“现在应该重新激活”

### P1 - 报告社区明细接口会静默降级，但不告诉调用方
- 文件：
  - `backend/app/api/v1/endpoints/reports.py`
- 证据：
  - `get_report_communities()` 读取底层 analysis 失败后，会自动退回 `top_communities`
  - 但接口响应里没有 `source` / `degraded_reason`
- 问题本质：
  - “完整社区明细”和“Top 社区近似清单”不是一回事
  - 现在调用方拿不到这个区别

### P1 - 报告下载 fallback 会把内部异常原文暴露给前端
- 文件：
  - `backend/app/api/v1/endpoints/reports.py`
  - `backend/app/api/routes/reports.py`
- 证据：
  - `download_report()` 在导出失败时会回退 JSON
  - 同时把 `str(exc)` 直接塞进 `X-Export-Error`
- 问题本质：
  - 这是内部异常文本外泄
  - 用户拿不到可执行修复建议，只会拿到一串内部错误
- 风险：
  - 泄露内部实现细节
  - 不利于统一错误协议

### P2 - 旧版 `api/routes/reports.py` 和新版 `api/v1/endpoints/reports.py` 长期复制漂移
- 事实核查：
  - 当前主应用真正挂载的是 `api/v1/endpoints/reports.py`
  - 旧版 `api/routes/reports.py` 不是主入口
  - 但新版还从旧版 import 共享限流器，测试也还直接引用旧版模块
- 风险：
  - 同一套“报告接口逻辑”维护两份 800~900 行代码
  - 很容易出现一边修了，一边还留着旧行为
- 备注：
  - 旧版 `download_report()` 里甚至还存在“服务取报告失败时返回空 CSV 成功响应”的更坏逻辑
  - 这条因为目前不是主入口，先记为漂移风险，不当成本轮线上主问题

## Round 5 的统一口径
- Round 5 解决的不是“接口能不能返回数据”
- 而是：
  - API 不许把“近似数据”冒充成“真实报告事实”
  - 高风险脚本不许绕过三库规则直接写库
  - 恢复脚本不许把旧 ghost 社区重新拉回生效池
  - 新旧两套 API 逻辑不能继续长期分叉

## 建议的修复顺序
1. 先修 `api/v1/endpoints/reports.py`
   - `export_communities(scope=all)` 只返回真实报告社区
   - 明确 `source / degraded_reason`
2. 再修 `get_report_communities()`
   - 不再静默把 Top 社区冒充完整社区明细
3. 再给高风险导入/恢复脚本加护栏
   - 只允许 Dev/Test
   - 默认 dry-run
   - 金库必须显式拒绝
4. 最后处理 `api/routes/reports.py`
   - 收口到单一真相实现
   - 旧逻辑不要再继续漂

## 结论
- Round 5 已完成深度审计
- 当前最深的问题不是“接口报错”，而是：
  - 报告 API 会把近似结果说成真实事实
  - 高风险脚本会在没有护栏的情况下直接写库
- 下一步应进入 Round 5 深修

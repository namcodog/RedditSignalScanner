# Phase 457 - 开放题 warzone 路由收口，暴露第二层 evidence 根因

## 本轮目标
- 不再继续修报告层补丁
- 按诊断方案，直接改分析主链中段入口
- 先验证开放题是否还会掉进错误的金融/加密社区宇宙

## 已完成

### 1. 开放题 warzone 路由第一段已落地
- 在 `backend/app/services/analysis/analysis_engine.py` 新增：
  - `OpenTopicRoute`
  - `WarzoneClassifier` 驱动的开放题路由
  - 8 大领域 seed communities
  - 社区级 warzone 过滤
- 对 `topic_profile is None` 的开放题：
  - 先猜 warzone
  - 只允许该 warzone 的 seed / 匹配社区进入后续链路

### 2. 中英关键词桥接已补上
- 扩展 `_augment_keywords()` 的中文触发词：
  - 家庭育儿
  - 咖啡
  - 省钱/订阅
  - 户外/旅行
  - 家居
  - EDC
- 目的：
  - 让中文开放题也能触发正确的 warzone classifier
  - 不再只有 PayPal 这种英文/品牌强题能命中入口过滤

### 3. 定向测试通过
- `pytest tests/services/analysis/test_analysis_engine.py -q -k 'open_topic_route or query_focus_filter'`
- 结果：`4 passed`

## live 横向复检结果

### 正向结果：社区宇宙已经被拉回来了
- 家庭题新任务：
  - `835b5ce7-7745-4969-bae1-4f1aab95aae0`
  - `6262f8d2-570f-4b91-bbe8-f1611e9bc951`
- `sources.communities` 已从错误的金融/加密社区切回：
  - `r/NewParents`
  - `r/daddit`
  - `r/beyondthebump`
  - `r/Parenting`
  - `r/parenting`
  - `r/BabyBumps`

### 新暴露的更深层问题
- 虽然 warzone 已正确，但 `pain_points` 仍退回：
  - `关键痛点 1`
  - `关键痛点 2`
  - `关键痛点 3`
- 第一条 evidence 也仍偏泛：
  - `Are all these newborn toys actually necessary?`
- 这说明：
  - 第一层根因 `社区路由错误` 已被击穿
  - 第二层根因转移到 `evidence selection / query focus`

## 诊断结论
- 当前 `_apply_query_focus_filter()` 仍然基本是 PayPal 特化逻辑
- 对家庭/咖啡/省钱/户外这类开放题，系统虽然进了正确领域，但还不会继续在领域内“抓对帖子”
- 所以下一步必须继续改：
  - 从 `抓对社区` 进入 `抓对证据`

## 下一步
- 重构 query focus contract：
  - 不再只识别 PayPal
  - 对 8 大领域开放题，从产品描述中提炼痛点簇和动作簇
  - 让 evidence selection 在正确 warzone 内继续收窄到用户真正关心的问题

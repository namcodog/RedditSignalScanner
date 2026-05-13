# Phase 813: hot 真实争议占比方案重评估与合同覆盖

## 发现

- 旧版方案默认把 `hot` 真实争议占比落到 `comments / comment_llm_labels` 聚合，这和“小程序独立线”边界冲突。
- 当前小程序发布链真正稳定可复用的输入是：
  - `source_link`
  - `push_mini_snapshot.py`
  - `mini_snapshot.py`
  - `reddit_client.fetch_post_comments(post_id, ...)`
- 当前 `hot` 图表的模板感根因未变：
  - `backend/app/services/hotpost/hot_controversy_chart.py` 仍在输出固定桶位近似值。

## 是否需要修复

- 需要，但这次先修的是方案和合同，不是代码。
- 原因很直接：如果继续沿着 dev DB 路线实现，最终会把小程序链和内部分析链绑死，违背当前范围。

## 精确修复方法

- 覆盖设计文档：
  - `docs/superpowers/specs/2026-04-14-hot-real-controversy-ratio-design.md`
- 覆盖计划与判断：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

新版固定口径：

1. 只做 `hot`
2. 不依赖 dev DB
3. mini 发布前按 `source_link` 直抓 Reddit 评论
4. 对单张卡评论样本做一次性 `support / oppose / neutral` 汇总
5. 结果写回现有 `controversy_chart`
6. 不再允许固定桶位回退

## 下一步系统计划

1. 先按新合同补测试：
   - `test_hot_comment_sample.py`
   - `test_hot_controversy_llm.py`
   - 更新 `test_push_mini_snapshot.py`
2. 再实现：
   - `hot_comment_sample.py`
   - `hot_controversy_llm.py`
   - `mini_snapshot.py / push_mini_snapshot.py` 接线
3. 最后跑 mini snapshot 真回填与 spot check。

## 价值

- 这次把“真实争议图”从错误依赖路径上拉回来了。
- 后续实现会直接对准小程序独立发布链，不会再把数据库和小程序链耦死。

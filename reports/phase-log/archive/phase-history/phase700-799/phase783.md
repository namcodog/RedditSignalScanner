# phase783

## 事项

- 把 key-os 里校准完成的 `breakdown thesis quality v1` 口径回灌到桌面项目生产 judge / program
- 只动 `breakdown`，不扩 schema，不新增状态，不碰 `signal / hot`

## 本次改动

- `backend/config/prompt_assets/breakdown_compact_prompt.md`
- `backend/config/prompt_assets/breakdown_field_semantics.md`
- `backend/app/services/hotpost/card_content_generator.py`
- `backend/tests/services/hotpost/test_card_content_generator.py`
- `backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py`

## 实际回灌的规则

- `thesis` 是硬门槛
- 至少 `2` 条原话要共同支撑同一条 `thesis`
- 不能只是更长一点的 `signal`
- 不能是同主题拼盘
- `title / summary_line / thesis / why_now` 不能重复同一个意思
- `why_now` 只回答：为什么把这几条放一起看，判断升级了
- 保留 `rewrite` 边界，不把所有边界样本都抬成 `publish`
- `评估标准迁移`、`trade-off 本身已经讲清` 这两类升级逻辑可以成立

## 程序侧回灌

### 1. prompt 资产

- `breakdown_compact_prompt.md`
  - 收进了 thesis 硬门槛、双引文共同支撑、`不是更长一点的 signal`
  - 没继续往里堆抽象说明
- `breakdown_field_semantics.md`
  - 明确各字段分工
  - 把“同主题拼盘”“字段抢活”“边界升级逻辑”写成生产口径

### 2. program / judge

- `card_content_generator.py`
  - `should_be_breakdown()` 现在会拒绝：
    - thesis 站不住
    - quote 支撑不够
    - `quote_pack` 无法构成共同支撑
    - 与 signal/current_card 高度重叠、只是更长一点的 signal

## 验证

### 定向回归

- `pytest backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py backend/tests/services/hotpost/test_card_content_generator.py -q --tb=short -p no:schemathesis`
- 结果：`72 passed`

### prompt 预算

- `build_reddit_guide_prompt_prefix(mode_name="跨区热议")`
- 长度：`2805`
- 结果：已回到门槛内

### lane / data 面

- 当前 `breakdown suggestion`：`0`
- 当前 `write` draft：`29`
- 没有出现因为回灌导致的异常膨胀

### 6 条 mimo spot check

- 结果文件：
  - `backend/tmp/breakdown-v1-spotcheck-6.json`
- 抽样范围：
  - 增长 `3`
  - 电商 `3`
  - 当前本地没有新的 AI `write` draft，所以这轮没有 AI 样本

- 判读：
  - 明显可过 `publish` 的：`4 / 6`
    - `draft-group-business-growth-ops-1d02bb884b`
    - `draft-group-business-growth-ops-473243edb7`
    - `draft-group-business-growth-ops-b86309e29a`
    - `draft-group-ecommerce-sellers-2f86027da3`
  - 仍应保守留在 `rewrite` 的：`2 / 6`
    - `draft-group-ecommerce-sellers-33704d4315`
    - `draft-group-ecommerce-sellers-b57af02513`

- 这两条保守留 `rewrite` 的原因：
  - 判断开始往消费心理/避坑逻辑上抬
  - 还存在“长一点的 signal / 同主题拼盘”的风险
  - 没有被这轮回灌错误抬成强 `publish`

## 结论

- `breakdown thesis quality v1` 已成功回灌到生产口径
- 回灌后：
  - 没有异常扩张
  - `rewrite` 边界还在
  - `06/07` 类升级逻辑已经能落到生产表达里
  - `05/08` 类边界样本没有被误抬
- 建议：正式启用

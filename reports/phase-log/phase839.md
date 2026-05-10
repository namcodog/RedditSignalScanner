# phase839

## 时间
- 2026-04-15

## 主题
- 统一 growth 回灌审计口径

## 结论
- 当前项目的主合同，已从 `fixed-count programming` 切到 `value-threshold publishing`
- `15` 现在只是窗口，不再是硬 veto
- 旧 `15-baseline` 不再作为 growth 回灌的硬性否决条件

## 旧基线失效范围
- 不再用旧模板硬判：
  - `9 / 4 / 2`
  - `5 / 5 / 5`
  - 某个旧 `breakdown` 位必须保留

## 旧基线仍保留的硬约束
- freshness gate
- named topic budget
- 发布链稳定性
- 首页显示层不能炸
- `snapshot / cloud_db / miniRelease` 同步链不能炸
- 不允许因为优化把系统重新打回旧世界

## growth 回灌的新审计口径
- 不再优先看：
  - hot 是不是变成 5
  - breakdown 是不是少了 1
  - 有没有碰掉旧 baseline 槽位
- 改为优先看：
  - `organic_new_intake_share`
  - `organic_old_draft_count`
  - `funnel_publish_keyword_count`
  - `growth_new_discovery_count`
  - `candidate -> publish` 穿透是否增强
  - 新社区 / 新发现感是否增强
  - 是否破坏 freshness / named topic / 发布链 / 首页显示链

## 对 growth P1 purity cleanup 的正式判定
- 判定：通过
- 结论：可以带入当前上线版本

## 项目侧统一一句话
- growth 这轮回灌不是在破坏旧 `15-baseline`，而是在新发布口径下，把 `organic-discovery / funnel-conversion` 从“刚过最低 winner 线”进一步提纯成“可直接上线的更干净版本”。

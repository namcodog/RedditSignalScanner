# phase1079

## 这轮达到的目的

完成 V13 semantic 出卡前增强，并把 semantic brief 纳入 review 治理资产。

## 当前状态变化

semantic schema 已加入 `lane_specific`，覆盖 hot / signal / breakdown 判断位。
`evidence_basis` 已改成 `claim / community / quote_text / permalink` 结构化对象。
新增 `uncertainty`，显式传递 confidence、缺失证据、弱点和单帖风险。
V13 shadow JSON / MD、published shadow plan / report、review CSV 现在都会保留 semantic brief 或摘要。

## 还没完成什么

这轮没有发卡、没有刷新小程序快照；下一步需要用真实补卡样本抽查 brief 是否读偏。

## 下一步做什么

出这两天卡前，先跑少量 V13 shadow 或直接 review 新卡 semantic brief，再进入正式发布链。

# Hotpost V13 Published Shadow Refresh 审核包

这份报告只读生成，不改 drafts / published / release，也不切默认生产流量。

- selected: `1`
- generated: `1`
- failed: `0`
- profile: `hotpost_v13_title_standalone`

## 总览

- `signal` `card-cand-business-growth-ops-1stfurr-validate`: 成功，title 残留 `1`

## signal · card-cand-business-growth-ops-1stfurr-validate

- card_type: `validate`
- model route: `deepseek/deepseek-v4-flash -> xiaomi/mimo-v2.5-pro`
- source: https://www.reddit.com/r/ecommerce/comments/1stfurr

**原卡**

- `title`: 卖家现在先看会话回放，不再先猜是哪个环节出错
- `summary_line`: 判断顺序从先猜是哪个环节出错，转成先看20-30个真实会话回放，因为2.1%的转化率意味着问题藏在分析工具看不到的地方。
- `audience`: Shopify卖家，特别是移动端转化率卡在2%左右的
- `why_now`: 有用户发现，所有常规优化都做完后，移动端转化率还是只有2.1%。这说明问题不在表面数据，而在用户实际操作中的误点、缩放失灵等细节。所以，下一步先看的不是调整哪个按钮，而是先看20-30个真实用户的会话回放。
- `detail.pain_point`: 移动端转化率死活上不去，但分析工具里看不出具体原因，只能干着急。
- `detail.target_user_and_scene`: 做Shopify的卖家，在优化完所有已知问题后，发现移动端转化率依然远低于桌面端时。
- `detail.why_test_now`: 原话里有个关键句：“What's add to cart rate mobile vs desktop? if similar rates but lower conversion it's defini”。最硬的证据是‘2.1% with all the obvious fixes done’和‘session replays on mobile specifically watch 20-30 real sessions’。这直接说明，当常规方法失效时，唯一的办法是去看用户到底怎么操作的，而不是继续猜。
- `detail.continue_signal`: 继续看有没有更多卖家开始分享具体的会话回放发现，比如‘rage clicks’或‘broken zoom’的具体案例。
- `detail.stop_signal`: 如果讨论又回到调整按钮颜色、简化表单这些老生常谈，而没人再提会话回放的具体发现，这条线就失去价值了。

**V13 候选新版**

- `title`: Shopify 卖家移动端转化率卡在 2.1%，放弃猜测，先看 20-30 个用户录屏
- `summary_line`: 判断顺序从‘先猜哪个环节出错’，转成‘先看20-30个真实会话回放’。
- `audience`: 已经做完所有常规优化（如简化表单、调按钮颜色）但移动端转化率仍低的Shopify卖家
- `why_now`: 有卖家遇到2.1%转化率瓶颈，常规优化无效。他发现移动端加购率与桌面端相近，问题可能在结账交互细节。
- `detail.pain_point`: 移动端转化率死活上不去，但分析工具里看不出具体原因，只能干着急。
- `detail.target_user_and_scene`: 做Shopify的卖家，在优化完所有已知问题后，发现移动端转化率依然远低于桌面端时。
- `detail.why_test_now`: 原话里有个关键句：“What's add to cart rate mobile vs desktop? if similar rates but lower conversion it's defini”。最硬的证据是‘2.1% with all the obvious fixes done’和‘session replays on mobile specifically watch 20-30 real sessions’。这直接说明，当常规方法失效时，唯一的办法是去看用户到底怎么操作的，而不是继续猜。
- `detail.continue_signal`: 继续看有没有更多卖家开始分享具体的会话回放发现，比如‘rage clicks’或‘broken zoom’的具体案例。
- `detail.stop_signal`: 如果讨论又回到调整按钮颜色、简化表单这些老生常谈，而没人再提会话回放的具体发现，这条线就失去价值了。

**自动检查**

- changed fields: `4`
- V11 中文顺读 repair 触发问题数：`0`
- V12 高密度残留问题：`2`
- V13 title 修前问题：`0`
- V13 title 修后问题：`1`

  - title: 标题 43 字，太长，不利于一眼读懂。

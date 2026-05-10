# Phase 728

## 本轮发现

- 继续按新 supply contract + 现有 `signal-ops` 真跑运营，没有回到旧世界那套“弱证据也硬发”的做法。
- 这轮把 3 张可救 draft 收成可发版本后发布，前台卡片总数从 `84 -> 87`。
- 最新 mini snapshot 已推送到：
  - `release-1c0ba26ab02a`
  - `card_count = 87`
- 当前候选池仍然够厚：
  - `ai-automation = 22`
  - `business-growth-ops = 24`
  - `ecommerce-sellers = 19`
- 现阶段真正的主瓶颈已经不是“没料”，而是：
  - `hot` 前排噪音还偏多
  - 批量 review 吞吐还不够高

## 本轮新发卡片

新增 `3` 张 signal 卡：

- `库存预警不一定要上 ERP，评论区开始拿 Excel 加 WhatsApp 这种轻量拼装先顶上。`
- `不少 FBA 卖家先漏掉的不是订单，而是本来能追回来的赔付款。`
- `做 AI agent 时，评论区开始把优势从代码快不快，挪到谁更懂具体业务。`

## 本轮执行动作

1. 复核两张已 seed draft 和一张新 seed AI draft，判断可救后进入人工收稿。
2. 直接把模板味很重的字段改掉：
   - 去掉 `1 个帖子 / 7 天反复出现` 这类废话 why_now
   - 去掉泛 audience
   - 去掉空泛 pain point
3. 发布 3 张 signal 卡：
   - `draft-cand-ai-automation-1sf0e36-validate`
   - `draft-cand-ecommerce-sellers-1sfd8p9-validate`
   - `draft-cand-ai-automation-1sgc7pm-validate`
4. 推送 mini snapshot，前台快照更新到最新 release。

## 当前盘面

- 已发布总数：`87`
- 最近 queue 前排仍偏吵：
  - `LocalLLaMA / ClaudeCode / Frugal / EntrepreneurRideAlong`
- `hot` lane 还不能靠这些高热帖硬补量，否则会回到：
  - 情绪帖
  - 围观帖
  - 正确的废话

## 结论

- 方向没偏：
  - 进口已经放宽
  - 卡片还能继续增
  - 质量闸门没被拆掉
- 但供卡要真正稳定，下一步该拉的是：
  - 更好的前排排序
  - 更高的批量 review 吞吐
  - 而不是降低发布标准

## 下一步

1. 继续按新 YAML collect。
2. 优先处理能稳发的 `signal`，把单轮出卡从现在的 `3-5` 往 `8-10` 抬。
3. 单独收 `hot` 前排噪音，争取自然长出第 `4 / 5` 张真热点。
4. 不再让弱热点和模板稿占掉 review 时间。

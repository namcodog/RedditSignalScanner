# phase933

1. 这轮达到的目的
- 审计首页为什么没把今天新发布的卡顶到最前，并把根因从“感觉”收成代码级结论。

2. 当前状态变化
- 已确认正式 release 本身按 `published_at` 倒序，新发 `12` 张时间都在最前。
- 已确认真正改变首页顺序的是 mini snapshot 生成链：`_apply_homepage_shelf_mix` 会混排前台窗口，`build_supplement_surface` 会把一部分新卡下沉到 `15天补充`。
- 当前最新 snapshot 里，今天新发 `12` 张只有 `3` 张进了首页首屏前 `30` 位，另有 `4` 张被下沉到 supplement。

3. 还没完成什么
- 还没决定这是不是产品想要的排序策略，还是应该改成“今天新发优先顶前”。

4. 下一步做什么
- 先按运营口径定规则：如果要求“新发优先”，就改 mini snapshot 的首页混排和 supplement 下沉策略，再重推 snapshot。

# phase878

1. 这轮达到的目的
把“后续连续跟 3-5 个 release 看会不会反弹”从口头要求变成项目侧默认能力，不再靠人工临时统计。

2. 当前状态变化
新增 `mini_release_trend_audit.py`、`audit_recent_mini_releases.py` 和 `make hotpost-release-trend-audit`。现在能直接审最近 5 个 release 的 `scope / pack / top community / front30`，并输出 `watching / rebound / stable`。最新 `release-727805c2aaf3` 当前是 `watching`，front30 已无 watch alert，但 full inventory 仍有 `FacebookAds / PPC / BuyItForLife / paid-economics` over-cap。

3. 还没完成什么
这说明系统已经能证明“这轮没有反弹”，但还不能证明“长期已经压稳”；后续还要继续跟 3-5 个新 release，看 latest status 能不能从 `watching` 走向 `stable`。

4. 下一步做什么
后续每轮新 release 后默认跑 `hotpost-release-trend-audit`，持续盯 `scope / pack / top community / front30` 和 `FacebookAds / PPC / BuyItForLife / paid-economics` 是否重新吃满；只有连续几轮不反弹，才能说这套治理真的压稳了。

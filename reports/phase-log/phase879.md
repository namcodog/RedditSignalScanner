# phase879

1. 这轮达到的目的
- 把 `rolling inventory stability` 从手工审计命令压成默认发布后动作。

2. 当前状态变化
- `push_mini_snapshot` 现在每次新 release 后都会自动跑 trend audit。
- `check_mini_release_sync` 新增了 `trend audit guard`，会校验 trend 报告必须跟当前 latest release 对齐。
- 最新 baseline 仍是 `release-727805c2aaf3`，当前 `latest_status = watching`，`remaining_new_releases = 5`。

3. 还没完成什么
- 还没拿到连续 `5` 个新 release 都不反弹的真实证据，所以还不能改成 `stable`。

4. 下一步做什么
- 后续每出一个新 release，默认继续跑 `hotpost-release-trend-audit`，只打库存层，继续看 full inventory 会不会反弹。

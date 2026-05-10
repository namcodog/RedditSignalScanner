# phase914

1. 这轮达到的目的
   把“旧一点但仍有价值的卡怎么给用户看”从口头判断落成解耦实现：主 freshness 不动，新增 `15天补充` 展示面。

2. 当前状态变化
   已新增 `hotpost_mini_surface_v1.yaml`、补充面选择器和小程序 `supplement` 标签页；`mini snapshot / miniRelease / miniFavorites / cloud_db` 已统一到 `release-2aa8efc6b16c`。当前 `card_count = 76`，其中 `main = 64`、`supplement = 12`；原来被主 freshness 挡掉的 `6` 张 AI 卡现在已进入补充面。`trend audit` 也已改成只看主面，最新状态恢复 `stable`。

3. 还没完成什么
   仓库内的快照、bundle 和 `dist-dev / dist-prod` 都已经对齐，但手机真机还需要在微信开发者工具里重新部署 `miniRelease / miniFavorites` 云函数，并用 `dist-prod` 再做一轮预览/真机确认。

4. 下一步做什么
   先完成手机侧云函数部署和真机确认，确认首页出现 `15天补充` 且 6 张 AI 补充卡可见；后续如果还要加别的补充面，只能继续走独立配置和 `surface_bucket`，不回头放宽主 freshness。

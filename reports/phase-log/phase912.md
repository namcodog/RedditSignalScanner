# phase912

1. 这轮达到的目的
   把小程序“本地开发工具”和“手机设备”两条链重新拉开，确认本地继续走本地服务器，手机继续走云端 release。

2. 当前状态变化
   已重新执行 `npm run build:weapp`，当前根项目 `miniprogramRoot` 已回到 `dist-dev/`，开发工具继续直连本地 `127.0.0.1:8006`。同时已产出一次 `npm run build:weapp:prod`，`dist-prod/` 可用于手机预览/上传；当前 cloud db 与小程序快照仍一致指向 `release-d514a1867cd1`，同步检查通过。

3. 还没完成什么
   这轮没有改 `miniRelease / miniFavorites` 云函数代码，所以不需要为了内容更新重传云函数；如果后面动了云函数代码，再单独部署，不要把“内容同步”和“云函数发布”混成一步。

4. 下一步做什么
   后续固定按双轨执行：本地看最新调试结果就跑 `build:weapp`，手机看最新云端结果就跑 `build:weapp:prod` 并导入最新 cloud db；不要再拿 `dist-prod` 充当本地调试包。

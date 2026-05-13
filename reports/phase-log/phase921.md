# phase921

1. 这轮达到的目的
   修正补充面被错误暴露到前端的问题，恢复“补充只在后台分桶，前端不加新 tab”的产品口径。

2. 当前状态变化
   已移除小程序首页 `15天补充` 标签；前端不再请求 `card_type=supplement`。本地与云函数取数都改成：补充卡继续由 `surface_bucket` 管理，但在现有列表里按原有 `lane / card_type` 展示。`tests/api/test_hotpost_clues.py` 11 通过，`cloudfunctions/tests/mini-release.test.mjs` 4 通过；`build:weapp`、`build:weapp:prod` 已重建成功，根项目已恢复 `dist-dev/`。

3. 还没完成什么
   手机真机要看到同一结果，还需要重新部署 `miniRelease` 云函数，并用最新 `dist-prod` 重新预览/上传。

4. 下一步做什么
   在微信开发者工具里重新上传 `miniRelease`，然后确认本地和手机都不再出现 `15天补充` tab，且列表能正常拉卡。

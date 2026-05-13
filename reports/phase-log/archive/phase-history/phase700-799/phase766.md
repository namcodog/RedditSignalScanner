# Phase 766 - 小程序真机详情页 loading 锁死修复

## 发现

- 手机截图里的“正在加载 / 马上就好，请稍等。”不是首页，而是详情页 `velocity` 的 loading 态。
- 根因不在云环境，而在详情页的授权分支：
  - 当 `promptLoginForAccess()` 返回 `bind_phone` 时，页面直接 `return`，但没有把 `loading` 关掉。
  - 真机比本地更容易触发这条链，因为真机的登录/试看状态和本地开发工具不是同一份。
- 手机号绑定页点“继续逛逛”时，如果来源是详情页，会回到旧的详情页实例；旧实例此前保持 `loading=true`，于是用户看到的就是卡死页。

## 修复

- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
  - 在 `cancelled` 分支先关闭 `loading`
  - 在 `bind_phone` 分支明确写入错误提示，并关闭 `loading`
- `hotpost-mini/hotpost-mini-app/src/pages/phone-bind/index.tsx`
  - 新增 `resolveTabRedirect`
  - 当来源是详情页时，点“继续逛逛”不再回到旧详情页，而是直接回首页

## 验证

- `npm run build:weapp:prod`
  - 通过
- `npm run build:weapp`
  - 未通过，但失败点是 Taro 清理 `dist/app.js.LICENSE.txt` 的旧构建问题，不是这次详情页逻辑修复引入的新错误

## 当前判断

- 这次真机打不开，不是“手机端和本地端用了不同 release”，而是“真机更容易走到手机号绑定分支，而该分支把详情页停在 loading”。
- 这类问题后续要优先按“真机状态差异 + 页面状态机”排，不要先怀疑产品态和卡片数据。

## 下一步

- 让用户重新上传体验版后，在手机上复测这条路径：
  - 未登录状态打开第 4 张卡
  - 进入手机号绑定页
  - 点“继续逛逛”
  - 应直接回首页，不再看到详情页永久 loading
- 再测一次：
  - 从手机号绑定页完成绑定
  - 应重新进入详情页并正常打开卡片

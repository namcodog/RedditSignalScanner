# phase975

## 这轮达到的目的
给开发态加了一个“一键把当前测试账号重置成新用户基线”的入口，避免继续手工删云库做验收。

## 当前状态变化
- `miniPoints` 新增 `resetQaState` 动作：按当前 `openid` 清空积分、签到、邀请标记、已看详情记录，并删除该用户的积分流水、邀请关系、收藏记录。
- 个人页开发态入口从“开发调试”改成“重置测试账号”。
- 重置后会同时清掉本地登录态和待处理邀请 token，重新授权后就按新用户首登走。

## 验证结果
- `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-points.test.mjs` 通过（7/7）
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp` 通过

## 下一步做什么
- 重新部署 `miniPoints` 云函数
- 开发态个人页点击“重置测试账号”
- 重新授权登录，验首登 `+60`

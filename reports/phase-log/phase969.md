# phase969

## 这轮达到的目的
修复云开发 `miniAuth` 和 `miniPoints` 在真机运行时找不到 `mini-points-store`，导致授权登录无反应并报 `-504002` 的问题。

## 当前状态变化
- `miniAuth` 不再依赖父目录 `../common/mini-points-store`
- `miniPoints` 不再依赖父目录 `../common/mini-points-store`
- 两个云函数都改为引用各自函数包内的 `./mini-points-store`
- 微信单函数部署时，不再因为公共模块未被打包而直接执行失败

## 验证结果
- `cd hotpost-mini/hotpost-mini-app && node --test cloudfunctions/tests/mini-auth.test.mjs cloudfunctions/tests/mini-points.test.mjs`
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：通过

## 下一步做什么
在微信开发者工具里重新部署 `miniAuth` 和 `miniPoints`，再真机验证：首页点详情后点击授权，不再出现 `-504002`。

# Phase 636 - 小程序真机白屏根因收口与构建护栏落地

## 时间
- 2026-04-06

## 目标
- 把这轮小程序真机白屏问题彻底收口。
- 不只修“这一次能跑”，而是把根因做进构建链路，避免后面每次打包又把问题带回来。

## 发现
- 真机白屏的根因不是首页业务代码，也不是卡片 UI 本身。
- 真正的问题在小程序工程配置：
  - `hotpost-mini/hotpost-mini-app/project.config.json`
  - `hotpost-mini/hotpost-mini-app/project.private.config.json`
- 之前这里的 `es6` / `enhance` 会被保留成错误状态，导致每次重新 `build:weapp` 时，`dist/project.config.json` 又被重新生成成真机不稳定的配置。
- 结果就是：
  - 开发工具里看着像修好了
  - 一重新打包，真机又白屏
  - 问题反复回滚

## 实现
- 把小程序工程源配置改成真机稳定基线：
  - `urlCheck: false`
  - `es6: false`
  - `enhance: false`
  - `minifyWXSS: false`
  - `minifyWXML: false`
- 新增构建护栏脚本：
  - `hotpost-mini/hotpost-mini-app/scripts/ensure-weapp-config.cjs`
- 把护栏接进小程序打包脚本：
  - `hotpost-mini/hotpost-mini-app/package.json`
  - `build:weapp`
  - `build:weapp:prod`
- 当前机制变成：
  - 打包前先校正一次源配置
  - 打包后再校正一次 `dist/project.config.json`
- 这样就不再依赖人工记忆，也不会出现“这次手工改好了，下次 build 又写回去”的回退。

## 改动文件
- `hotpost-mini/hotpost-mini-app/project.config.json`
- `hotpost-mini/hotpost-mini-app/package.json`
- `hotpost-mini/hotpost-mini-app/scripts/ensure-weapp-config.cjs`

## 验证
- 执行：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：
  - 构建通过
  - 护栏脚本在 build 前后都执行成功
- 配置核实：
  - `hotpost-mini/hotpost-mini-app/project.config.json`
  - `hotpost-mini/hotpost-mini-app/dist/project.config.json`
  - 两边当前都确认是：
    - `es6: false`
    - `enhance: false`
- 真机结果：
  - 用户已确认真机调试可重新看到页面，不再是之前那种一打包就白屏。

## 当前判断
- 这轮真机白屏问题已经不再是“人工排障经验”，而是被固化成了构建护栏。
- 后续只要正常走：
  - `npm run build:weapp`
  - `npm run build:weapp:prod`
- 这条错误配置就不会再被重新写回去。

## 价值
- 把一次性的排障结论，升级成了可重复执行的工程规则。
- 避免以后再因为同一类微信工程配置回退，重复消耗真机验证时间。
- 这次真正留下来的不是“修好了”，而是“以后不容易再坏回去”。

## 下一步
1. 继续收尾小程序 UI 细节，但不再动这条真机构建基线。
2. 用真机继续验：
   - 首页
   - 收藏
   - 我的
   - 静默登录 / 收藏写云端 / 清缓存恢复
3. 后续如果再遇到真机异常，先查构建链路和环境差异，不再先动产品页面。

# Phase 564 - Mini Hotpost 历史页标题错位修复

## 发现了什么？
- 小程序 `分析记录` 页当前错位，不是后端数据问题，也不是微信端随机抽风。
- 根因在历史页 header 自己的布局约束没写完整：
  - `nav-header` 没明确规定纵向排布
  - `main-title` 和 `subtitle-italic` 也没有占满整行
- 结果就是标题和副标题在窄屏里互相挤压，标题被按单字换行，副标题也被压到旁边，看起来像整块塌掉。

## 是否需要修复？
- 需要。
- 这会直接伤产品观感，而且会误导成“分析记录页整体坏了”。

## 精确修复方法
- 修改 `hotpost-mini/hotpost-mini-app/src/pages/history/index.scss`
  - `nav-header`
    - 增加 `display: flex`
    - 增加 `flex-direction: column`
    - 增加 `align-items: flex-start`
  - `main-title`
    - 增加 `width: 100%`
    - 增加 `line-height: 1.15`
  - `subtitle-italic`
    - 增加 `width: 100%`
    - 增加 `line-height: 1.5`
- 重新执行：
  - `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`

## 验证
- `dist/pages/history/index.wxss` 已包含：
  - `nav-header{align-items:flex-start;display:flex;flex-direction:column...}`
  - `main-title{...line-height:1.15;width:100%}`
  - `subtitle-italic{...line-height:1.5;width:100%}`
- `build:weapp`
  - 结果：`Compiled successfully`

## 下一步系统性计划
1. 在微信开发者工具重新编译/刷新当前 mini app
2. 复看 `分析记录` 页顶部排版是否恢复正常
3. 如果页面其余区块还有错位，再继续逐块收 CSS，而不是回头怀疑后端

## 这次执行的价值是什么？
- 把这次问题重新归类成了前端布局 bug。
- 现在可以继续把注意力放回 `rant` 结果质量，而不是被页面错位反复打断。

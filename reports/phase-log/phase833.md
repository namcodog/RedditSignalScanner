# phase833

## 本轮目标
- 放弃书签式详情交互，回滚到原来的详情页交互版本。

## 实际改动
- 从 checkpoint `mini-app-20260414-184808` 恢复以下文件：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-sections.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.scss`
- 删除：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-reading-flow.scss`

## 说明
- 只回滚详情页交互层。
- 没有回滚后续的登录链修复，也没有动首页卡片和数据链。

## 验证
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
  - 通过

## 下一步
- 开发者工具重新编译后，只验证一件事：
  - 详情页是否恢复到回滚前的原始交互样式

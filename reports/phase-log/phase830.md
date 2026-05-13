# Phase 830 - miniRelease 去除 display_order 云库索引依赖

## 发现

- 在把首页显示顺序贯穿到 cloud_db 与云函数后，手机端仍然出现“加载失败”。
- 新增判断：问题很可能不是数据缺失，而是 `miniRelease` 云函数在云数据库执行：
  - `where({ release_id }).orderBy('display_order', 'asc')`
- 这条查询在真云环境下可能要求组合索引；本地测试夹具不会暴露这个约束。

## 修复

- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js`
  - 去掉云库侧 `orderBy('display_order', 'asc')`
  - 改成：
    - 先按 `release_id` 分页拉出卡片
    - 再在内存中按 `display_order` 排序
- 排序规则：
  - 优先按 `display_order asc`
  - 若缺失 `display_order`，再回退到 `published_at desc`

## 为什么这样修

- 目标不是改规则，而是去掉云端索引依赖。
- 这样即使云库没有给 `release_id + display_order` 建复合索引，首页也不会因为排序查询直接报错。

## 验证

- 云函数测试：
  - `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
  - `4 passed`
- 本地开发包重建：
  - `npm run build:weapp`
  - 通过
- 生产包重建：
  - `npm run build:weapp:prod`
  - 通过

## 结论

- 当前手机端“加载失败”的最大剩余风险已从云函数代码侧收口：
  - 不再依赖 `display_order` 的云库排序索引
- 后续真机只需要：
  1. 重新部署 `miniRelease`
  2. 重新导入最新 cloud_db 文件
  3. 再扫新的预览二维码

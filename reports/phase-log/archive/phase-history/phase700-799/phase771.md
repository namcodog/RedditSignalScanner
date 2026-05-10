# Phase 771 - 近期爆帖详情卡加载修复

## 发现

- 首页四个 tab 的详情页都走 `/pages/velocity/index`，不是路由分叉问题。
- 本地 snapshot 中 hot 卡详情数据完整，未发现缺字段或脏卡。
- 当前证据更指向详情查询链本身：
  - `miniRelease.getCardDetail` 之前会先整包加载当前 release，再从内存里找单卡。
  - 详情页前端没有超时保护，一旦云函数调用迟迟不返回，页面就会一直停在“正在加载”。

## 结果

- 云函数 `miniRelease` 已改为按 `release_id + card_id` 直查单卡详情，不再整包扫描 release。
- 详情页已补 10 秒超时保护，避免再次出现无限 loading。
- 相关单测通过：
  - `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
- 小程序开发态构建通过：
  - `npm run build:weapp`

## 下一步

- 开发者工具里重新上传：
  - 小程序代码包
  - `miniRelease` 云函数
- 真机重点验证“近期爆帖 -> 详情页”链路是否恢复。

# Phase 827

## 本轮目标
- 修复小程序首页在更新 `release-d982bc4849eb` 后出现的“卡片加载失败”。

## 发现
- 首页错误不是排序规则失效，也不是 cloud_db 数据没更新。
- 当前本地最新数据正确：
  - `latest.json` 首卡是 `hot`
  - `cloud_db` 导入文件首卡也是 `hot`
- 失败点在小程序云函数 `miniRelease` 的首页列表链：
  - `store.js -> toCardSummary()` 仍然硬依赖 `item.source_module.top_community`
  - 这条链对新 release 的摘要契约兼容性过窄
  - 一旦云函数端读到 summary-shape 卡片或非预期结构，就会整页失败
- 同时发现 `loadReleaseMeta()` 取最新 release 的方式不稳：
  - 先 `limit(100).get()` 再本地排序
  - 这在云端 `mini_release_meta` 积累很多历史 release 后不可靠

## 修复
- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js`
  - `loadReleaseMeta()` 改成按 `published_at desc` 取最新 release
  - `toCardSummary()` 改成优先读顶层摘要字段：
    - `top_community`
    - `thread_count`
    - `community_count`
  - 如果顶层没有，再回退到 `source_module`
  - 如果两边都不满足，显式抛出 `MINI_RELEASE_CARD_SUMMARY_INVALID:<card_id>`，不再模糊失败
- `hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
  - 适配新的 `orderBy(...).limit(...).get()` 查询链
  - 新增回归测试：云函数必须接受 summary-shape 卡片，不要求一定带 `source_module`

## 验证
- `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
  - `4 passed`
- 本地直接对当前 `miniRelease/data/latest.json` 跑 `listCards(snapshot, { cardType: 'all' })`
  - 返回 `30` 张
  - 首卡是 `hot`

## 结论
- 当前“首页卡片加载失败”的根因是云函数 `miniRelease` 的列表摘要契约过旧，不是 release 数据坏了。
- 代码已在仓库修好，但手机真机恢复还需要把 `miniRelease` 云函数重新部署到当前云环境。

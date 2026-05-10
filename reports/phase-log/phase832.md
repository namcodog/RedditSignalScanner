# Phase 832 - miniRelease 最新 release 选取规则修复

## 发现

- 用户反馈：
  - 手机已能加载
  - 但首页排序仍然回到旧版，首卡不是 `hot`
- 核对后确认，问题不在 cloud_db 数据缺失，而在 `miniRelease` 云函数选错了“最新 release”。

## 根因

- `release-d982bc4849eb`
- `release-d21df020d6e8`
- 以及后续重建出来的多版 release，其 `published_at` 都相同：
  - `2026-04-14T09:50:08.707203Z`
- 云函数此前用：
  - `published_at desc`
  来判定“最新 release”
- 这会在同一发布时间的多版 release 并存时，稳定选错旧版。
- 旧版 release 没有正确的 `display_order` 语义，因而首页会退回旧顺序。

## 修复

### 导出侧

- `backend/app/services/hotpost/mini_snapshot.py`
  - `cloud_db` 导出不再把 `synced_at` 写成 `published_at`
  - 改为真实导出时间：
    - `datetime.now(timezone.utc)`

### 云函数侧

- `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js`
  - `loadReleaseMeta()` 改成：
    - 先按 `synced_at desc` 取 meta
    - 再按 `synced_at -> published_at -> release_id` 排序兜底
- 这样“最新 release”由真实导入时间决定，不再被相同 `published_at` 干扰。

## 验证

- 新导出文件当前已经变成：
  - `release_id = release-4d2eee765646`
  - `synced_at = 2026-04-14T12:08:17.301272Z`
- 云函数测试：
  - `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
  - `4 passed`
- 生产构建：
  - `npm run build:weapp:prod`
  - 通过

## 结论

- 手机排序被打回旧版的真正根因，不是前端缓存，也不是用户没导数据，而是云函数一直按错误时间字段选 release。
- 现在 release 选取规则已改成 `synced_at` 优先，后续重新导入并重新部署后，手机应命中新版顺序。

# phase706

## 本轮完成
- 已把 `hotpost-mini v1.0` 的第一优先级底座真正接起来：
  - 小程序工程已识别 `cloudfunctions`
  - 本地 `published` 发布集已能导出成 `mini snapshot`
  - 小程序读卡链已改走 `miniRelease` 云函数

## 代码改动

### 后端
- 新增 `mini snapshot` 构建与发布：
  - `backend/app/services/hotpost/mini_snapshot.py`
  - `backend/scripts/hotpost/push_mini_snapshot.py`
- 新增回归测试：
  - `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`

### 小程序
- 接入云开发基础配置：
  - `hotpost-mini/hotpost-mini-app/project.config.json`
  - `hotpost-mini/hotpost-mini-app/config/index.ts`
  - `hotpost-mini/hotpost-mini-app/src/app.ts`
  - `hotpost-mini/hotpost-mini-app/types/global.d.ts`
- 新增云函数与公共读卡 store：
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/common/mini-release-store.js`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/*`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/miniAuth/*`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/miniFavorites/*`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/miniEvents/*`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
- 新增云函数调用封装：
  - `hotpost-mini/hotpost-mini-app/src/services/cloud.ts`
- 把内容读取切到云函数：
  - `hotpost-mini/hotpost-mini-app/src/services/clues.ts`

## 实际结果
- 已真实执行：
  - `python backend/scripts/hotpost/push_mini_snapshot.py`
- 当前导出结果：
  - `release_id = release-8e60dc5c296a`
  - `card_count = 57`
- 已生成并同步：
  - `backend/data/hotpost/mini_snapshots/latest.json`
  - `backend/data/hotpost/mini_snapshots/release-8e60dc5c296a.json`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/data/latest.json`
  - `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/data/releases/release-8e60dc5c296a.json`

## 验证
- Python：
  - `pytest tests/scripts/hotpost/test_push_mini_snapshot.py -q`
  - `2 passed`
- Cloud Function：
  - `node --test cloudfunctions/tests/mini-release.test.mjs`
  - `1 passed`
- Mini App：
  - `npm run build:weapp:prod`
  - 构建成功

## 当前边界
- 这轮只迁了“内容分发链”：
  - 首页读卡
  - 详情读卡
  - 基础事件上报入口
- `auth / favorites / profile` 还没有切到真正可用的云端实现，目前只补了云函数骨架，下一轮再接。

## 下一步
- 继续接：
  - `miniAuth`
  - `miniFavorites`
  - `3-card meter`
- 然后再把：
  - 首页门槛
  - 收藏云同步
  - Profile 用户态
  一起收口。

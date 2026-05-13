# Phase 829 - 首页显示顺序全链对齐修复

## 发现

- 用户真机与开发工具本地看到的首页首卡一致，都是旧顺序：
  - 第 1 张是 `breakdown`
  - 不是当前 display-order winner 里的 `hot`
- 问题不是缓存歧义，而是首页显示顺序没有贯穿到实际取数主链。

## 根因

### 1. 云函数链

- `mini_snapshot/latest.json` 和 `mini_release_cards.wechat-import.json` 中，卡片顺序本来就是正确的：
  - `hot / hot / signal / signal / breakdown ...`
- 但 `hotpost-mini/hotpost-mini-app/cloudfunctions/miniRelease/store.js`
  从云库取 `mini_release_cards` 时又按 `published_at desc` 排了一次。
- 导致 cloud_db 里的正确显示顺序被洗掉。

### 2. 本地开发链

- `hotpost-mini` 开发工具本地模式走 `127.0.0.1:8006/api/hotpost/cards`
- `backend/app/services/hotpost/clues_catalog.py`
  之前直接按 `published_at` 倒序从 `published` 取卡。
- 所以本地开发工具首页和手机线上都在看“发布时间顺序”，而不是首页 winner 顺序。

## 修复

### 云函数

- `mini_snapshot` 导出 cloud_db 文件时，为每张卡写入：
  - `display_order`
- `miniRelease/store.js` 改为：
  - 按 `display_order asc` 从云库读取 `mini_release_cards`

### 本地开发接口

- `clues_catalog.py` 增加读取 `backend/data/hotpost/mini_snapshots/latest.json`
- `/api/hotpost/cards` 列表接口优先按最新 `mini_snapshot` 顺序出卡
- 如果本地不存在 snapshot，才回退到旧的 `published_at` 顺序

## 验证

- 后端 API 测试：
  - `cd backend && pytest tests/api/test_hotpost_clues.py -q --tb=short`
  - `10 passed`
- 云函数测试：
  - `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
  - `4 passed`
- 重建 snapshot：
  - `cd backend && python scripts/hotpost/push_mini_snapshot.py`
  - 新 release：`release-d21df020d6e8`
- 本地函数直接验证：
  - `list_card_summaries(card_type='all')` 首 10 张已是 `hot / hot / signal / signal / breakdown ...`
- 本地 `127.0.0.1:8006/api/hotpost/cards?card_type=all` 实测也已回正：
  - 第 1 张 `hot`
  - 第 2 张 `hot`
  - 第 5 张 `breakdown`

## 后续动作

- 手机真机要看到同样顺序，必须：
  1. 重新导入新的 `mini_release_cards.wechat-import.json`
  2. 重新部署 `miniRelease` 云函数
  3. 用新的生产构建重新预览

## 结论

- 这次问题不是规则没生效，而是显示顺序信息没有贯穿到实际取数链。
- 当前已把：
  - 本地开发接口
  - cloud_db 导出
  - 云函数读取
  三段全部收口到同一顺序来源。

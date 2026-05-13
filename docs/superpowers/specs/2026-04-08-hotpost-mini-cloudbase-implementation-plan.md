# Plan: hotpost-mini v1.0 云开发实施方案
Date: 2026-04-08
Branch: main

## 1. 锁死的产品结论

`v1.0` 按下面 5 条执行，不再反复摇摆：

1. 小程序主线只做卡片阅读链，不带旧 `search/result/loading`。
2. 冷启动采用 `3-card meter`，不是首页首屏强登录。
3. 小程序发布后，内容分发必须云端常驻，不依赖本机在线。
4. 卡片继续走 `snapshot-first`，用户/收藏/埋点走云数据库。
5. 用户模型现在就预留后续收费字段，但 `v1.0` 不先做完整会员系统。

## 2. 目标体验

### 未登录用户
- 进入首页可看到前 3 张卡
- 可感受到产品值不值
- 第 4 张或继续深读时，出现登录门槛

### 已登录用户
- 可继续看全部已发布卡
- 可收藏、同步、跨设备恢复
- 后续可以无缝接收费权益

## 3. 架构方案

```text
本地产卡链（唯一内容真相源）
collect -> candidate -> draft -> review -> publish
                          |
                          v
                 published snapshot
                          |
                          v
                 push_mini_snapshot.py
                          |
        +-----------------+-----------------+
        |                                   |
        v                                   v
  云存储 latest/versioned snapshot      云数据库 release_meta
        |                                   |
        +-----------------+-----------------+
                          |
                          v
                   hotpost-mini 小程序
             先看 3 张 -> 登录 -> 全量阅读/收藏/埋点
                          |
                          v
             云数据库 users / favorites / events
```

## 3.1 内部存储收口

当前不能再继续把所有状态都塞进一个 `hotpost_clues.json`。

现状问题不是“4 千多行看着烦”，而是：
- 一个文件同时承担：
  - `categories`
  - `candidates`
  - `drafts`
  - `published`
- 候选、草稿、发布、脚本回填、前台接口都在读写同一个总桶
- 当前仓库里已有约 `35` 处代码/测试直接依赖这个单文件

所以要改的不是“换个更大的 JSON”，而是**拆职责**。

### 推荐拆法

#### A. 工作集（可编辑）

```text
backend/data/hotpost/
  categories.json
  candidates/
    ai-automation.json
    ecommerce-sellers.json
    business-growth-ops.json
  drafts/
    <draft_id>.json
```

说明：
- `candidates` 按 `scope` 拆
- `drafts` 按单卡拆
- 这样人工 review 和脚本更新不会再整桶重写

#### B. 发布集（不可变）

```text
backend/data/hotpost/releases/
  <release_id>/
    index.json
    cards/
      <card_id>.json
  latest.json
```

说明：
- `release` 一旦产出就不要回写旧版本
- `latest.json` 只做当前版本指针或最新索引
- 回滚时切 `latest` 即可

#### C. 小程序分发集（云端）

```text
cloud:
  releases/hotpost/latest.json
  releases/hotpost/<release_id>.json
```

说明：
- 小程序不关心 `candidates / drafts`
- 小程序只消费发布产物

### 结论

不要再把 `hotpost_clues.json` 当长期真相源继续养大。
它现在最多只能作为迁移过渡文件。

## 4. 云端资源设计

### 4.1 云存储

用于卡片内容分发：

- `releases/hotpost/latest.json`
- `releases/hotpost/<release_id>.json`

说明：
- `latest.json` 给小程序读取当前线上版本
- 版本化对象用于回滚

### 4.2 云数据库集合

#### `mini_users`

字段建议：
- `openid`
- `unionid`
- `nickname`
- `avatar_url`
- `plan`
- `status`
- `entitlements`
- `last_login_at`
- `created_at`
- `updated_at`

默认值建议：
- `plan = free`
- `status = active`
- `entitlements = []`

#### `mini_user_favorites`

字段建议：
- `openid`
- `card_id`
- `created_at`

唯一约束口径：
- `openid + card_id`

#### `mini_event_logs`

`v1.0` 只记最小必要事件：
- `meter_prompt_shown`
- `login_success`
- `detail_view`
- `favorite_click`
- `favorites_view`
- `profile_view`

字段建议：
- `openid`（未激活用户可为空或写临时访客标识）
- `event_type`
- `card_id`
- `category_id`
- `created_at`

#### `mini_release_meta`

字段建议：
- `release_id`
- `snapshot_path`
- `card_count`
- `checksum`
- `published_at`
- `is_latest`

## 5. 登录与门槛设计

### 5.1 产品口径

不采用“首页首屏强登录”。

采用：
- 前 3 张免费试读
- 第 4 张或继续深读时登录

### 5.2 工程口径

把“技术识别用户”和“产品上视为已登录”拆开：

- 技术识别：
  - 可通过微信登录能力拿到 `openid`
- 产品登录：
  - 用户点击“继续查看”后，创建/激活 `mini_user`
  - 从这一步开始解锁全量卡片、收藏、同步

### 5.3 不做的事

- 不把头像昵称授权绑在登录门槛
- 不在 `v1.0` 做复杂会员页
- 不在 `v1.0` 做强反作弊付费墙

## 6. 代码改造清单

### 6.1 小程序工程

建议新增：

- `hotpost-mini/hotpost-mini-app/cloudfunctions/`
- `hotpost-mini/hotpost-mini-app/src/services/cloud/`
- `hotpost-mini/hotpost-mini-app/src/services/access-meter.ts`
- `hotpost-mini/hotpost-mini-app/src/components/LoginGate.tsx`

建议改造：

- [project.config.json](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/project.config.json)
  - 增加 `cloudfunctionRoot`
- [auth.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/auth.ts)
  - 从 Python HTTP 登录切到云函数登录/激活
- [clues.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/clues.ts)
  - 从 HTTP 请求切到云端 snapshot 读取
- [favorites.ts](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/services/favorites.ts)
  - 从 Python API 切到云函数/云数据库
- [index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx)
  - 接入 3-card meter
- [profile/index.tsx](/Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app/src/pages/profile/index.tsx)
  - 接入登录状态与权益文案

### 6.2 云函数建议

`v1.0` 建议只做 4 个：

1. `miniAuth`
   - 创建/更新 `mini_users`
   - 返回当前用户 `plan/status/entitlements`

2. `miniRelease`
   - 返回 `latest snapshot` 地址或内容
   - 返回 `release_meta`

3. `miniFavorites`
   - list/add/remove favorites

4. `miniEvents`
   - 记录最小必要事件

### 6.3 后端脚本

建议新增：

- `backend/scripts/hotpost/push_mini_snapshot.py`
- `backend/scripts/hotpost/migrate_hotpost_storage_layout.py`

职责：
- 从 `backend/data/hotpost_clues.json` 读取 `published`
- 生成小程序可消费的最小 snapshot
- 上传云端 `latest + versioned`
- 更新 `mini_release_meta`

迁移脚本职责：
- 把当前单桶 `hotpost_clues.json` 拆成：
  - `categories.json`
  - `candidates/<scope>.json`
  - `drafts/<draft_id>.json`
  - `releases/<release_id>/...`
- 提供一次性迁移和校验输出

## 7. 分阶段实施顺序

### Phase 1：云开发工程脚手架

目标：
- 把 mini-app 工程接上云开发目录和最小云函数骨架

完成标准：
- 开发者工具能识别 `cloudfunctionRoot`
- 能跑通一个最小 `ping/login` 云函数

### Phase 2：内部存储拆桶

目标：
- 先把本地单桶 JSON 拆成“工作集 / 发布集”

完成标准：
- `hotpost_clues.json` 不再承担长期编辑职责
- 候选、草稿、发布产物已分路径存放
- 现有 review / publish / list 入口仍可工作

### Phase 3：snapshot 发布链

目标：
- 让本地产卡结果可以被一条脚本稳定推送到云端

完成标准：
- `latest.json` 可读
- 版本化 snapshot 可回滚
- `mini_release_meta` 能显示版本信息

### Phase 4：登录与 3-card meter

目标：
- 把冷启动漏斗接起来

完成标准：
- 未登录可看前 3 张
- 第 4 张或继续深读时弹登录门槛
- 登录成功后解锁全量

### Phase 5：收藏 / 埋点 / 我的页面

目标：
- 完成用户状态闭环

完成标准：
- 收藏可写云端
- 换设备收藏可恢复
- 我的页面能显示用户基本状态

### Phase 6：上线验收与回滚

目标：
- 让这套东西不是“能跑”，而是“敢发”

完成标准：
- 微信开发者工具验收通过
- 真机验收通过
- 发布失败时能切回上一个 snapshot

## 8. 测试与验收

## 8.1 现状

- mini-app 当前没有独立测试 runner
- backend 已有 `pytest`

## 8.2 最小测试策略

### Python

新增：
- `backend/tests/scripts/hotpost/test_push_mini_snapshot.py`
- `backend/tests/scripts/hotpost/test_migrate_hotpost_storage_layout.py`

覆盖：
- 存储拆桶结果
- 从旧单桶到新结构的迁移校验
- snapshot 导出字段
- 上传前数据裁剪
- release meta 更新
- 回滚选择逻辑

### Cloud Functions

不建议为了 `v1.0` 新引一整套复杂测试框架。
建议直接用 `node:test` 做 contract smoke。

建议新增：
- `hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-auth.test.mjs`
- `hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-favorites.test.mjs`
- `hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`

### Mini App

验收以这 3 类为主：

1. `npm run build:weapp:prod`
2. 微信开发者工具冒烟
3. 真机手动验收矩阵

### 验收矩阵

```text
登录漏斗
========
[ ] 未登录进入首页，只看到前 3 张
[ ] 第 4 张或继续深读时出现登录门槛
[ ] 登录成功后可继续看全部内容

内容分发
========
[ ] 小程序读取的是云端 latest snapshot
[ ] 发布新 snapshot 后，客户端能看到更新
[ ] 回滚到旧 snapshot 后，客户端能恢复旧版本

用户状态
========
[ ] 收藏成功
[ ] 清缓存后重新登录，收藏恢复
[ ] Profile 页展示当前用户状态
```

## 9. 风险与规避

### 风险 1：meter 被本地清缓存绕过

判断：
- `v1.0` 可接受

规避：
- 不把 meter 当付费墙，只把它当冷启动转化门槛

### 风险 2：snapshot 推送一半失败

规避：
- 先上传版本化对象
- 校验成功后再切 `latest`

### 风险 3：未来恢复搜索时污染当前底座

规避：
- 搜索只能以后加 `search facade`
- 不改当前内容分发和用户体系

### 风险 4：隐私指引或审核不过

规避：
- 提前补全登录、头像昵称、收藏、埋点涉及的隐私说明
- 提审前做一次隐私项自查

### 风险 5：单桶 JSON 继续增长，编辑和发布互相污染

规避：
- 先拆本地工作集和发布集
- 小程序只消费发布产物
- 候选/草稿不再和发布产物共桶

## 10. 这版不做

- 不迁旧 `search/result/loading`
- 不把云数据库当正式内容真相源
- 不做完整会员系统
- 不做复杂推荐算法
- 不为了未来搜索先做大而全后端
- 不继续把单个 `hotpost_clues.json` 养成永久总桶

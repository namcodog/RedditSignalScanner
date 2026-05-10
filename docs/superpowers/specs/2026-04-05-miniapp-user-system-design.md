# Design: 小程序用户体系 & 上线收尾方案

Date: 2026-04-05
Branch: main

---

## Problem Statement

小程序当前是一个**纯本地运行的信号阅读器**：没有用户身份、收藏存在浏览器缓存里、个人中心只有静态说明文。如果用户换手机、清缓存、重新安装小程序，所有收藏全丢。

这意味着产品不具备上线条件——既不满足微信审核对用户数据保护的基本要求，也无法支撑后续任何运营动作。

---

## Premise Challenges

| 被挑战的前提 | 结论 |
|---|---|
| "先上线再说，用户体系以后做" | **否决**。微信审核对有数据存储行为的小程序要求登录，且本地收藏丢失会直接摧毁用户信任 |
| "做完整的用户系统（注册/手机号/密码）" | **否决**。这是探索型工具，不是社交产品，不需要完整用户系统 |
| "用微信强授权弹窗" | **否决**。微信 2023 年后已废弃 `wx.getUserProfile`，且强授权弹窗对阅读工具摩擦太大 |
| "个人中心需要很多功能" | **部分否决**。V1 只需要身份展示+基本入口，不要做成"我的页面大杂烩" |

---

## Options Considered

### OPTION A: 静默登录（最轻量）

**What**: `wx.login()` 拿 code → 后端换 openid → 自动建用户，不弹任何授权框
**Effort**: S
**Risk**: Low
**Best for**: 赶上线、功能极简时

- 优点：零用户摩擦，开发量最小
- 缺点：个人中心无头像昵称，很"空"

### OPTION B: 静默登录 + 按需授权头像昵称 ⭐ 推荐

**What**: 先静默登录拿 openid，个人中心提供"设置头像和昵称"入口（微信新规组件）
**Effort**: M
**Risk**: Low
**Best for**: 平衡体验和开发效率

- 优点：核心功能无摩擦，个人中心有完整感
- 缺点：多一个授权交互流程

### OPTION C: 强制授权登录

**What**: 进入小程序或点收藏弹出登录/授权
**Effort**: M
**Risk**: High — 大量用户流失
**Best for**: 社交类、电商类产品（不是我们）

---

## Chosen Direction

**OPTION B — 静默登录 + 按需授权头像昵称**

理由：
1. `wx.login()` 是微信内置能力，零代码成本拿到稳定 openid
2. 收藏同步只依赖 openid，不需要用户手动操作
3. 头像昵称按需授权，放在个人中心，不阻断核心流程
4. 微信新规要求用 `<button open-type="chooseAvatar">` + `<input type="nickname">`，我们直接按规范来

---

## 用户体系技术设计

### 数据模型

```
users
├── id (PK, UUID)
├── wx_openid (UNIQUE, 索引)
├── wx_unionid (可空 — 绑定开放平台后有)
├── nickname (默认 "探索者")
├── avatar_url (默认头像 URL)
├── plan (VARCHAR, 默认 'free' — 预留: 'free' | 'pro')
├── plan_expires_at (TIMESTAMP, 可空 — 付费过期时间)
├── created_at
└── last_login_at

user_favorites
├── id (PK)
├── user_id (FK → users.id)
├── card_id
├── created_at
└── UNIQUE(user_id, card_id)
```

### 登录流程

```
[小程序启动]
     │
     ▼
wx.login() 拿 code
     │
     ▼
POST /api/hotpost/auth/login { code }
     │
     ▼
后端用 code 换 openid (调用微信 code2Session)
     │
     ├── openid 已存在 → 返回 token + 用户信息
     │
     └── openid 不存在 → 自动建用户 → 返回 token + 用户信息
     │
     ▼
前端存 token → 后续请求 header 带 Authorization
```

### API 新增

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/hotpost/auth/login` | POST | 接收 `{ code }`，返回 `{ token, user }` |
| `/api/hotpost/auth/profile` | PUT | 更新昵称/头像 `{ nickname, avatar_url }` |
| `/api/hotpost/favorites` | GET | 获取当前用户收藏列表 |
| `/api/hotpost/favorites/{card_id}` | POST | 收藏卡片 |
| `/api/hotpost/favorites/{card_id}` | DELETE | 取消收藏 |

### 前端 Token 管理

```typescript
// services/auth.ts
const TOKEN_KEY = 'hotpost:auth:token'

export async function ensureLogin(): Promise<string> {
  // 1. 检查本地 token 是否有效
  // 2. 无效则 wx.login() → POST /auth/login
  // 3. 存储并返回 token
}
```

### 收藏迁移策略

老用户（V1.0 之前的本地收藏）→ 首次登录时，将本地收藏批量上传到服务端 → 清空本地缓存。

```typescript
async function migrateLocalFavorites(token: string) {
  const localItems = Taro.getStorageSync('hotpost:favorites:v1')
  if (localItems?.length) {
    await request('/api/hotpost/favorites/batch', { card_ids: localItems.map(i => i.card_id) }, 'POST')
    Taro.removeStorageSync('hotpost:favorites:v1')
  }
}
```

---

## 收藏页完善方案

### 当前状态
- ✅ 收藏列表展示（复用 CluePreviewCard）
- ✅ 收藏计数 + 空状态引导
- ✅ 取消收藏交互

### V1.0 必须改的

| 改动 | 说明 |
|---|---|
| 收藏数据源从本地切到云端 | `listFavoriteCards()` → `GET /api/hotpost/favorites` |
| 收藏/取消收藏走 API | `toggleFavoriteCard()` → `POST/DELETE /api/hotpost/favorites/{card_id}` |
| 首次登录迁移本地数据 | 见上方迁移策略 |

### V1.1 增强

| 改动 | 说明 |
|---|---|
| 按类型筛选 | 收藏页顶部加"全部/商业观察/写作角度"tab |
| 收藏时间展示 | 每张卡下方展示"3天前收藏" |

---

## 个人中心完善方案

### 当前页面分析（基于截图）

目前"我的"页面只有两个模块：
1. "怎么用最顺" — 3 条使用指南
2. "最近收藏的" — 最近 2 个收藏标题

**问题**：信息密度低，缺乏用户身份感，没有功能入口。

### V1.0 改版设计

```
┌─────────────────────────────┐
│         [默认头像]           │
│       探索者 / 昵称          │
│    "你已经收藏了 5 个观察"    │
│    [完善头像和昵称]（按钮）   │
│                             │
├─────────────────────────────┤
│  📌 我的收藏                │
│     → 查看全部收藏（跳收藏tab）│
│                             │
│  📖 怎么用最顺              │
│     1. 先盯首页...           │
│     2. 详情页看原话...        │
│     3. 收藏页只留...          │
│                             │
├─────────────────────────────┤
│  💬 意见反馈                 │
│  ℹ️  关于                   │
│  📋 用户协议 | 隐私政策       │
│                             │
│      v1.0.0                 │
└─────────────────────────────┘
```

### V1.0 需要新增的模块

| 模块 | 说明 | 实现方式 |
|---|---|---|
| 用户头像区 | 展示头像 + 昵称 + 收藏数 | 登录后从用户信息渲染 |
| 完善信息入口 | 设置头像和昵称 | `<button open-type="chooseAvatar">` + `<input type="nickname">` |
| 意见反馈 | 微信自带反馈入口 | `<button open-type="feedback">` |
| 关于/版本号 | 产品说明 + 当前版本 | 静态文本 |
| 用户协议/隐私政策 | 审核必需 | 跳转到隐私协议页面 |

---

## 上线版本规划

### V1.0 — 可上线最小版本 "信号阅读器"

**上线核心目标**：能过审核 + 数据不丢 + 基本可信

| 功能 | 状态 | 优先级 |
|---|---|---|
| 静默登录（wx.login → openid） | 新增 | P0 |
| 收藏云端同步 | 改造 | P0 |
| 本地收藏迁移 | 新增 | P0 |
| 个人中心用户信息展示 | 改造 | P0 |
| 用户隐私协议弹窗 | 新增 | P0（审核强制） |
| 隐私政策/用户协议页面 | 新增 | P0（审核强制） |
| 意见反馈入口 | 新增 | P0 |
| 关于页面/版本号 | 新增 | P1 |

**预估工期**：3-5 天（前后端并行）

**后端工作量**：
- 用户表 + 收藏表 migration
- auth/login API（wx code2Session 对接）
- favorites CRUD API
- JWT/token 中间件

**前端工作量**：
- auth service（token 管理 + 自动登录）
- favorites service 重构（本地 → API）
- profile 页面改版
- 隐私协议弹窗组件
- 隐私政策页面

---

### V1.1 — 上线后第一版迭代 "体验增强"

| 功能 | 说明 |
|---|---|
| 头像昵称授权 | 个人中心"完善信息" |
| 收藏页分类筛选 | 商业观察/写作角度 tab |
| 卡片分享 | 生成小程序卡片分享到微信聊天 |
| 阅读历史 | 记录看过的卡片详情 |

**预估工期**：1 周

---

### V1.2 — 运营驱动迭代

| 功能 | 说明 |
|---|---|
| 消息订阅推送 | 每日新卡提醒 |
| 收藏批量管理 | 全选、批量取消 |
| 阅读统计 | "你这周看了 X 张卡" |

---

## NOT in Scope（明确不做）

- ❌ 手机号登录（不需要，openid 够用）
- ❌ 用户注册系统（静默登录自动完成）
- ❌ 用户间社交（评论、点赞、关注）
- ❌ 个性化推荐（V1 不做，数据不够）
- ❌ 后台管理用户画面（先用数据库直连看数据）
- ❌ 微信支付/会员体系

---

## Success Criteria

| 指标 | 标准 |
|---|---|
| 微信审核通过 | 一次提交通过，不被打回 |
| 收藏不丢失 | 老用户升级后，本地收藏完整迁移到云端 |
| 个人中心有内容 | 不再是两个孤零零的卡片 |
| 用户无感登录 | 不会因为登录弹窗而流失 |
| 收藏同步正常 | 换设备后收藏依然在 |

---

## Risks

| 风险 | 应对 |
|---|---|
| 微信 code2Session 接口调用频率限制 | 前端缓存 token，不重复请求 |
| 本地收藏迁移丢失 | 迁移前备份本地数据，迁移成功后再清除 |
| 审核对"信息资讯"类目有额外要求 | 提前准备 ICP 备案、内容合规声明 |

---

## 下一步

1. **你确认方向后** → 转入 `plan-eng-review` 做架构审查
2. **架构确认后** → 输出 implementation plan
3. **执行顺序**：后端 API 先行（auth + favorites）→ 前端对接 → 个人中心改版 → 隐私协议 → 提审

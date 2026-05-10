# 小程序用户系统云开发收口方案

日期：2026-04-22
范围模式：**HOLD SCOPE（锁定范围）**

---

## 1. 这轮到底要解决什么

把小程序用户系统从“半本地、半云开发”的状态，收成 **一套云开发真链路**。

目标不是做更复杂的系统，而是把下面这些功能变成同一套可信用户系统：

- 微信授权登录
- 绑定手机号
- 查看详情扣积分
- 每日签到积分
- 邀请新用户成功后奖励积分
- 个人页查看积分余额和积分流水

内容链、发卡链、卡片 schema 一律不动。

---

## 2. CEO 审查结论

### 2.1 这是对的问题吗

是。
当前真正的问题不是“缺一个按钮”，而是：

- 用户系统是裂开的
- 开发态和线上态不是一套
- 后面再加积分和邀请奖励，只会更乱

### 2.2 更简单的方案是什么

最简单的方案不是补本地 backend，而是：

**让小程序用户系统彻底只走云开发。**

### 2.3 不做会怎样

如果继续维持“双系统”：

- 本地调试能过，真机不一定过
- 手机号绑定、积分、邀请奖励都要维护两套
- 后面每加一个用户权益点，复杂度翻倍

### 2.4 范围决策

| 事项 | 决策 | 原因 |
|---|---|---|
| 登录统一走云开发 | 接受 | 这是本轮核心 |
| 手机号绑定统一走云开发 | 接受 | 本地当前根本没做完 |
| 积分系统 | 接受 | 新需求核心 |
| 邀请新用户奖励 | 接受 | 新需求核心 |
| 头像 / 昵称增强 | 不做 | 用户已明确不重要 |
| 本地 backend 对齐手机号/积分 | 不做 | 会变成第二套用户系统 |
| 公众号关注 +100 真核验 | 暂缓 | 当前没有核验链，不能假做 |

---

## 3. 工程审查结论

### 3.1 最小架构

保留 2 个云函数边界：

- `miniAuth`
  - login
  - bindPhone
  - updateProfile

- `miniPoints`
  - getSummary
  - consumeDetail
  - checkin
  - listLedger
  - createInvite
  - completeInvite

不把积分逻辑塞进 `miniAuth`，避免认证和增长逻辑混在一起。

### 3.2 数据模型

#### `mini_users`

新增或补齐：

- `points_balance`
- `last_checkin_date`
- `phone_number`
- `phone_masked`
- `phone_bound_at`

#### `mini_user_points_ledger`

记录所有积分变化：

- `user_openid`
- `delta`
- `reason`
- `meta`
- `created_at`

`reason` 只允许：

- `init_grant`
- `detail_consume`
- `daily_checkin`
- `referral_reward`
- `official_account_reward`

#### `mini_user_referrals`

保证邀请奖励可追溯、可防刷：

- `invite_token`
- `inviter_openid`
- `invitee_openid`
- `status`
- `reward_points`
- `created_at`
- `completed_at`
- `rewarded_at`

`status`：

- `pending`
- `completed`
- `rewarded`

### 3.3 关键数据流

#### 登录 + 绑手机号

```text
用户点详情
-> 未登录
-> 弹登录提示
-> miniAuth.login
-> 跳 bind-phone 页
-> miniAuth.bindPhone
-> 若成功:
   - 首次绑定手机号的新用户，写入 init_grant +60
   - 若存在待完成 invite_token，尝试 completeInvite
-> 返回详情
```

#### 查看详情扣分

```text
用户点详情
-> 已登录且已绑手机号
-> miniPoints.consumeDetail(card_id)
-> points_balance >= 10:
   - ledger 写入 detail_consume -10
   - 返回 allowed=true
-> points_balance < 10:
   - 返回 allowed=false + share CTA
```

#### 每日签到

```text
用户进个人页
-> 点签到
-> miniPoints.checkin()
-> 若今天未签:
   - +10
   - 写 ledger
-> 若今天已签:
   - 返回 already_checked_in=true
```

#### 邀请奖励

```text
老用户点分享
-> miniPoints.createInvite()
-> 生成 invite_token
-> 分享 path 带 invite_token

新用户打开小程序
-> 本地存 pending invite_token
-> 完成 login + bindPhone
-> miniPoints.completeInvite(invite_token)
-> 仅当 invitee 是新用户且首次完成绑手机号:
   - 给 inviter +30
   - 写 referral ledger
```

---

## 4. 当前需求清单（按优先级）

### P0 必做

1. **开发态与生产态用户系统统一走云开发**
2. **详情页强制登录 + 绑手机号**
3. **新用户首次绑手机号送 60 分**
4. **查看详情扣 10 分**
5. **积分不足时拦截详情，并提示“分享好友可获得30积分”**
6. **首页品牌名改成 `深蓝singal`**
7. **授权页改成两步式：先授权，再绑手机号**
8. **个人页新增积分卡**
9. **积分卡进入积分流水页**
10. **每日签到 +10**
11. **分享给新用户，新用户完成授权+绑手机号后，老用户 +30**

### P1 需明确阻塞

12. **关注公众号 +100**
   - 当前没有核验链
   - 不能直接发真积分
   - 本轮只保留产品位，不落真实奖励

---

## 5. 具体实施列表

### Phase 1：用户系统收口

- [ ] 前端 `auth.ts` 去掉本地 backend 登录分支，统一走云开发 `miniAuth`
- [ ] 开发态配置改成云开发用户系统
- [ ] 检查所有页面不再依赖本地 `wx-auth/*`

### Phase 2：登录 / 绑手机号流程改造

- [ ] 详情页点击前统一门禁：未登录先授权，已登录未绑手机号跳绑定页
- [ ] 重写绑定页为“两步式”
- [ ] 首次绑定手机号成功时发放 `60` 积分
- [ ] 首次绑定手机号后保持当前成功跳转逻辑

### Phase 3：积分系统

- [ ] 新建 `miniPoints` 云函数
- [ ] 实现 `consumeDetail`
- [ ] 实现 `checkin`
- [ ] 实现 `getSummary`
- [ ] 实现 `listLedger`
- [ ] 实现积分不足拦截与提示

### Phase 4：邀请奖励

- [ ] 实现 `createInvite`
- [ ] 设计分享 path 携带 `invite_token`
- [ ] 在小程序入口捕获并缓存 `invite_token`
- [ ] 实现 `completeInvite`
- [ ] 保证“仅新用户 + 首次绑手机号 + 仅奖励一次”

### Phase 5：个人页与积分页

- [ ] 个人页新增积分卡
- [ ] 个人页新增签到入口
- [ ] 个人页新增分享入口
- [ ] 新增积分流水页
- [ ] 显示积分变化明细

### Phase 6：公众号积分位

- [ ] 前端保留产品位
- [ ] 后端/云函数不发真积分
- [ ] 明确标成待接核验能力

### Phase 7：验收

- [ ] 云函数测试
- [ ] 前端门禁测试
- [ ] 真机登录/绑手机号测试
- [ ] 真机积分扣减测试
- [ ] 真机签到测试
- [ ] 真机邀请奖励测试

---

## 6. 验收标准

### 用户链

- 列表可直接浏览
- 点详情必定先过登录 + 绑手机号
- 旧的“免费看 3 张”逻辑彻底消失

### 积分链

- 新用户首次绑手机号后余额 = `60`
- 每次成功打开详情后余额 `-10`
- 余额不足时不能进入详情
- 每日签到只能成功一次，且 `+10`
- 积分流水能完整看到每笔变化

### 邀请链

- 老用户分享后必须拿到 `invite_token`
- 新用户必须完成“授权 + 绑手机号”才算成功邀请
- 老用户奖励固定 `+30`
- 同一个新用户不能重复给多个老用户发奖励
- 同一个邀请关系不能重复奖励

### 公众号积分链

- 本轮不得假记分
- 没有核验链时，按钮只能展示，不得直接发放 `+100`

---

## 7. 推荐执行顺序

1. 先切云开发用户系统
2. 再做绑手机号与首登积分
3. 再做详情扣分
4. 再做签到
5. 再做邀请奖励
6. 最后补积分页与公众号积分位

这条顺序的原因很简单：

- 先把用户身份统一
- 再把积分核心闭环跑通
- 最后再加增长玩法

否则会一边修登录，一边修奖励，一边修页面，最后全部缠在一起。

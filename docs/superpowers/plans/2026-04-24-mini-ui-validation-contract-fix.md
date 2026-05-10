# Mini UI Validation Contract Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把小程序界面优化从“源码侧已改”推进到“合同无漏口、可重新编译、可真机验收”。

**Architecture:** 不重做积分系统，也不治理 Taro 本机环境。先补齐 `share_click` 事件在前端类型、云函数 store、backend schema 三处合同，再做目标测试和微信开发者工具真机验收。

**Tech Stack:** Taro 4.1.11 + React + 微信云函数 Node.js + FastAPI/Pydantic + pytest + node:test。

---

## Scope Challenge

- 现有代码杠杆：`trackCardEvent()`、`miniEvents/store.js`、`CardEventRequest` 已经是统一事件入口，只需要补一个事件枚举，不建新埋点系统。
- 最小变更集：只改事件合同和对应测试；不碰积分计算、不碰页面视觉、不碰 Taro/Rust 环境。
- 复杂度检查：核心修复应控制在 5 个文件内；超过这个范围就是跑偏。
- 验收边界：本机 `npm run build:weapp` 已知会触发 Taro/Rust `dynamic_store` panic，本轮不把它作为代码通过/失败判断。
- 记录边界：当前 `INDEX.md` 指向 `phase1001` 的界面核实记录已经漂移，执行收口时要用新 phase 纠正，不覆盖现有 AI 出卡记录。

## Files

- Modify: `hotpost-mini/hotpost-mini-app/src/services/mini-events.ts`
- Modify: `hotpost-mini/hotpost-mini-app/cloudfunctions/miniEvents/store.js`
- Modify: `hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-events.test.mjs`
- Modify: `backend/app/schemas/hotpost_clues.py`
- Modify: `backend/tests/api/test_hotpost_clues.py`
- Modify: `reports/phase-log/INDEX.md`
- Create: `reports/phase-log/phase1004.md` or next free phase number if `phase1004.md` already exists

## Task 1: 写失败测试，证明 `share_click` 现在没进小程序云函数事件合同

**Files:**
- Modify: `hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-events.test.mjs`

- [x] **Step 1: Add the failing node:test case**

Append this test after `mini events store normalizes card event payload`:

```js
test('mini events store accepts share click card event', () => {
  assert.equal(ALLOWED_EVENT_TYPES.has('share_click'), true)

  const doc = buildEventDoc(
    {
      eventType: 'share_click',
      cardId: 'card-share-1',
      categoryId: 'signal',
    },
    { OPENID: 'openid-share' },
  )

  assert.equal(doc.openid, 'openid-share')
  assert.equal(doc.event_type, 'share_click')
  assert.equal(doc.card_id, 'card-share-1')
  assert.equal(doc.category_id, 'signal')
})
```

- [x] **Step 2: Run the test and verify it fails**

Run:

```bash
node cloudfunctions/tests/mini-events.test.mjs
```

Expected before implementation: FAIL because `ALLOWED_EVENT_TYPES.has('share_click')` is `false` or `buildEventDoc()` throws `EVENT_TYPE_NOT_ALLOWED`.

## Task 2: 写失败测试，证明 backend API schema 还不接受 `share_click`

**Files:**
- Modify: `backend/tests/api/test_hotpost_clues.py`

- [x] **Step 1: Add the failing pytest case**

Append this test after `test_hotpost_card_event_records_metric`:

```python
@pytest.mark.asyncio
async def test_hotpost_card_event_accepts_share_click(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.endpoints import hotpost_clues

    redis = _FakeRedis()
    monkeypatch.setattr(hotpost_clues.Redis, "from_url", lambda *args, **kwargs: redis)
    listing = await client.get("/api/hotpost/cards")
    card_id = listing.json()["items"][0]["card_id"]

    resp = await client.post(
        "/api/hotpost/card-events",
        json={"type": "share_click", "card_id": card_id, "category_id": "all"},
    )

    assert resp.status_code == 200
    assert any("share_click" in fields for fields in redis._hashes.values())
```

- [x] **Step 2: Run the focused backend test and verify it fails**

Run:

```bash
cd backend && python -m pytest tests/api/test_hotpost_clues.py::test_hotpost_card_event_accepts_share_click -q
```

Expected before implementation: FAIL or 422 because `share_click` is not part of `CardEventType`.

## Task 3: 补齐三处事件合同

**Files:**
- Modify: `hotpost-mini/hotpost-mini-app/src/services/mini-events.ts`
- Modify: `hotpost-mini/hotpost-mini-app/cloudfunctions/miniEvents/store.js`
- Modify: `backend/app/schemas/hotpost_clues.py`

- [x] **Step 1: Add frontend type support**

In `hotpost-mini/hotpost-mini-app/src/services/mini-events.ts`, update `MiniEventType` to include `share_click`:

```ts
export type MiniEventType =
  | 'home_view'
  | 'detail_view'
  | 'back_click'
  | 'origin_click'
  | 'quote_click'
  | 'share_click'
  | 'category_click'
  | 'type_click'
  | 'favorite_click'
  | 'favorites_view'
  | 'profile_view'
  | 'meter_prompt_shown'
  | 'login_success'
```

- [x] **Step 2: Add cloud function allowlist support**

In `hotpost-mini/hotpost-mini-app/cloudfunctions/miniEvents/store.js`, update `ALLOWED_EVENT_TYPES`:

```js
const ALLOWED_EVENT_TYPES = new Set([
  'home_view',
  'detail_view',
  'back_click',
  'origin_click',
  'quote_click',
  'share_click',
  'category_click',
  'type_click',
  'favorite_click',
  'favorites_view',
  'profile_view',
  'meter_prompt_shown',
  'login_success',
])
```

- [x] **Step 3: Add backend schema support**

In `backend/app/schemas/hotpost_clues.py`, update `CardEventType`:

```python
CardEventType = Literal[
    "home_view",
    "detail_view",
    "back_click",
    "origin_click",
    "quote_click",
    "share_click",
    "category_click",
    "type_click",
    "favorite_click",
    "favorites_view",
    "profile_view",
]
```

## Task 4: 跑目标验证，不把历史噪音伪装成本轮失败

**Files:**
- No source edits

- [x] **Step 1: Verify cloud function event contract**

Run:

```bash
node cloudfunctions/tests/mini-events.test.mjs
```

Expected: PASS, including `mini events store accepts share click card event`.

- [x] **Step 2: Verify backend event contract**

Run:

```bash
cd backend && python -m pytest tests/api/test_hotpost_clues.py::test_hotpost_card_event_records_metric tests/api/test_hotpost_clues.py::test_hotpost_card_event_accepts_share_click -q
```

Expected: PASS.

- [x] **Step 3: Verify TypeScript no longer reports `share_click`**

Run:

```bash
cd hotpost-mini/hotpost-mini-app && ./node_modules/.bin/tsc --noEmit --skipLibCheck
```

Expected: command may still exit `2` because this repo already has unrelated TypeScript issues, but the output must no longer contain:

```text
src/pages/velocity/index.tsx(217,26): error TS2345: Argument of type '"share_click"' is not assignable to parameter of type 'CardEventType'.
```

## Task 5: 修正 phase-log 指针并记录本轮执行结果

**Files:**
- Modify: `reports/phase-log/INDEX.md`
- Create: `reports/phase-log/phase1004.md` or next free phase number if `phase1004.md` already exists

- [x] **Step 1: Create the phase record after code verification**

Use this content, with the phase number adjusted only if `phase1004.md` already exists:

```markdown
# phase1004

1. 这轮达到的目的
- 把小程序界面优化后的 `share_click` 事件合同补齐，并重新定义验收边界。

2. 当前状态变化
- `share_click` 已进入前端事件类型、`miniEvents` 云函数 allowlist 和 backend `CardEventType`。
- 小程序云函数事件测试与 backend 事件测试已覆盖 `share_click`。
- 本机 Taro build panic 继续作为环境问题保留，不再误判成界面源码失败。

3. 还没完成什么
- 还没在微信开发者工具和真机上完成视觉与分享链闭环验收。

4. 下一步做什么
- 用微信开发者工具清缓存重新编译，真机验积分页产品态、sticky 顶部、详情分享和邀请奖励链。
```

- [x] **Step 2: Update `INDEX.md` top entry**

Replace the stale entry that currently points interface validation to `phase1001.md` with:

```markdown
- 已核实上一轮小程序界面优化只能算“源码侧完成”，本轮已补齐详情页 `share_click` 事件合同；微信开发者工具 / 真机验收仍是下一步：
  - [phase1004.md](/Users/hujia/Desktop/RedditSignalScanner/reports/phase-log/phase1004.md)
```

## Task 6: 微信开发者工具 / 真机验收清单

**Files:**
- No source edits

- [ ] **Step 1: Rebuild in WeChat Developer Tools**

Open the `hotpost-mini/hotpost-mini-app` project, confirm root points to `dist-dev/` for local dev, then run “清缓存并重新编译”.

Expected: simulator can open 首页、详情页、积分中心.

- [ ] **Step 2: Validate UI product state**

Check exactly these three screens:

```text
积分中心：规则区不出现后台解释；积分消费记录默认收起；按钮文案是前台用户能懂的话。
详情页：顶部“返回首页”滑动时不滚走；点击后回首页 tab。
积分页：顶部“返回”滑动时不滚走；样式和详情页顶部一致。
```

- [ ] **Step 3: Validate share behavior**

Check exactly these two flows:

```text
详情页底部分享：好友打开后进入同一张详情页。
积分中心 / 积分不足弹层分享：好友打开后进入首页，并携带 inviteToken；新用户首次授权登录后邀请人 +30。
```

Expected: if真机分享链失败，先看云函数 `miniPoints` / `miniEvents` 是否已重新部署，不回头改页面样式。

## Final Verification Gate

- `node cloudfunctions/tests/mini-events.test.mjs` passes.
- Focused backend pytest for card events passes.
- `share_click` TypeScript error disappears.
- `reports/phase-log/INDEX.md` no longer points interface validation to an AI 出卡 phase.
- 微信开发者工具 / 真机验收结果被写回新的 phase-log。

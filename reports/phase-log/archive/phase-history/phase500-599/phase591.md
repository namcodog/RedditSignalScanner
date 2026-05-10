# Phase 591 - 收掉 06 / 下一步 的系统口气

## Goal
- 解决小程序 `06 / 下一步` “看不懂”的问题。
- 去掉系统内部 note 的曝光。
- 把动作建议压成更短、更像人话的两步。

## Work
- 后端：
  - `backend/app/services/hotpost/response_bundle.py`
    - 新增 `_rewrite_rant_action()`
    - 把长句建议压成更短的人话动作
    - 对当前转化类 `rant` 优先输出两类短句：
      - `先把 TikTok 能记录到的下单链路补齐...`
      - `先查点击到下单这段漏斗...`
- 小程序：
  - `hotpost-mini/hotpost-mini-app/src/pages/friction/helpers.ts`
    - 新增 `nextStepNote()`
    - 过滤 `关键词过长 / 已拆分为` 这类内部 note
  - `hotpost-mini/hotpost-mini-app/src/pages/friction/sections.tsx`
    - `06 / 下一步` 改成“两步卡片”
    - 不再把 note、建议、追问挤成一整段

## Verification
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_response_bundle.py -q`
  - `14 passed`
- `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - `Compiled successfully`
- 真无缓存 live：
  - query=`为什么tiktok上做的内容有流量但却没有转化购买？`
  - `from_cache=false`
  - `status=completed`
  - `recommended_actions`：
    - `先把 TikTok 能记录到的下单链路补齐，不然现在算不清广告到底有没有带来订单。`
    - `先查点击到下单这段漏斗，重点看商品页、落地页和结账有没有断点。`

## Result
- `06 / 下一步` 现在不该再像一大坨系统说明。
- 你在小程序里看到的应该是：
  - 不展示“关键词过长，已拆分为 2 次查询”
  - 两条短动作建议
  - 最后才是追问关键词

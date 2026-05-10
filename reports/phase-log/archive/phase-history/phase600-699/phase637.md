# Phase 637 - 小程序需求信号卡完整迁移落地

## 时间
- 2026-04-07

## 目标
- 把小程序卡片从旧的“商业观察 / 写作角度”口径，完整迁到新的“需求信号卡”口径。
- 不改后端 schema 名，不改请求接口，但把生成链、前端解释链、旧卡回填链一次打通。

## 发现
- 旧卡主链此前没有沉淀正式的 LLM 出卡流程，`summary_line / audience / why_now / detail` 主要靠系统外统一写法灌入。
- 当前真正缺的不是字段，而是内容合同：
  - 信号卡：症状 + 值不值得追
  - 拆解卡：症状 + 真根因 + 值不值得追
- 首页如果要展示 signal meter，现有 `CardSummary` 不够，需要最小增字段：
  - `top_community`
  - `thread_count`
  - `community_count`
- 旧 `published` 数据存在历史契约缺口：
  - 多张卡没有 `signal_level`
- 独立回填脚本最初没有先加载 `backend/.env`，导致模型调用错误地打到 OpenAI 主站；修正后已能按 `OPENAI_BASE=https://openrouter.ai/api/v1` 走外部模型。

## 实现

### 后端
- 新增卡片内容生成链：
  - `backend/app/services/hotpost/card_content_generator.py`
  - `backend/app/services/hotpost/card_content_prompts.py`
  - `backend/config/card_content_rules.yaml`
- 新生成链规则：
  - 所有 draft 先按 `📡 信号` 合同生成
  - 只有满足证据门槛，才升级成 `🔍 拆解`
  - 拆解门槛：
    - `thread_count >= 2`
    - `evidence_quotes >= 3`
    - 有 `thesis`
    - `quote_pack >= 2`
    - 且 `community_count >= 2` 或 `thread_count >= 3`
- `preview_quote` 不再默认拿第一条，而是由生成链先重排 `evidence_quotes`，发布时继续复用现有发布逻辑。
- 双 seed 入口都已接入自动填充：
  - `backend/app/api/v1/endpoints/hotpost_card_candidates.py`
  - `backend/app/api/v1/endpoints/hotpost_card_review.py`
- 摘要接口补最小展示字段：
  - `top_community`
  - `thread_count`
  - `community_count`
- 详情兼容层已补：
  - 即使旧 published 顶层没有这些字段，也会从 `source_module` 映射出来。
- 新增旧卡回填脚本：
  - `backend/scripts/backfill_hotpost_card_content.py`

### 前端
- 前台统一口径：
  - `validate -> 📡 信号`
  - `write -> 🔍 拆解`
- 首页 Tab 改成：
  - `全部 / 📡 信号 / 🔍 拆解`
- 首页 Hero 改成：
  - `需求信号`
  - `把 Reddit 上零散的真人讨论，整理成你能快速判断的信号。`
- 卡片预览新增 `signal meter`：
  - 意图温度
  - 帖子数
  - 社区数
  - top community
- 详情页重写语义：
  - `audience` 改成“谁在聊”
  - `why_now` 改成“这波为什么要看”
  - `商业观察 / 写作角度` 改成 `📡 信号 / 🔍 拆解`
  - `WriteBlock` 新增 `quote_pack` 展示
- 收藏页类型补齐新摘要字段，避免新 `CardSummary` 契约把收藏页打坏。

## 改动文件
- `backend/app/schemas/hotpost_clues.py`
- `backend/app/services/hotpost/clues_catalog.py`
- `backend/app/services/hotpost/card_draft_builder.py`
- `backend/app/api/v1/endpoints/hotpost_card_candidates.py`
- `backend/app/api/v1/endpoints/hotpost_card_review.py`
- `backend/app/services/hotpost/card_content_generator.py`
- `backend/app/services/hotpost/card_content_prompts.py`
- `backend/config/card_content_rules.yaml`
- `backend/scripts/backfill_hotpost_card_content.py`
- `backend/tests/services/hotpost/test_card_content_generator.py`
- `backend/tests/api/test_hotpost_card_candidates.py`
- `backend/tests/api/test_hotpost_card_review.py`
- `backend/tests/api/test_hotpost_card_draft_review.py`
- `backend/tests/api/test_hotpost_clues.py`
- `hotpost-mini/hotpost-mini-app/src/services/clues.ts`
- `hotpost-mini/hotpost-mini-app/src/services/favorites.ts`
- `hotpost-mini/hotpost-mini-app/src/components/CluePreviewCard.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/index/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-view-model.ts`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail-sections.tsx`

## 验证

### 后端测试
- 执行：
  - `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_card_content_generator.py backend/tests/api/test_hotpost_card_candidates.py backend/tests/api/test_hotpost_card_review.py backend/tests/api/test_hotpost_card_draft_review.py backend/tests/api/test_hotpost_clues.py backend/tests/api/test_hotpost_card_drafts.py -q`
- 结果：
  - `21 passed`

### 前端构建验证
- 执行：
  - `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：
  - 进入 Taro weapp 构建链，但在当前环境触发底层系统库 panic：
    - `system-configuration ... Attempted to create a NULL object`
- 该错误发生在构建器/系统层，不是本轮卡片迁移代码直接报错。

### TypeScript 静态编译
- 执行：
  - `cd hotpost-mini/hotpost-mini-app && npx tsc --noEmit`
- 结果：
  - 工程里仍有大量既存的 Taro / node_modules 类型噪音
  - 本轮新增的真实类型问题已补齐：
    - 收藏页 `FavoriteCard` 缺少新摘要字段

### 旧卡回填
- 已执行：
  - `cd backend && PYTHONPATH=. python scripts/backfill_hotpost_card_content.py`
- 当前状态：
  - 代码链已打通
  - 历史数据兼容缺口已补（缺失 `signal_level` 的旧卡）
  - 独立脚本已改为先加载 `backend/.env`
  - 但这轮全量回填尚未确认完成，`backend/data/hotpost_clues.json` 还没有看到最终落盘变化
- 结论：
  - **完整迁移的代码与执行通道已落地**
  - **旧 34 张卡的最终内容回填还需要继续跑完并确认结果**

## 当前判断
- 这轮不是“先改文案，再说别的”，而是已经把：
  - 生成合同
  - 升级判定
  - 摘要展示
  - 详情解释
  - 回填脚本
  一次打通了。
- 真正还没闭环的只剩最后一步：
  - 让 34 张旧 published 卡完成新合同回填并确认落盘

## 价值
- 把旧的统一腔调卡片，迁成了有明确任务边界的需求信号产品。
- 以后不管是人补卡还是 LLM 补卡，都会被新合同约束，不会再滑回“完整但不锋利”的老路。
- 这次真正留下来的不是几句新文案，而是一条可持续的供给链。

## 下一步
1. 继续完成 34 张旧卡的全量回填，并抽检至少 5 张确认“信号 / 拆解”分类没有说谎。
2. 在微信开发者工具里重新过一遍首页和详情，确认：
   - 标签
   - signal meter
   - 详情结构
   没有真机展示回退。
3. 如果 Taro 构建 panic 持续存在，单独开一条构建链排障，不把这类系统层问题误写成卡片迁移问题。

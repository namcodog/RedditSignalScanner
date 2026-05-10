# phase705

## 结果
- 完成 `爆贴热点 V1` 的最小落地，不新增第三套系统。
- 在 `validate` 主链下新增 `lane` 语义分流：
  - `signal` -> `信号快报`
  - `hot` -> `爆贴热点`
  - `breakdown` -> `深度信号`
- 前台列表卡、详情页标签、详情块标题都已按 `lane` 区分。
- 现有 `signal-ops / breakdown-ops` 不分裂，继续复用。

## 关键实现
- 新增 `backend/app/services/hotpost/card_lane_policy.py`
  - 负责 `validate` 候选的热点 lane 推断
  - 负责老卡 lane fallback
- 后端 schema / draft / published / catalog 全链透传 `lane`
- 前台新增 lane 文案映射：
  - `hotpost-mini/hotpost-mini-app/src/constants/card-lane-copy.ts`
- 列表卡和详情页已按 lane 区分显示文案
- 云端 release 读取层补了 lane fallback，兼容旧 snapshot

## 验证
- `pytest backend/tests/services/hotpost/test_card_lane_policy.py backend/tests/services/hotpost/test_card_content_generator.py -q`
  - `29 passed`
- `node --test hotpost-mini/hotpost-mini-app/cloudfunctions/tests/mini-release.test.mjs`
  - `1 passed`
- `make hotpost-workflow-dry-run`
  - 全链正常返回

## 边界
- V1 没有新建第三套 `hot-ops`
- V1 没有新增第三套 judge / prompt / SOP
- 当前 lane 对已有老卡默认 fallback：
  - `validate -> signal`
  - `write -> breakdown`
- 真正的 `爆贴热点` 视觉效果，会从后续新发布卡开始明显出现；旧卡不会批量硬改

## 下一步
- 按现有 SOP 继续补卡
- 优先观察后续 listing-first 新卡是否自然落到 `hot` lane
- 如果热点量稳定，再决定要不要补热点专用 detail 结构 v1.1

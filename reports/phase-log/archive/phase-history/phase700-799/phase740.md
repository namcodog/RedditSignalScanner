# Phase 740

## 发现了什么

- `breakdown` 供给不再是零。修完 `breakdown_suggestion_quality.py` 之后，`list_breakdown_suggestions(limit=10)` 从 `0` 长到 `1`，并成功 materialize 出新 draft：
  - `draft-group-ai-automation-98265ccb4c`
- 这张 draft 原始版本证据方向对，但有明显模板味和杂质 quote；收稿后改成了更窄的 thesis：
  - `AI 写代码开始卡住的，不是生成，而是调顺它的那层人工成本`
- 该 draft 已发布成功：
  - `card-group-ai-automation-98265ccb4c`
  - `published_count = 94`
- mini snapshot 初次推送时短暂读到旧 release，但复跑后已对齐到：
  - `release-65b45e791128`
  - `card_count = 94`

## 是否需要修复

- `breakdown = 0` 这个硬伤这轮已经修掉。
- 但最近 `20` 张 lane mix 仍然失衡：
  - `signal = 16`
  - `hot = 3`
  - `breakdown = 1`
- 领域 mix 基本可控：
  - `ai-automation = 8`
  - `business-growth-ops = 6`
  - `ecommerce-sellers = 6`

## 精确修复方法

- 通过修 `breakdown_suggestion_quality.py`，放宽了“共享锚点必须出现在每条 quote 里”的过严限制，允许从 `matched_keywords / query / title` 获得候选级支撑。
- 手动收稿 `draft-group-ai-automation-98265ccb4c`，去掉过度发散的 thesis 和模板味文案，只保留真正被证据托住的判断。
- 成功走完：
  - `publish draft-group-ai-automation-98265ccb4c`
  - `push_mini_snapshot.py`

## 下一步系统性的计划

1. 停止继续补 `signal`。
2. 继续补 `hot` 的新供给，优先争论型题材。
3. 继续补 `breakdown` suggestion 密度，让最近 `20` 张里的 `breakdown` 从 `1` 往 `4` 拉。
4. 保持当前 `safe / harvest` collect 模式，不为补量破坏账号安全边界。

## 这次执行的价值

- 今天这轮不是“又多发一张卡”，而是把最近 `20` 张里 `breakdown = 0` 的结构性问题打掉了。
- 同时也验证了一件事：当前真正缺的不是 `signal`，而是 `hot + breakdown` 的供给密度；下一轮主线不能再漂回去。

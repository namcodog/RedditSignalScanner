# phase784

## 事项

- 按 `breakdown v1.0` 口径回灌已发布 `breakdown`
- 只处理 `lane=breakdown / card_type=write`，不碰 `signal / hot / lane=None`

## 执行边界

- 已发布 `breakdown` 总量：`34`
- 仅对这 `34` 张做受控刷新
- 不扩 schema
- 不新增状态
- 不改 `signal`
- 不改 `hot`
- 不改排序 / 分发 / feed contract

## 本轮处理

### 1. dry-run 全量 plan

- 命令：
  - `python backend/scripts/hotpost/refresh_published_card_semantics.py --lane breakdown --all --limit 40 --output-plan backend/tmp/published-breakdown-v10-refresh-plan-full.json --json`
- 结果：
  - `selected=34`
  - `merged=0`

### 2. 抽样 spot check

- 第一轮看 `5` 张 dry-run 样本
- 第二轮用当前 `mimo` 对 `6` 条 `write draft` 做只读重刷：
  - 文件：`backend/tmp/breakdown-v1-spotcheck-6.json`
- 结论：
  - `4 / 6` 明显可过 `publish`
  - `2 / 6` 仍保守留在 `rewrite`
  - 没出现“更长一点的 signal”被大面积误抬

### 3. apply 已发布 breakdown 刷新

- 命令：
  - `python backend/scripts/hotpost/refresh_published_card_semantics.py --apply-plan backend/tmp/published-breakdown-v10-refresh-plan-full.json --json`
- 结果：
  - `selected=34`
  - `merged=34`

### 4. 发布链闭环

- `python backend/scripts/hotpost/push_mini_snapshot.py`
  - `release_id=release-1c74b796833f`
  - `card_count=155`
- `python backend/scripts/hotpost/check_mini_release_sync.py`
  - `feed_contract=30/30`
  - `cloud_db copy guard: ok`

## 额外检查

- 对 full plan 做发布护栏字段扫描：
  - 扫描字段：`title / summary_line / audience / why_now`
  - 结果：`0 hits`
- `quote_pack` 里的 `... / …` 没再额外清洗
  - 原因：当前发布护栏不扫 `breakdown quote_pack`
  - 这轮不为此扩规则

## 结论

- 已发布 `breakdown` 已完成统一刷新：`34 / 34`
- 当前三条主线已发布池状态：
  - `signal v1.0`：已统一
  - `hot v1.0`：已统一
  - `breakdown v1.0`：已统一
- 当前发布总卡数：`155`
- 当前 release：`release-1c74b796833f`

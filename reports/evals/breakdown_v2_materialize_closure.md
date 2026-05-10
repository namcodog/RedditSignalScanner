# Breakdown V2 Materialize Closure
Date: 2026-04-08

## 结论

`breakdown V2` 已完成最关键的自动化闭环：

- 系统会扫描当前合格的 `breakdown suggestions`
- 自动生成 `write draft`
- 保留人工 `review / publish`
- 不再要求手动逐条 `seed-group`

这次没有把拆解变成自动上线系统，边界仍然守住：

- 自动化止于 `draft`
- `publish` 仍是人工闸门

## 新增能力

### 1. 自动 materialize 服务

- `backend/app/services/hotpost/breakdown_draft_materializer.py`

职责：

- 读取当前 `suggestions`
- 逐条转成 grouped write draft
- 调用现有 `generate_card_content`
- 只接受最终仍为 `write` 的结果
- 自动保存 draft
- 对已存在 draft/card 做去重跳过

### 2. API 入口

- `POST /api/hotpost/card-review/materialize-drafts`

返回：

- `materialized`
- `skipped_existing`
- `failed`

### 3. CLI 入口

- `backend/scripts/hotpost/materialize_breakdown_drafts.py`

用途：

- 本地/定时任务可直接跑
- 自动加载 `backend/.env`

## 真实验证

当前真实 suggestion：

- `suggestion-ai-automation-94bfe667d1`
- `topic_pack = agent-builder`

第一次执行：

```json
{
  "count": 1,
  "materialized": 1,
  "skipped_existing": 0,
  "failed": 0
}
```

已真实落盘：

- `draft-group-ai-automation-94bfe667d1`
- `card_type = write`

第二次重复执行：

```json
{
  "count": 1,
  "materialized": 0,
  "skipped_existing": 1,
  "failed": 0
}
```

说明：

- 自动去重生效
- 不会重复制造拆解草稿

## 当前产出示例

真实生成的拆解草稿：

- title:
  - `Cursor的SQL生成让我紧张，但原因可能不是我想的那样`
- thesis:
  - `用户对AI代码助手生成特定SQL模式的紧张感，可能源于对AI行为的误解——AI并非在犯错，而是在模仿和适应用户已有的代码风格。`

## 通过项

- suggestion -> write draft 自动化已打通
- 静默降级已被拒绝
- 重复落草稿已被拒绝
- API / script / service 三层入口一致

## 不在本次范围

- 不自动 publish
- 不自动替代人工 review
- 不把 collect 入口和 breakdown materialize 强耦合

## 最终判断

`breakdown V2` 已经从“人工挑 suggestion 再 seed-group”推进成：

`suggestions -> auto materialize write drafts -> human review -> publish`

这条链已经可用，可以作为后续拆解供给的正式主链。

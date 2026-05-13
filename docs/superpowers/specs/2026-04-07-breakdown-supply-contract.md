# Contract: Breakdown Supply
Date: 2026-04-07
Branch: current workspace

## 1. 目标

这份合同只解决一件事：

**让 `🔍 拆解` 成为一种有明确证据门槛、节奏更慢、质量更高的卡片供给。**

它不是为了让拆解数量变多，而是为了让拆解不再靠单帖硬写。

---

## 2. 产品定义

### `📡 信号`

- 单点问题 / 单条讨论 / 单个判断线索
- 可以日更
- 可以当天采集、当天发布

### `🔍 拆解`

- 不是单帖总结
- 是近 `48 小时到 7 天` 内多条相关讨论压缩出来的判断卡
- 默认比信号慢
- 不追求日更数量

一句话：

- `信号` 是日报产品
- `拆解` 是滚动聚合产品

---

## 3. 自动化边界

### V1 正式边界

系统自动做到这里：

```text
collect
  -> signal candidates
  -> breakdown suggestions
```

系统**不自动 publish**。

人工保留在这里：

```text
breakdown suggestion
  -> seed-group
  -> draft
  -> review
  -> publish
```

### 明确禁止

- 不允许 `collect -> auto publish breakdown`
- 不允许靠 prompt 把单帖写成拆解
- 不允许为了提高拆解数量降低证据门槛

---

## 4. 触发条件

### 4.1 进入拆解候选池

必须同时满足：

- 同一个 `source_scope_id`
- 同一个 `topic_pack_id`
- 时间窗口位于近 `48h - 7d`
- 至少 `2` 条 candidate
- 更理想是 `3` 条

### 4.2 允许生成 breakdown suggestion

必须同时满足：

- 至少 `2` 个不同帖子
- 至少 `2` 条非重复 quote
- 最好满足：
  - `2` 个社区
  - 或 `3` 个线程
- 能明确写出一句“误判纠正句”

误判纠正句模板：

- 表面看是 `A`，其实真正卡在 `B`
- 大家嘴上在说 `A`，真正不能忽视的是 `B`

### 4.3 不允许升拆解

任一命中即禁止：

- 单帖
- 跨 `source_scope_id`
- 跨 `topic_pack_id`
- 只有一条强帖，其他只是附和
- meme / promo / 公告 / 新闻帖混进来
- 只是同类目，不是同一个决策问题
- 提不出成立的误判纠正句

---

## 5. 人工组卡规则

运营手动确认时，只看 3 个问题：

### 5.1 是不是同一个对象

比如都在讲：

- 饮料分配器
- 厨卫耐用品品牌
- 手机 Agent 安全

### 5.2 是不是同一个决策张力

比如都在回答：

- 该买什么材料
- 该信什么品牌
- 该不该把权限交给 Agent

### 5.3 能不能写出一句误判纠正句

如果写不出来：

- 不组卡
- 继续做 `📡 信号`

---

## 6. suggestion 数据合同

`breakdown suggestion` 至少包含：

- `suggestion_id`
- `source_scope_id`
- `topic_pack_id`
- `candidate_ids`
- `thread_count`
- `community_count`
- `intent_tags`
- `evidence_score`
- `hypothesis`
- `reason_codes`

其中：

- `hypothesis` = 误判纠正句草案
- `reason_codes` = 为什么这组 candidate 被认为值得合并

---

## 7. 前端解释合同

前端不新增第三种标签，只解释现有 `🔍 拆解`。

### 首页标签说明

`拆解：基于近几天多条相关讨论提炼，不是单帖总结。`

### 详情页说明

`这张拆解卡来自多条相关讨论的合并判断，用来帮助你看清同一个问题的更深层卡点。`

### 禁止文案

- 不写“AI 深度分析”
- 不写“自动得出结论”
- 不写“代表市场真相”

---

## 8. 供给比例

当前目标比例：

- `📡 信号`：`70% - 80%`
- `🔍 拆解`：`20% - 30%`

在供给刚起步阶段，拆解更少是正常现象。

---

## 9. 实现顺序

### V1

- 新增 `breakdown_candidate_clusterer`
- 自动生成 suggestion
- 人工挑 suggestion
- 复用现有 `seed-group -> draft -> publish`

### V2

- 自动把 suggestion 变成 breakdown draft
- 但仍保留人工 review / publish

---

## 10. 不在范围内

- 不改前端主信息架构
- 不新增“拆解”之外的新卡类型
- 不把拆解变成自动上线系统
- 不用 prompt 替代证据聚合

# Phase 814: hot 真实争议占比合同补强

## 发现

- 新版“小程序独立线”方案方向已经正确，但还缺两类硬约束：
  - 工程口子
  - LLM 价值口子
- 如果不补这两类约束，后续实现很容易退化成：
  - 只抓一批评论
  - 只算一个比例
  - 没有审计字段
  - LLM 只做低价值弱分类

## 是否需要修复

- 需要。
- 这一步不改代码，先把合同补强，避免后续实现跑偏。

## 精确修复方法

已更新：

- `docs/superpowers/specs/2026-04-14-hot-real-controversy-ratio-design.md`
- `task_plan.md`
- `findings.md`
- `progress.md`

新增固定合同：

### 工程口子

- 固定抓取预算：
  - `mode="smart_shallow"`
  - `limit=40`
  - `depth=2`
- 必须有总超时
- 抓取失败或样本不足时：
  - 只允许 `confidence=low`
  - 禁止回退旧模板桶位
- 发布产物必须保留：
  - `post_id`
  - `sample_size`
  - `sampled_at`
  - `fetch_status`
  - `llm_summary_version`

### LLM 价值口子

- LLM 必须做：
  - 立场归并
  - 分歧点提炼
  - 代表观点抽取
  - 低置信识别
- 不允许把 LLM 降级成简单情绪打分器

## 下一步系统计划

1. 先按新合同补测试
2. 再实现抓评论与单卡汇总
3. 最后跑 mini 发布与 spot check

## 价值

- 这次把“真实争议图”从一个可能做成浅功能的需求，收成了有工程边界、有审计字段、有 LLM 价值要求的正式合同。

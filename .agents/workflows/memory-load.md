---
description: 加载记忆上下文 — 读取全部 5 个记忆文件，输出完整上下文摘要
---

# /memory-load — 全量加载记忆

用于复杂任务前的深度上下文加载。日常启动协议已在 GEMINI.md 里自动执行，本 workflow 是补充。

## 步骤

// turbo-all

1. 读 `mem/MEMORY.md` 全文，重点提取：
   - `Current State` 段（实时状态）
   - `Pending Implementation` 段（待办事项）
   - 最近 5 条 `Calibration Log`
   - `Recent Actions` 和 `Recent Decisions`（最近 3 条）

2. 读 `mem/IDENTITY.md` 全文，提取：
   - Core Goals
   - Decision Rules
   - Thinking Style
   - 优先级事项

3. 读 `mem/USER.md` 全文，提取：
   - Interest Graph（加权兴趣图谱）
   - Active Projects（当前活跃项目）
   - Media Channels（社媒使用习惯）
   - Hobbies & Aesthetics

4. 读 `mem/PLAYBOOK.md` 全文，提取：
   - 被证伪的模式（避免重复建议）
   - 诊断框架

4. 读 `mem/SOUL.md` 全文，提取：
   - Core Truths
   - Memory Protocol
   - Boundaries

5. 读 `mem/ARCHIVE.md`（如存在），快速浏览主题分类

6. 输出一份**简洁的上下文摘要**（不超过 30 行），格式：

```
## 记忆加载完成

### 当前状态
[从 Current State 段提取]

### 待落实
[从 Pending Implementation 提取]

### 近期轨迹
[最近 3 条行动/决策]

### 底层心智要点
[IDENTITY.md 的 Core Goals + Decision Rules 精简版]

### 红线提醒
[PLAYBOOK.md 的被证伪模式列表]
```

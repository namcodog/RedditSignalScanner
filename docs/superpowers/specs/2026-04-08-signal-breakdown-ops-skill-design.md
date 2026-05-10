# Design: Signal / Breakdown Ops Skills
Date: 2026-04-08
Branch: current workspace

## Problem Statement

当前小程序已经有两条稳定主链：

- `📡 signal` 生产链
- `🔍 breakdown` 生产链

但这些能力现在主要固化在：

- backend 代码
- judge / gate / materialize 脚本
- phase-log 和设计文档

这对系统运行够了，但对后续团队/代理工作流还不够顺手。

真正的问题不是“能不能生成卡”，而是：

**要不要把日常操作层再封一层成 skill，方便 workflow 调用。**

## Premise Challenges

### 挑战 1：是不是应该把运行时主链直接做成 skill？

不应该。

原因：

- 运行时主链已经在 backend 代码里
- 如果再在 skill 里复制一套业务逻辑，会形成第二真相源
- 以后 prompt、gate、pack 规则一改，skill 和代码很容易漂

结论：

**运行时继续留在代码里，不做“skills 驱动的生产系统”。**

### 挑战 2：是不是完全不需要 skill？

也不是。

原因：

- 现在操作层已经足够复杂
- 后面团队/代理要频繁做：
  - 日常 signal 产卡
  - breakdown draft materialize
  - 质量检查
  - 发布前 review
- 如果全靠人记命令、记文档，效率会掉

结论：

**需要 skill，但只能做“薄 orchestration skill”，不能做业务逻辑 skill。**

## Options Considered

| Option | What | Effort | Risk | Best for |
|---|---|---:|---:|---|
| A. 不做 skill | 继续只靠代码 + SOP + 手工命令 | S | 中 | 团队很小，只有一个人维护 |
| B. 做两个薄 skill | `signal-ops` + `breakdown-ops`，只封操作顺序与脚本调用 | M | 低 | 当前阶段，最稳 |
| C. 做 runtime skill system | 用 skills 直接驱动生成、评审、发布 | L | 高 | 不适合当前系统 |

## Chosen Direction

选择 **B. 两个薄 skill**。

具体是：

### 1. `signal-ops`

职责：

- 跑 signal 日常链
- 指导使用：
  - collect
  - candidate 检查
  - input quality gate 结果确认
  - draft / publish 前 review

它做的是：

- 调脚本
- 给操作顺序
- 给检查清单

它不做的是：

- 重写生成逻辑
- 复制 pack 规则
- 复制 prompt 内容

### 2. `breakdown-ops`

职责：

- 跑 breakdown 日常链
- 指导使用：
  - suggestion 检查
  - coherence gate 结果确认
  - materialize write draft
  - overlap audit
  - publish 前 review

它做的是：

- 调脚本
- 给操作顺序
- 给 review 清单

它不做的是：

- 重写 suggestion 聚类逻辑
- 重写 breakdown judge
- 复制 materialize 逻辑

## Skill Boundary

这两个 skill 只允许引用：

- 已存在的 backend 脚本
- 已存在的 judge / audit / materialize 命令
- 已存在的 SOP 文档

它们不允许内嵌：

- pack 业务规则
- prompt 细节
- gate 阈值
- publish 判断逻辑

一句话：

**skill 负责“怎么调用系统”，代码负责“系统怎么工作”。**

## Success Criteria

做完后满足这 4 条：

1. 新人或代理可以不翻一堆 phase-log，就知道 signal / breakdown 各自怎么跑
2. skill 不会成为第二套业务规则真相源
3. 日常运行与优化运行的入口分开
4. 以后换 prompt / gate / pack 逻辑时，不需要重写 skill 主体

## Risks

### 风险 1：skill 变厚

缓解：

- skill 里只放操作顺序和调用入口
- 不放业务规则

### 风险 2：skill 和代码漂移

缓解：

- 所有业务判断都继续以 backend 代码和正式设计文档为准
- skill 只引用，不复制

### 风险 3：把优化流和生产流混在一起

缓解：

- `signal-ops` / `breakdown-ops` 只服务日常生产与 review
- 优化流继续单独走 eval / judge / canary / promote

## NOT in Scope

- 不做 runtime skill engine
- 不做自动自治 workflow controller
- 不把优化工作流直接封进这两个 skill
- 不在 skill 里复制 prompt、pack、gate 规则

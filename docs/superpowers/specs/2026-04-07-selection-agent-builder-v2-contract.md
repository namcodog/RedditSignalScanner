# Contract: Selection-Signals / Agent-Builder / Breakdown V2
Date: 2026-04-07
Branch: current workspace

## 1. 目标

这份小合同只解决一件事：

**先把 `selection-signals` 和 `agent-builder` 做成下一阶段最值得投入的 signal 主战场，再决定何时推进 `breakdown V2`。**

顺序锁死为：

1. `selection-signals`
2. `agent-builder`
3. `breakdown V2`

不倒序，不并行铺开。

---

## 2. 为什么是这两个 pack

### `selection-signals`

- 最接近产品当前主价值：
  - 更早看见真实需求信号
- 最容易被用户感知到价值
- 后面天然适合进入拆解
- 必须守住边界：
  - **是选品信号，不是爆品推荐**

### `agent-builder`

- AI 侧最有判断密度的一条线
- 比 `tools-efficiency` 更像真实落地门槛
- 适合后面成为拆解的重要来源
- 当前样本更薄，所以：
  - **先轻量推进，不和 `selection-signals` 同节奏重投入**

---

## 3. 不做什么

- 不直接开 `breakdown V2`
- 不同时扩更多 pack
- 不继续重推 `tools-efficiency`
- 不把 `selection-signals` 写成“推荐你卖什么”
- 不把 `agent-builder` 写成“技术圈新闻流”

---

## 4. 执行顺序

## 4.1 第一阶段：`selection-signals`

目标：

**把它推进成下一个拥有专用 signal 写法的成熟 pack。**

按这个顺序做：

1. 审供给是否够格
2. 修供给
3. 建 pack eval cohort
4. 跑 judge
5. 做小 canary
6. 赢了再 promote

### 验收标准

至少满足这些再算过关：

- 能稳定产出过 `signal input quality gate` 的 candidate
- judge 已经能清楚打出高频坏法
- 至少有一个定向变体赢过全局基线
- 可以像 `paid-economics` 一样 promote 到生产链

---

## 4.2 第二阶段：`agent-builder`

目标：

**先确认它值不值得做成下一个成熟 pack，而不是一上来就重投入。**

按这个顺序做：

1. 先做轻量供给审计
2. 确认样本厚度和输入质量
3. 只有盘子够厚，才建 pack eval cohort
4. 只做小 canary，不直接上专用写法 promote

### 验收标准

至少满足这些再算准备好：

- 样本不再明显偏薄
- 能稳定通过 `signal input quality gate`
- judge 能稳定识别它的独立失败模式
- 有资格进入正式 pack signal 实验

如果做不到：

- 不强推
- 保留为观察中的高潜 pack

---

## 4.3 第三阶段：`breakdown V2`

只有当前两步满足条件，才开。

### 触发条件

至少满足其中两条：

- `selection-signals` 已经形成稳定 signal 主战场
- `agent-builder` 已经进入正式 pack signal 实验
- 拆解 suggestion 池里，这两个 pack 已经持续出现高质量候选
- 不再只是单帖弱证据，而是真正开始出现多帖共指

### 目标

`breakdown V2` 不是为了让拆解变多，而是：

**让 `selection-signals` 和 `agent-builder` 成为最先稳定产出高质量拆解的主战场。**

---

## 5. 方法复制的边界

这次复制的是：

- `eval -> judge -> canary -> promote` 这套方法

不是复制：

- `paid-economics` 的文案
- `paid-economics` 的业务判断
- `paid-economics` 的专用写法本身

一句话：

**复制的是工作流，不是抄写法。**

---

## 6. 成功定义

这条小合同完成时，应该看到的是：

- `selection-signals` 成为第二个成熟 pack
- `agent-builder` 至少完成 readiness 判断
- `breakdown V2` 的启动条件被明确锁死

如果三件事都没做到，就不算完成。

---

## 7. 当前结论

当前主线已经确定：

- 先做 `selection-signals`
- 再做 `agent-builder`
- 再推进 `breakdown V2`

这是接下来一段时间内的默认执行顺序，除非后续真实验证把它推翻。

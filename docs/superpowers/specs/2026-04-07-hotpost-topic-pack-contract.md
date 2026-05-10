# Hotpost Mini Topic-Pack 合同

## 1. 目标

这份合同只解决一件事：

**在不改前端的前提下，把 hotpost-mini 的后端内容供给重新排布。**

前台继续保持：

- `📡 信号`
- `🔍 拆解`

不新增“选品信号”前端标签。
这次调整的是**后端内容路由和供给比例**，不是 UI 分类。

---

## 2. 硬约束

### 2.1 不碰前台分类

- 前端不新增“选品信号”
- 前端不新增第四个入口
- `📡 信号 / 🔍 拆解` 仍然是唯一深度轴

### 2.2 不造第二套全局 vertical

- 这份合同只属于 `hotpost-mini`
- 只定义：
  - `source_scope`
  - `topic_pack`
  - 供给权重
- **不复用主系统数据表，不依赖主系统 warzones 数据链**
- 也**不把这份合同升级成新的全局 vertical SSOT**

一句话：

**全局 vertical 不动；hotpost-mini 在自己现有的 3 个 source scope 下面，增加一层 topic-pack 路由。**

### 2.3 “选品”只做信号，不做推荐

允许：

- 哪类需求在反复出现
- 哪类产品缺口被反复提
- 哪类类目开始变挤、变贵、变难做
- 哪类机会值得继续追

不允许：

- 直接推荐卖什么
- 直接下“这个会爆”的结论
- 把卡片写成爆品推荐器

---

## 3. Source Scope 不变

继续保留 3 个现有 scope：

1. `ai-automation`
2. `ecommerce-sellers`
3. `business-growth-ops`

变的是：**每个 scope 内部的 topic-pack 合同。**

---

## 4. Topic-Pack 合同

## 4.1 `ecommerce-sellers`

### 核心目标

把电商卡从“卖家运营问题流”，改成：

- `选品信号`
- `类目风向`
- `kill signals`

其中：

- **选品信号是主供给**
- `kill signals` 保留，但降权

### Topic Packs

| topic_pack | 目标占比 | 作用 | 典型内容 |
|---|---:|---|---|
| `selection-signals` | 60% | 主供给 | 需求缺口、替代需求、反复被提的产品机会、值得继续追的细分品类 |
| `category-winds` | 25% | 次主供给 | 类目风向、消费偏好变化、类目拥挤度、价格敏感、需求热区变化 |
| `kill-signals` | 15% | 否决信号 | 运费、仲裁、平台风险、单位经济、费用结构、回款、平台规则 |

### `selection-signals` 覆盖的细分方向

这批是**电商选品信号的主覆盖面**：

- 宠物
- 咖啡
  - 咖啡机
  - 咖啡豆
  - 磨豆 / 萃取周边
- 户外
- EDC
- 家居
- 3C（先作为电商内部子方向，不单独升成新 scope）

### 社区方向

`selection-signals` 不以卖家社区为主，而以：

- 买家社区
- 爱好者社区
- 重度使用者社区

为主供给源。

卖家社区继续保留，但它更适合：

- `category-winds`
- `kill-signals`

### 判断原则

- 卖家运营问题不删，但不能继续占据多数
- 电商卡应该越来越像：
  - “什么值得继续看”
  - 而不是：
  - “平台又出什么问题了”

---

## 4.2 `ai-automation`

### 核心目标

把 AI 卡从“泛 AI 热点”，收成三类清晰供给：

- 上游风向
- 工具与效率
- builder 基建

### Topic Packs

| topic_pack | 目标占比 | 作用 | 典型内容 |
|---|---:|---|---|
| `upstream-winds` | 25% | 风向层 | 大厂风向、GitHub 开源、模型/平台变化、行业转向 |
| `tools-efficiency` | 35% | 工具层 | AI 工具、效率、workflow、SOP、skills、copilot 类使用变化 |
| `agent-builder` | 40% | 基建层 | LLM、agent、orchestration、context、eval、可靠性、自动化工作流 |

### 判断原则

- 不要继续把 AI 卡做成“大厂新闻流”
- 要保留风向，但主供给要更贴近：
  - 工具变化
  - builder 问题
  - 真实工作流变化

---

## 4.3 `business-growth-ops`

### 核心目标

把增长运营从“泛运营讨论”，收成 3 个稳定问题域：

- 投放经济
- 自然增长
- 转化链路

### Topic Packs

| topic_pack | 目标占比 | 作用 | 典型内容 |
|---|---:|---|---|
| `paid-economics` | 35% | 投放层 | ROI、ROAS、Ads、投流、CAC、创意疲劳、投放效率 |
| `organic-discovery` | 30% | 发现层 | SEO、GEO、内容分发、自然流量、搜索变化 |
| `funnel-conversion` | 35% | 转化层 | 独立站、落地页、结账链路、表单、流量转化 |

### 判断原则

- 不要再泛泛写“增长”
- 每张增长卡都应该能落在：
  - 投放
  - 搜索
  - 转化

这 3 个问题域之一

---

## 5. 发布比例目标

下一轮内容供给，按这个方向收：

| scope | 目标存在感 |
|---|---|
| `ai-automation` | 保持强势，但不再一家独大 |
| `ecommerce-sellers` | 明显提升，占比抬高 |
| `business-growth-ops` | 保持稳定 |

对电商内部再加一条硬约束：

- `selection-signals` 必须成为电商卡主供给
- `kill-signals` 只能保留少量，不能继续主导电商 feed

---

## 6. 不做什么

这次明确不做：

- 不新增前端“选品信号”标签
- 不新增新的 source scope
- 不把 3C 升成新 scope
- 不复用主系统 warzones 数据链
- 不把选品卡写成“爆品推荐”

---

## 7. 最终口径

一句话锁定：

**hotpost-mini 继续保持 3 个 source scope，但每个 scope 内部改用 topic-pack 路由；电商主打选品信号，AI 主打风向+工具+builder，增长主打投放/搜索/转化。**

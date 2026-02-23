# 垂直市场洞察 (Vertical Market Insights) 词典需求文档

## 1. 核心纠偏
我们之前的方向偏向于“通用客服/电商体验”（如物流、退款），这只能看到因为购买产生的“售后痛点”。
**您真正需要的市场洞察**，是关于产品本身的“**使用痛点**”和“**场景需求**”。这需要深入每个垂直领域的“行话”。

## 2. 目标
构建一个能够听懂“行话”的领域词典，根据 `competitor_layers.yml` 中的 7 大赛道，精准捕捉用户在**使用产品时**的真实反馈。

## 3. 结构要求 (按赛道分类)
请为您列表中的 7 个核心赛道提供详尽的术语库。格式建议为 YAML 或 JSON。

### 3.1 赛道列表 (基于 competitor_layers.yml)
1.  **Ecommerce_Business** (SaaS, 物流, 金融)
2.  **Family_Parenting** (母婴, 玩具，宠物)
3.  **Food_Coffee_Lifestyle** (咖啡, 厨具, 食品)
4.  **Frugal_Living** (省钱, 穷游, 折扣)
5.  **Home_Lifestyle** (家居, 家具,清洁, 装修)
6.  **Minimal_Outdoor** (户外, 露营, 机能服饰)
7.  **Tools_EDC** (工具, 刀具, 随身装备)

### 3.2 词典结构示例 (以 "Food_Coffee_Lifestyle" 为例)
我们需要捕捉的不仅仅是“好/坏”，而是具体的**技术参数**、**使用场景**和**硬核痛点**。

```yaml
# 垂直领域：咖啡与生活 (Coffee & Lifestyle)
domain: food_coffee_lifestyle
categories:
  # 1. 核心参数/规格 (Specs) - 用户在比较什么？
  specs:
    - ["grind consistency", "grind size", "uniformity"]  # 研磨一致性
    - ["bar pressure", "9 bar", "15 bar", "extraction pressure"] # 压力
    - ["heat up time", "thermal block", "boiler"] # 加热
    - ["retention", "zero retention", "clumping"] # 残粉 (磨豆机痛点)
  
  # 2. 使用场景/动作 (Actions/Scenarios) - 用户在做什么？
  scenarios:
    - ["pulling a shot", "dialing in", "tamping"] # 萃取过程
    - ["steaming milk", "frothing", "latte art"] # 打奶泡
    - ["single dosing", "hopper feeding"] # 进豆方式
    - ["seasoning burrs", "aligning burrs"] # 刀盘校准
  
  # 3. 领域特有痛点 (Domain Pains) - 只有这个圈子懂的槽点
  pain_points:
    - ["channeling", "sputtering", "messy puck"] # 通道效应 (萃取失败)
    - ["fines", "boulders", "muddy cup"] # 细粉过多
    - ["sour", "bitter", "underextracted", "overextracted"] # 风味缺陷
    - ["scale buildup", "descaling"] # 水垢

  # 4. 褒义形容词 (Desirables) - 用户追求什么？
  desirables:
    - ["clarity", "body", "mouthfeel", "sweetness"] # 风味描述
    - ["workflow", "stepless adjustment"] # 操作体验
```

## 4. 各赛道重点关注方向

请按以下指引补充内容：

**1. Ecommerce_Business (SaaS/Biz)**
*   **关注**: API 限制、ROI、转化率、封号 (Account Suspension)、资金冻结 (Holds)、多渠道集成 (Omnichannel)。
*   **黑话**: "Buy Box", "ACoS", "ROAS", "PL (Private Label)", "OA (Online Arbitrage)".

**2. Family_Parenting (Baby)**
*   **关注**: 安全 (Safety), 材质无毒 (Non-toxic), 睡眠训练 (Sleep training), 漏尿 (Blowouts - 尿布痛点), 清洗难度.
*   **黑话**: "Tummy time", "Cluster feeding", "Regression" (睡眠倒退).

**3. Home_Lifestyle (Decor/Cleaning)**
*   **关注**: 吸力 (Suction), 缠绕 (Tangle-free), 续航 (Runtime), 组装 (Assembly), 占地 (Footprint).
*   **黑话**: "Mop robot", "Self-emptying".

**4. Minimal_Outdoor (Camping/Gear)**
*   **关注**: 重量 (Base weight), 防水指数 (Hydrostatic head), 保暖 (R-value), 透气 (Breathability).
*   **黑话**: "Ultralight (UL)", "Glamping", "Thru-hiking", "Condensation" (结露).

**5. Tools_EDC (Knives/Tools)**
*   **关注**: 钢材 (Steel type - S30V, M390), 保持性 (Edge retention), 锁定机制 (Lock type), 扭矩 (Torque).
*   **黑话**: "Blade centering", "Blade play", "Fidget factor", "Hot spots" (握持痛点).

## 5. 总结
请提供一份包含上述 7 个领域的详细词典。一旦有了这份**懂行**的词典，我们的系统就能从“用户在抱怨物流”进化到“用户在抱怨**磨豆机残粉太多**”或“**帐篷结露严重**”。这才是真正的市场洞察。

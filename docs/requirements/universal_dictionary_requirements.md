# 通用属性词典 (Universal Attribute Dictionary) 需求文档

## 1. 目标
构建一个全面、结构化的“属性词典”，用于将用户的反馈（评论和帖子）精准分类到具体的痛点维度（如价格、质量、服务等），从而大幅降低“其他 (Other)”类别的占比。

## 2. 格式要求 (YAML/JSON)
我们需要一个层级分明的 JSON 或 YAML 文件。

```yaml
# 结构示例
aspects:
  quality:
    label: "质量与可靠性 (Quality & Reliability)"
    definition: "涉及物理缺陷、耐用性问题或做工质量的抱怨。"
    subcategories:
      - name: "physical_damage" # 物理损坏
        keywords: ["broken", "crack", "scratch", "dent", "shatter", "snapped"]
      - name: "durability" # 耐用性
        keywords: ["fell apart", "stopped working", "died", "lifespan", "wear and tear"]
      - name: "materials" # 材质手感
        keywords: ["cheap plastic", "flimsy", "thin", "rough", "texture"]
      - name: "defects" # 缺陷/次品
        keywords: ["lemon", "defect", "faulty", "malfunction", "DOA"]
      
  service:
    label: "客户服务 (Customer Service)"
    definition: "与客服支持、退款流程或沟通相关的交互。"
    subcategories:
      - name: "responsiveness" # 响应速度
        keywords: ["ghosted", "no reply", "ignored", "on hold", "wait time"]
      - name: "competence" # 专业能力
        keywords: ["useless", "scripted", "runaround", "chatbot", "robot"]
      - name: "attitude" # 态度
        keywords: ["rude", "unhelpful", "arrogant", "dismissive"]
      - name: "policies" # 政策/退款
        keywords: ["refused refund", "restocking fee", "policy", "fine print"]

  # ... (请补充 Price, Shipping, Function, Installation, UX, Ecosystem, Subscription, Scam 等维度)
```

## 3. 核心维度 (Aspects)
请提供以下 11 个 L2 维度的**穷举式**关键词列表：

1.  **Quality (质量)**: 物理特征、缺陷、耐用性、材质手感 (e.g., "flimsy", "plastic").
2.  **Service (服务)**: 客服交互、退款流程、沟通质量 (e.g., "rude", "ghosted").
3.  **Shipping (物流)**: 配送速度、包裹丢失、包装破损、关税 (e.g., "lost", "crushed").
4.  **Price (价格)**: 成本、性价比、隐藏费用、折扣 (e.g., "overpriced", "ripoff").
5.  **Function (功能)**: 性能、Bug、故障、连接问题、参数虚标 (e.g., "glitch", "lag").
6.  **Installation (安装)**: 设置难度、说明书、组装、支架安装 (e.g., "confusing manual").
7.  **UX (用户体验)**: 易用性、App 界面、学习曲线、人体工学 (e.g., "clunky", "bloated").
8.  **Ecosystem (生态)**: 兼容性、专有配件、封闭系统 (e.g., "proprietary", "walled garden").
9.  **Content (内容)**: (适用于媒体/课程) 音画质量、信息过时、节奏 (e.g., "outdated").
10. **Subscription (订阅)**: 扣费周期、取消难度、自动续费、涨价 (e.g., "auto-renew").
11. **Scam (欺诈)**: 假货、钓鱼、账号被盗、虚假列表 (e.g., "fake", "hacked").

## 4. 细节与颗粒度
对于每个分类，请务必包含不同词性的“**痛点触发词**”：
*   **名词 (Nouns)**: "hinge" (铰链), "bezel" (边框), "agent" (客服), "tracking" (单号).
*   **动词 (Verbs)**: "snapped" (断裂), "ghosted" (失联), "overcharged" (多扣费), "crashed" (崩溃).
*   **形容词 (Adjectives)**: "wobbly" (晃动), "rude" (粗鲁), "exorbitant" (天价), "laggy" (卡顿).
*   **习语/黑话 (Slang)**: "brick" (变砖), "lemon" (次品), "vaporware" (画饼), "dead on arrival" (到手即坏).

## 5. 领域特异性 (可选)
如果某个词有歧义（例如 "frozen" -> 在物流里指冷冻食品，在功能里指死机），请备注其适用语境，或拆分成不同文件（如 `tech_attributes.yml`, `clothing_attributes.yml`）。

## 6. 情感倾向 (关键)
请聚焦通过 **负面 (Negative)** 或 **以痛点为中心** 的词汇。
如果一个词本身是中性的（如 "price"），我们需要它搭配负面修饰语（如 "high price"）才有用。
但有些词天生就是负面的（如 "glitch", "scam", "flimsy"），这些最有价值。

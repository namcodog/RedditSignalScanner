# 人工标注指南

**版本**: v1.0  
**创建日期**: 2025-10-28  
**用途**: 阈值校准与数据质量提升（Spec 007 User Story 5）

---

## 📋 标注目标

为 200 条 Reddit 帖子标注**是否为商业机会**以及**机会强度**，用于校准信号检测阈值，提升 Precision@50 至 ≥ 0.6。

---

## 🎯 标注任务

### 任务 1: 判断是否为商业机会（label 列）

**标注值**:
- `opportunity` - 是商业机会
- `non-opportunity` - 不是商业机会

**判断标准**:

#### ✅ 是商业机会（opportunity）

满足以下**任意一条**即可标注为 `opportunity`：

1. **明确的痛点或需求**
   - 用户抱怨现有工具/服务的不足
   - 用户寻求解决方案或工具推荐
   - 用户表达对某个功能的强烈需求
   
   **示例**:
   - "I'm frustrated with Notion's slow loading time"
   - "Looking for a better alternative to Slack for small teams"
   - "Wish there was a tool that could automate this workflow"

2. **产品讨论或比较**
   - 用户比较不同产品的优劣
   - 用户分享使用某个产品的体验
   - 用户询问产品推荐
   
   **示例**:
   - "Notion vs Obsidian: which one is better for note-taking?"
   - "Just switched from Trello to ClickUp, here's my experience"
   - "What's the best project management tool for remote teams?"

3. **市场趋势或新兴需求**
   - 讨论某个领域的新趋势
   - 提及新兴技术或工作方式
   - 表达对未来产品的期待
   
   **示例**:
   - "AI-powered note-taking is the future"
   - "Remote work tools need better async collaboration features"
   - "Looking forward to more no-code automation tools"

4. **用户行为或使用场景**
   - 分享具体的工作流程或使用场景
   - 描述如何使用某个工具解决问题
   - 提及工具的具体应用场景
   
   **示例**:
   - "Here's how I use Notion to manage my startup"
   - "My workflow for content creation with Airtable"
   - "Using Zapier to automate customer onboarding"

#### ❌ 不是商业机会（non-opportunity）

以下情况标注为 `non-opportunity`：

1. **纯技术讨论**
   - 编程语言、框架、算法讨论
   - 技术实现细节
   - 代码调试问题
   
   **示例**:
   - "How to implement binary search in Python?"
   - "React vs Vue: performance comparison"
   - "Debugging memory leak in Node.js"

2. **娱乐或闲聊**
   - 游戏、电影、音乐讨论
   - 个人生活分享
   - 幽默或梗图
   
   **示例**:
   - "Just finished watching Stranger Things S4"
   - "My cat did the funniest thing today"
   - "Best memes of 2025"

3. **新闻或时事**
   - 政治、经济、社会新闻
   - 突发事件
   - 公共政策讨论
   
   **示例**:
   - "Breaking: New tax policy announced"
   - "Climate change summit results"
   - "Election results discussion"

4. **无明确需求或痛点**
   - 纯粹的信息分享
   - 无具体问题或需求
   - 泛泛而谈
   
   **示例**:
   - "Interesting article about productivity"
   - "Random thoughts on remote work"
   - "Just sharing this cool website"

---

### 任务 2: 判断机会强度（strength 列）

**仅对 `label=opportunity` 的帖子标注强度**

**标注值**:
- `strong` - 强机会
- `medium` - 中等机会
- `weak` - 弱机会

**判断标准**:

#### 🔥 强机会（strong）

满足以下**至少 2 条**：

1. **痛点明确且具体**
   - 清晰描述了具体问题
   - 提供了失败案例或负面体验
   - 表达了强烈的情绪（frustration, annoyed, hate）

2. **需求紧迫**
   - 使用"急需"、"迫切"、"现在就需要"等词汇
   - 表示愿意付费解决问题
   - 提及时间压力或截止日期

3. **市场规模大**
   - 提及团队、公司、组织层面的需求
   - 讨论行业通用问题
   - 高赞（score > 100）或高评论（num_comments > 50）

4. **可行性高**
   - 问题有明确的解决方向
   - 已有类似产品但不完美
   - 技术上可实现

**示例**:
- "Our entire team is struggling with Slack's pricing. We need a cheaper alternative ASAP!" (score: 150, comments: 80)
- "I've tried 5 different project management tools and none of them support our workflow. Willing to pay for a custom solution."

#### ⚡ 中等机会（medium）

满足以下**至少 1 条**：

1. **痛点存在但不紧迫**
   - 提到了问题但没有强烈情绪
   - 可以接受现有解决方案
   - 没有明确的时间压力

2. **需求较为通用**
   - 个人层面的需求
   - 中等赞数（10 < score < 100）
   - 中等评论（10 < num_comments < 50）

3. **有替代方案**
   - 已有多个竞品
   - 可以通过组合工具解决
   - 不是刚需

**示例**:
- "Notion is a bit slow sometimes, but I can live with it" (score: 30, comments: 15)
- "Looking for a better way to organize my notes, any suggestions?"

#### 💡 弱机会（weak）

不满足强机会或中等机会的标准，但仍然是商业机会：

1. **痛点模糊**
   - 问题描述不清晰
   - 没有具体场景
   - 泛泛而谈

2. **需求不明确**
   - 只是随便问问
   - 没有实际行动意愿
   - 低赞低评论（score < 10, num_comments < 10）

3. **市场小众**
   - 非常特定的场景
   - 用户群体很小
   - 难以规模化

**示例**:
- "Anyone else think productivity tools could be better?" (score: 5, comments: 3)
- "Just curious, what do you use for task management?"

---

## 📝 标注流程

### 步骤 1: 打开 CSV 文件

```bash
# 使用 Excel、Google Sheets 或任何 CSV 编辑器打开
open data/annotations/sample_200.csv
```

### 步骤 2: 阅读帖子内容

- 仔细阅读 `title` 和 `body` 列
- 必要时点击 `url` 查看完整帖子和评论
- 注意 `score` 和 `num_comments` 作为参考

### 步骤 3: 标注 label 列

- 根据上述标准判断是否为商业机会
- 填写 `opportunity` 或 `non-opportunity`

### 步骤 4: 标注 strength 列

- **仅对 `label=opportunity` 的帖子标注**
- 根据上述标准判断强度
- 填写 `strong`、`medium` 或 `weak`
- 对于 `non-opportunity` 的帖子，`strength` 列留空

### 步骤 5: 添加备注（可选）

- 在 `notes` 列添加任何有助于理解标注的备注
- 例如：关键词、特殊情况、边界案例等

---

## ⚠️ 注意事项

### 1. 保持一致性

- 使用相同的标准判断所有帖子
- 遇到边界案例时，参考已标注的类似案例
- 不确定时，倾向于保守标注（标为 `non-opportunity` 或 `weak`）

### 2. 避免主观偏见

- 不要因为个人喜好影响判断
- 不要因为熟悉某个产品而偏向标注
- 专注于帖子本身的内容，而非个人观点

### 3. 质量优先

- 宁可慢一点，也要保证标注质量
- 遇到不确定的情况，可以在 `notes` 列标记
- 建议每标注 50 条休息一次，避免疲劳

### 4. 边界案例处理

**案例 1**: 技术讨论中提到工具痛点
- **判断**: 如果痛点明确且与产品相关 → `opportunity`
- **示例**: "Using React for this project, but the state management is a pain" → `opportunity` (medium)

**案例 2**: 娱乐内容中提到产品
- **判断**: 如果只是顺带提及，无明确需求 → `non-opportunity`
- **示例**: "Watching Netflix while working on my Notion setup" → `non-opportunity`

**案例 3**: 新闻中提到市场趋势
- **判断**: 如果讨论了具体需求或痛点 → `opportunity`
- **示例**: "Report: 80% of remote workers struggle with async communication" → `opportunity` (strong)

---

## 📊 预期分布

根据经验，标注结果的预期分布：

- **opportunity**: 30-40%
  - strong: 5-10%
  - medium: 15-20%
  - weak: 10-15%
- **non-opportunity**: 60-70%

**如果你的标注结果与此差异很大，请重新检查标注标准。**

---

## ✅ 质量检查

标注完成后，请自查：

1. **完整性**: 所有 200 条都已标注 `label` 列
2. **一致性**: `label=opportunity` 的帖子都有 `strength` 标注
3. **合理性**: 分布符合预期（30-40% opportunity）
4. **准确性**: 随机抽查 10 条，确认标注符合标准

---

## 🎯 标注示例

### 示例 1: Strong Opportunity

**Title**: "Our startup is drowning in Slack messages. Need a better async tool!"  
**Body**: "We're a 20-person remote team and Slack is killing our productivity. Too many notifications, hard to find important info, and the pricing is insane. We've tried Twist and Discord but they're not much better. Willing to pay $50/user/month for a real solution."  
**Score**: 180  
**Comments**: 95  

**标注**:
- `label`: `opportunity`
- `strength`: `strong`
- `notes`: "Clear pain point, urgent need, willing to pay, large team"

### 示例 2: Medium Opportunity

**Title**: "What's a good alternative to Notion for personal use?"  
**Body**: "I like Notion but it's a bit slow on my old laptop. Looking for something lighter and faster. Free or cheap would be nice."  
**Score**: 45  
**Comments**: 22  

**标注**:
- `label`: `opportunity`
- `strength`: `medium`
- `notes`: "Personal use, not urgent, price-sensitive"

### 示例 3: Weak Opportunity

**Title**: "Productivity tools these days..."  
**Body**: "Anyone else think there are too many productivity tools? Sometimes I wonder if we even need them."  
**Score**: 8  
**Comments**: 5  

**标注**:
- `label`: `opportunity`
- `strength`: `weak`
- `notes`: "Vague, no specific need, low engagement"

### 示例 4: Non-Opportunity

**Title**: "Just watched a great documentary on Netflix"  
**Body**: "Highly recommend 'The Social Dilemma'. Really makes you think about tech addiction."  
**Score**: 120  
**Comments**: 60  

**标注**:
- `label`: `non-opportunity`
- `strength`: (留空)
- `notes`: "Entertainment content, no business relevance"

---

## 📞 联系方式

如有任何疑问，请联系项目负责人。

**预计标注时间**: 6 小时（平均 1.8 分钟/条）

**祝标注顺利！** 🎉


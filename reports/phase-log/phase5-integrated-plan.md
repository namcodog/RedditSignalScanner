# Phase 5: 数据与算法双轨优化 - 整合实施计划

生成时间：2025-10-16 21:00  
状态：✅ 冷热分层完成，开始整合实施

---

## 📋 整合概述

**已完成基础设施：**
- ✅ 冷热分层架构（posts_raw + posts_hot + posts_latest）
- ✅ 增量抓取服务（IncrementalCrawler）
- ✅ 水位线机制（last_seen_post_id, last_seen_created_at）
- ✅ 双写逻辑（先冷库，再热缓存）
- ✅ 部分数据（26/102 社区，3,075 条帖子）

**整合目标：**
将冷热分层架构与 plan.md 的 15 步计划整合，实现：
1. 样本扩量：2-5 倍提升（目标 ≥1500 条/分析）
2. 规则优化：Precision@50 ≥0.6
3. 在线评测：仪表盘 + 红线策略

---

## 🎯 整合后的实施计划

### 阶段 1：数据基础设施完善（T+0~3 天）

#### Step 1.1：完成剩余社区抓取（T+0~0.5 天）✅ 部分完成

**当前状态：**
- ✅ 已抓取：26/102 社区，3,075 条帖子
- ⏳ 待抓取：76 个社区

**行动：**
1. 完成剩余 76 个社区的首次抓取
2. 验证冷热分层数据一致性
3. 记录抓取失败的社区（空结果/API 错误）

**预期结果：**
- 冷库：~8,000 条帖子（100 社区 × 80 条平均）
- 热缓存：~8,000 条帖子
- 失败社区：记录到 `community_cache.empty_hit`

---

#### Step 1.2：基线监测与数据标签（T+0.5~1 天）

**对应 plan.md Step 1**

**数据库改造：**
```sql
-- 扩展 community_cache 表
ALTER TABLE community_cache ADD COLUMN IF NOT EXISTS empty_hit INTEGER DEFAULT 0;
ALTER TABLE community_cache ADD COLUMN IF NOT EXISTS success_hit INTEGER DEFAULT 0;
ALTER TABLE community_cache ADD COLUMN IF NOT EXISTS failure_hit INTEGER DEFAULT 0;
ALTER TABLE community_cache ADD COLUMN IF NOT EXISTS avg_valid_posts NUMERIC(5,2) DEFAULT 0;
ALTER TABLE community_cache ADD COLUMN IF NOT EXISTS quality_tier VARCHAR(20) DEFAULT 'normal';

-- 创建监控统计表
CREATE TABLE IF NOT EXISTS crawl_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    metric_hour INTEGER,
    cache_hit_rate NUMERIC(5,2),
    valid_posts_24h INTEGER,
    valid_posts_72h INTEGER,
    empty_results INTEGER,
    failed_requests INTEGER,
    total_requests INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**埋点改造：**
- 修改 `IncrementalCrawler` 记录：
  - 成功抓取（有帖子）
  - 空结果（0 条帖子）
  - 失败（API 错误）
- 更新 `community_cache` 的统计字段

**预期结果：**
- ✅ 每小时记录缓存命中率
- ✅ 每日记录有效帖子数（24h/72h）
- ✅ 社区级别的质量分级

---

#### Step 1.3：社区池扩容 & 黑名单（T+1~2 天）

**对应 plan.md Step 4**

**社区扩容：**
1. 从现有 102 个社区中筛选 Top 100（按 `avg_valid_posts` 排序）
2. 补充 200 个新社区（按类目分布）
3. 添加类目标签（tech/business/lifestyle/finance 等）
4. 限制同类目 ≤5 个

**黑名单配置：**
```yaml
# config/community_blacklist.yaml
blacklist:
  - name: "r/FreeKarma4U"
    reason: "spam_farm"
    action: "exclude"
  
  - name: "r/giveaways"
    reason: "low_quality"
    action: "downrank"

downrank_keywords:
  - "giveaway"
  - "for fun"
  - "just sharing"
```

**数据库改造：**
```sql
-- 扩展 community_pool 表
ALTER TABLE community_pool ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE community_pool ADD COLUMN IF NOT EXISTS is_blacklisted BOOLEAN DEFAULT FALSE;
ALTER TABLE community_pool ADD COLUMN IF NOT EXISTS blacklist_reason VARCHAR(100);
```

**预期结果：**
- ✅ 社区池扩容到 300 个
- ✅ 黑名单配置文件
- ✅ 类目标签完善

---

#### Step 1.4：刷新调度改造（T+2~3 天）

**对应 plan.md Step 2**

**社区分级策略：**
- **Tier 1（Top 20）**：每 2 小时刷新
- **Tier 2（次优 40）**：每 6 小时刷新
- **Tier 3（长尾）**：每 24 小时刷新

**Celery Beat 配置：**
```python
celery_app.conf.beat_schedule = {
    # Tier 1: 每 2 小时
    "crawl-tier1": {
        "task": "tasks.crawler.crawl_tier",
        "schedule": crontab(minute="0", hour="*/2"),
        "args": ("tier1",),
    },
    # Tier 2: 每 6 小时
    "crawl-tier2": {
        "task": "tasks.crawler.crawl_tier",
        "schedule": crontab(minute="0", hour="*/6"),
        "args": ("tier2",),
    },
    # Tier 3: 每 24 小时
    "crawl-tier3": {
        "task": "tasks.crawler.crawl_tier",
        "schedule": crontab(minute="0", hour="0"),
        "args": ("tier3",),
    },
}
```

**精准补抓任务：**
```python
async def补抓低质量社区():
    """
    条件：last_crawled_at > 8h 且 avg_valid_posts < 阈值
    """
    query = """
    SELECT community_name 
    FROM community_cache
    WHERE last_crawled_at < NOW() - INTERVAL '8 hours'
      AND avg_valid_posts < 50
      AND quality_tier != 'blacklist'
    """
```

**预期结果：**
- ✅ 分级调度策略
- ✅ 精准补抓任务
- ✅ 失败回写 `empty_hit`

---

### 阶段 2：分析引擎改造（T+3~9 天）

#### Step 2.1：样本下限与补抓兜底（T+3~4 天）

**对应 plan.md Step 3**

**分析前置检查：**
```python
async def check_sample_size(product_description: str) -> bool:
    """
    检查缓存样本量是否 ≥1500
    不足则触发关键词+时间窗抓取
    """
    # 1. 从热缓存读取
    hot_count = await count_hot_cache()
    
    # 2. 从冷库补读（最近 30 天）
    cold_count = await count_cold_storage(days=30)
    
    total = hot_count + cold_count
    
    if total < 1500:
        # 触发补抓任务
        await trigger_keyword_crawl(product_description)
        return False
    
    return True
```

**关键词抓取任务：**
```python
async def keyword_crawl(keywords: List[str], time_window: str):
    """
    使用 Reddit Search API 按关键词抓取
    标记来源类型：cache/search
    """
    for keyword in keywords:
        posts = await reddit_client.search(
            query=keyword,
            time_filter=time_window,
            limit=100,
        )
        
        # 写入冷库，标记来源
        for post in posts:
            await upsert_post(post, source_type="search")
```

**预期结果：**
- ✅ 分析前样本量检查
- ✅ 关键词补抓任务
- ✅ 来源类型标记（cache/search）

---

#### Step 2.2：规则关键词与否定列表（T+4~5 天）

**对应 plan.md Step 5**

**配置文件：**
```yaml
# config/scoring_rules.yaml
positive_keywords:
  - keyword: "need"
    weight: 0.3
  - keyword: "urgent"
    weight: 0.4
  - keyword: "looking for"
    weight: 0.3

negative_keywords:
  - keyword: "giveaway"
    weight: -0.5
  - keyword: "for fun"
    weight: -0.3
  - keyword: "just sharing"
    weight: -0.2

semantic_negation:
  - pattern: "not interested"
    weight: -0.4
  - pattern: "don't need"
    weight: -0.5
```

**评分器改造：**
```python
class OpportunityScorer:
    def __init__(self, config_path: str):
        self.config = load_yaml(config_path)
        self.positive_kw = self.config['positive_keywords']
        self.negative_kw = self.config['negative_keywords']
    
    def score_post(self, post: RedditPost) -> float:
        score = 0.0
        
        # 正例关键词
        for kw in self.positive_kw:
            if kw['keyword'] in post.text.lower():
                score += kw['weight']
        
        # 负例关键词（对冲）
        for kw in self.negative_kw:
            if kw['keyword'] in post.text.lower():
                score += kw['weight']  # 负权重
        
        return max(0, score)  # 不低于 0
```

**预期结果：**
- ✅ 正负关键词配置
- ✅ 语义否定检测
- ✅ 配置热更新支持

---

#### Step 2.3：上下文窗口与噪声剔除（T+5~6 天）

**对应 plan.md Step 6**

**文本预处理：**
```python
def clean_text(text: str) -> str:
    """
    去除 URL、代码块、引用块
    """
    # 去除 URL
    text = re.sub(r'https?://\S+', '', text)
    
    # 去除代码块
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # 去除引用块
    text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)
    
    return text.strip()
```

**句级评分 + 上下文窗口：**
```python
def score_with_context(sentences: List[str], index: int) -> float:
    """
    取当前句 + 前后各 1 句窗口
    """
    window_start = max(0, index - 1)
    window_end = min(len(sentences), index + 2)
    
    context = ' '.join(sentences[window_start:window_end])
    
    return score_text(context)
```

**预期结果：**
- ✅ 文本清洗函数
- ✅ 句级评分
- ✅ 上下文窗口（±1 句）

---

#### Step 2.4：模板加成与反模板（T+6~7 天）

**对应 plan.md Step 7**

**正向模板：**
```yaml
# config/scoring_templates.yaml
positive_templates:
  - pattern: '\$[0-9,]+'
    name: "money_amount"
    weight: 0.3
  
  - pattern: 'in \d+ (weeks|months|days)'
    name: "time_urgency"
    weight: 0.3
  
  - pattern: '\d+ (users|customers|people)'
    name: "scale"
    weight: 0.2
```

**反模板：**
```yaml
negative_templates:
  - pattern: 'hiring|job posting|we are looking for'
    name: "job_posting"
    weight: -1.0  # 直接置零
  
  - pattern: 'giveaway|contest|raffle'
    name: "giveaway"
    weight: -0.8
  
  - pattern: 'check out my|shameless plug'
    name: "self_promotion"
    weight: -0.6
```

**预期结果：**
- ✅ 正向模板正则
- ✅ 反模板降权/置零
- ✅ 模板配置文件

---

#### Step 2.5：去重与主题聚合（T+7~9 天）

**对应 plan.md Step 9**

**MinHash 去重：**
```python
from datasketch import MinHash, MinHashLSH

def deduplicate_posts(posts: List[RedditPost]) -> List[RedditPost]:
    """
    使用 MinHash + LSH 去重
    相似度 >0.85 的帖子聚合
    """
    lsh = MinHashLSH(threshold=0.85, num_perm=128)
    
    unique_posts = []
    duplicates = {}
    
    for post in posts:
        # 计算 MinHash
        m = MinHash(num_perm=128)
        for word in post.title.split():
            m.update(word.encode('utf8'))
        
        # 查询相似帖子
        result = lsh.query(m)
        
        if not result:
            # 新帖子
            lsh.insert(post.id, m)
            unique_posts.append(post)
            duplicates[post.id] = []
        else:
            # 重复帖子
            master_id = result[0]
            duplicates[master_id].append(post.id)
    
    return unique_posts, duplicates
```

**证据计数：**
```python
# 在分析结果中记录重复项
analysis_result = {
    "post_id": master_post.id,
    "score": 0.85,
    "evidence_count": len(duplicates[master_post.id]) + 1,
    "duplicate_ids": duplicates[master_post.id],
}
```

**预期结果：**
- ✅ MinHash/Jaccard 去重
- ✅ 主题聚合（相似度 >0.85）
- ✅ 证据计数记录

---

### 阶段 3：评测与优化（T+9~18 天）

#### Step 3.1：抽样标注与阈值校准（T+9~11 天）

**对应 plan.md Step 8**

**抽样标注流程：**
1. 从冷库随机抽样 500 条帖子
2. 人工标注：机会/非机会、强/中/弱
3. 保存到 `data/labeled_samples.csv`

**阈值网格搜索：**
```python
def grid_search_threshold(labeled_data: pd.DataFrame):
    """
    网格搜索最优阈值
    优化 Precision@50 和 F1
    """
    thresholds = np.arange(0.3, 0.9, 0.05)
    
    best_threshold = None
    best_precision = 0
    
    for threshold in thresholds:
        predictions = [1 if score >= threshold else 0 
                      for score in labeled_data['score']]
        
        precision = precision_score(labeled_data['label'], predictions)
        
        if precision > best_precision:
            best_precision = precision
            best_threshold = threshold
    
    return best_threshold, best_precision
```

**配置更新：**
```yaml
# config/scoring_config.yaml
threshold:
  opportunity: 0.65  # 网格搜索结果
  strong: 0.80
  medium: 0.60
  weak: 0.40

calibration:
  date: "2025-10-16"
  precision_at_50: 0.72
  f1_score: 0.68
  sample_size: 500
```

**预期结果：**
- ✅ 500 条标注样本
- ✅ 最优阈值（Precision@50 ≥0.6）
- ✅ 阈值配置文件

---

#### Step 3.2：仪表盘与红线策略（T+11~15 天）

**对应 plan.md Step 12**

**每日跑分表：**
```python
# 生成每日报告
daily_metrics = {
    "date": "2025-10-16",
    "cache_hit_rate": 0.68,
    "valid_posts_24h": 1850,
    "duplicate_rate": 0.12,
    "empty_results": 15,
    "precision_at_50": 0.72,
    "f1_score": 0.68,
}

# 写入 CSV
pd.DataFrame([daily_metrics]).to_csv(
    f"reports/daily_metrics/{date}.csv",
    index=False
)
```

**红线触发逻辑：**
```python
def check_red_lines(metrics: dict) -> dict:
    """
    检查红线触发条件
    """
    actions = []
    
    # 红线 1：有效帖子 <1500
    if metrics['valid_posts_24h'] < 1500:
        actions.append({
            "trigger": "low_sample_size",
            "action": "conservative_mode",
            "params": {"top_communities": 10, "enable_补抓": True}
        })
    
    # 红线 2：缓存命中率 <60%
    if metrics['cache_hit_rate'] < 0.60:
        actions.append({
            "trigger": "low_cache_hit",
            "action": "increase_crawl_frequency",
        })
    
    # 红线 3：重复率 >20%
    if metrics['duplicate_rate'] > 0.20:
        actions.append({
            "trigger": "high_duplicate",
            "action": "improve_dedup",
        })
    
    # 红线 4：Precision@50 <0.6
    if metrics['precision_at_50'] < 0.60:
        actions.append({
            "trigger": "low_precision",
            "action": "increase_threshold",
        })
    
    return actions
```

**预期结果：**
- ✅ 每日跑分表（CSV）
- ✅ 红线触发逻辑
- ✅ 自动降级策略

---

#### Step 3.3：报告行动位强化（T+15~18 天）

**对应 plan.md Step 13**

**报告模版改造：**
```python
class OpportunityReport:
    def __init__(self):
        self.problem_definition = ""
        self.evidence_chain = []  # 2-3 条证据
        self.suggested_actions = []
        self.confidence = 0.0
        self.urgency = 0.0
        self.product_fit = 0.0
        self.priority = 0.0  # confidence × urgency × product_fit
    
    def calculate_priority(self):
        self.priority = (
            self.confidence * 0.4 +
            self.urgency * 0.3 +
            self.product_fit * 0.3
        )
```

**行动位示例：**
```markdown
## 机会 #1: AI 笔记应用需求

**问题定义：**
用户在 r/productivity 中频繁提及需要自动总结会议笔记的工具。

**证据链：**
1. "I need an AI tool that can summarize my meeting notes" (r/productivity, 2025-10-15, 85 upvotes)
2. "Looking for automatic note-taking app" (r/Entrepreneur, 2025-10-14, 120 upvotes)
3. 相似需求出现 12 次（去重后）

**建议动作：**
1. 在 r/productivity 发布产品介绍帖
2. 准备话术："我们的 AI 笔记应用可以自动总结会议..."
3. 联系 Top 3 高赞帖子作者，提供免费试用

**置信度：** 0.85  
**紧迫性：** 0.70  
**产品适配度：** 0.90  
**优先级：** 0.82 ⭐⭐⭐⭐⭐
```

**预期结果：**
- ✅ 报告模版包含行动位
- ✅ 优先级计算公式
- ✅ 可点击链接 + 话术草稿

---

### 阶段 4：迭代与延伸（T+18~30 天）

#### Step 4.1：两周迭代总结（T+18~21 天）

**对应 plan.md Step 14**

**复盘内容：**
1. 社区扩容效果（300 个社区，样本量提升倍数）
2. 规则改造效果（Precision@50, F1）
3. 阈值调整效果（最优阈值，校准流程）
4. 红线触发次数与降级效果

**写入 phase-log：**
```markdown
# Phase 5 阶段总结

## 数据扩容
- 社区池：102 → 300
- 样本量：3,075 → 15,000+（5 倍提升）
- 缓存命中率：68%

## 规则优化
- Precision@50：0.72（目标 ≥0.6）
- F1 Score：0.68
- 最优阈值：0.65

## 红线触发
- 低样本量：3 次 → 触发补抓
- 低缓存命中：1 次 → 提升抓取频率
- 高重复率：0 次
- 低精度：0 次
```

---

#### Step 4.2：一月内延伸（T+21~30 天）

**对应 plan.md Step 15**

**轻量 NER：**
```python
# 使用 spaCy 或词典+正则
import spacy

nlp = spacy.load("en_core_web_sm")

def extract_entities(text: str) -> dict:
    doc = nlp(text)
    
    entities = {
        "products": [],
        "features": [],
        "audiences": [],
        "industries": [],
    }
    
    for ent in doc.ents:
        if ent.label_ == "PRODUCT":
            entities["products"].append(ent.text)
        elif ent.label_ == "ORG":
            entities["industries"].append(ent.text)
    
    return entities
```

**趋势分析：**
```python
def analyze_trends(days: int = 30):
    """
    输出主题趋势曲线（7/14/30 天）
    """
    query = """
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as count
    FROM posts_raw
    WHERE created_at >= NOW() - INTERVAL '{days} days'
    GROUP BY DATE(created_at)
    ORDER BY date
    """
    
    # 绘制趋势图
    plt.plot(df['date'], df['count'])
    plt.title(f"Post Volume Trend ({days} days)")
    plt.savefig(f"reports/trends/trend_{days}d.png")
```

**证据图谱：**
```python
class EvidenceGraph:
    def __init__(self):
        self.nodes = []  # 机会节点
        self.edges = []  # 证据链接
    
    def add_opportunity(self, opp_id: str, evidence_ids: List[str]):
        self.nodes.append({"id": opp_id, "type": "opportunity"})
        
        for evi_id in evidence_ids:
            self.nodes.append({"id": evi_id, "type": "evidence"})
            self.edges.append({"from": opp_id, "to": evi_id})
    
    def export_json(self):
        return {
            "nodes": self.nodes,
            "edges": self.edges,
        }
```

---

## 📊 成功标准（整合版）

### 数据层面
- ✅ 可用帖子样本量：3,075 → 15,000+（5 倍提升）
- ✅ 冷库数据：支持 30/90 天历史回溯
- ✅ 热缓存命中率：≥60%
- ✅ 社区池：102 → 300

### 算法层面
- ✅ Precision@50：≥0.6
- ✅ F1 Score：≥0.6
- ✅ 去重率：<20%
- ✅ 阈值校准：每周固化流程

### 系统层面
- ✅ 分析引擎：5 分钟内完成
- ✅ 红线策略：自动降级
- ✅ 仪表盘：每日跑分表
- ✅ 报告行动位：问题定义 + 证据链 + 建议动作 + 优先级

---

## 🚀 下一步行动

### 立即执行（今天）
1. ✅ 完成剩余 76 个社区的抓取
2. ✅ 验证冷热分层数据一致性
3. ✅ 记录抓取失败的社区

### 本周完成（T+0~7 天）
1. 基线监测与数据标签
2. 社区池扩容 & 黑名单
3. 刷新调度改造
4. 样本下限与补抓兜底
5. 规则关键词与否定列表

### 下周完成（T+7~14 天）
1. 上下文窗口与噪声剔除
2. 模板加成与反模板
3. 去重与主题聚合
4. 抽样标注与阈值校准

### 第三周完成（T+14~21 天）
1. 仪表盘与红线策略
2. 报告行动位强化
3. 两周迭代总结

---

**🎉 整合计划已就绪！现在开始执行第一步：完成剩余社区抓取！**


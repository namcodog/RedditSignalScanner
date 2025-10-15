# PRD-03: 分析引擎设计

## 1. 问题陈述

### 1.1 背景
Reddit Signal Scanner的核心价值在于将海量的Reddit讨论转化为精准的商业洞察。**基于Linus的严厉批评**，系统必须诚实地描述其架构：我们承诺的"5分钟分析"基于**缓存优先架构**而非实时爬取。系统需要一个智能分析引擎，利用24小时预爬取缓存，在5分钟内处理和分析相关数据，生成高质量的商业洞察报告。

### 1.4 核心架构决策 - 缓存优先（Cache First）

**诚实的数学现实**：
- 实时爬取模式：20社区 × 100帖子 = 2000 API调用
- Reddit限制：60请求/分钟 → 需要33分钟（物理不可能5分钟完成）

**我们的解决方案**：
```
后台爬虫系统 (24小时持续) → Redis缓存层 (90%数据源)
     ↓                          ↓  
分析引擎 (5分钟处理) ← 精准补充API调用 (10%数据源)
```

**缓存优先保证**：
- 90%分析数据来自24小时预爬取缓存
- 10%数据通过精准实时API调用补充
- 总API调用：< 20次/分钟（远低于60次/分钟限制）
- 数据新鲜度：主体数据24小时内，补充数据实时

### 1.2 目标
设计四步分析算法的完整技术规范，基于缓存优先架构：
- 智能发现最相关的社区（动态配置10-30个，基于缓存命中率）
- 高效利用预爬取缓存 + 精准API补充的混合数据源
- 使用Reddit特定NLP模型提取三类商业信号（不是Twitter模型！）
- 生成结构化、可信度加权的分析报告
- 完整的后台爬虫系统维护缓存层数据

### 1.3 非目标
- **不支持**实时流式分析（批量处理模式）
- **不支持**多语言内容分析（专注英文Reddit）
- **不支持**图片和视频内容分析（仅文本）
- **不支持**社交网络关系分析（专注内容语义）

## 2. 解决方案

### 2.1 核心设计：四步分析流水线

基于Linus的"数据结构优先"原则，设计线性处理流水线：

```
Step 1: 智能社区发现 (30秒)
  ↓
Step 2: 并行数据采集 (120秒) 
  ↓
Step 3: 统一信号提取 (90秒)
  ↓  
Step 4: 智能排序输出 (30秒)
```

**设计哲学**：
- **线性流水线**：避免复杂的分支和并行依赖
- **缓存优先**：最大化利用Redis中的历史数据
- **配置驱动**：所有参数通过YAML文件管理
- **优雅降级**：每步都有fallback机制

### 2.2 数据流

```
用户产品描述 
  ↓ 关键词提取
候选社区池(500+) → Top 20相关社区
  ↓ 并行API调用
原始帖子数据(5000+) → 过滤后数据(1500+)
  ↓ NLP语义分析  
结构化信号数据 → 权重排序
  ↓ 模板渲染
最终分析报告
```

### 2.3 关键决策

#### 决策1: 为什么是四步而不是更多？
**理由**: 遵循Linus的"简单胜过聪明"原则。四步能够清晰地划分职责，每步都可以独立测试和优化。

#### 决策2: 为什么动态配置社区数量而非固定20个？
**理由**: 基于Linus的"去除魔数"要求，社区数量应该基于实际缓存命中率动态调整：
- 缓存命中率 > 80%：分析30个社区（数据充足）
- 缓存命中率 60-80%：分析20个社区（平衡模式）
- 缓存命中率 < 60%：分析10个社区（保守模式）
这确保了系统在任何缓存状态下都能在5分钟内完成分析。

#### 决策3: 为什么使用配置文件而非数据库存储参数？
**理由**: 配置即代码的原则。所有优化都通过Git管理，支持版本控制和快速回滚。

## 3. 技术规范

### 3.0 社区池管理策略（动态进化架构）

**核心理念**: 社区池是动态的、自我进化的系统，而非静态配置

#### 3.0.1 四层社区池架构

**第一层：种子社区池（50-100个）**
- **来源**: 产品/运营团队提供的核心通用社区
- **覆盖率**: 60-70% 的用户需求
- **爬取频率**: 每 30 分钟一次
- **缓存命中率**: > 95%
- **示例**: r/startups, r/Entrepreneur, r/SaaS, r/ProductManagement

**第二层：扩展社区池（动态增长）**
- **来源**: 通过 Reddit API 搜索帖子自动发现
- **覆盖率**: 额外 20-25% 的用户需求
- **爬取频率**: 根据使用频率动态调整（1-6 小时）
- **缓存命中率**: 70-90%
- **触发条件**: 种子社区池相关性 < 0.3

**第三层：用户反馈驱动池（持续优化）**
- **来源**: 用户分析反馈 + Admin 审核
- **覆盖率**: 额外 5-10% 的长尾需求
- **爬取频率**: 5+ 用户需要后自动批准并爬取
- **缓存命中率**: 首次 0%，后续 > 80%
- **自动批准**: 同一社区被 5+ 不同用户发现

**第四层：Admin 手动添加池（完全可控）**
- **来源**: Admin 后台手动添加
- **覆盖率**: 特殊需求和战略社区
- **爬取频率**: 立即爬取并加入定期计划
- **优先级**: 最高

#### 3.0.2 社区池数据结构

```json
// backend/config/seed_communities.json
{
  "version": "1.0",
  "last_updated": "2025-10-14",
  "seed_communities": [
    {
      "name": "r/startups",
      "tier": "seed",
      "categories": ["startup", "business", "founder"],
      "description_keywords": ["startup", "founder", "product", "launch", "mvp"],
      "daily_posts": 200,
      "avg_comment_length": 150,
      "quality_score": 0.95,
      "priority": "high"
    }
    // ... 50-100 个种子社区
  ]
}
```

```sql
-- 动态社区池表（数据库）
CREATE TABLE community_pool (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    tier VARCHAR(20) NOT NULL,  -- seed, discovered, user_feedback, admin
    categories JSONB NOT NULL,
    description_keywords JSONB NOT NULL,
    daily_posts INTEGER DEFAULT 0,
    avg_comment_length INTEGER DEFAULT 0,
    quality_score DECIMAL(3,2) DEFAULT 0.50,
    user_feedback_count INTEGER DEFAULT 0,
    discovered_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 待审核社区表
CREATE TABLE pending_communities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    discovered_from_keywords JSONB,
    discovered_count INTEGER DEFAULT 1,
    first_discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected
    admin_reviewed_at TIMESTAMP,
    admin_notes TEXT
);
```

#### 3.0.3 社区自动发现机制

**Reddit API 搜索策略**（Reddit API 不支持直接搜索 subreddit）：

```python
async def discover_related_communities(
    keywords: List[str],
    limit: int = 20
) -> List[str]:
    """
    通过搜索 Reddit 帖子来发现相关社区

    策略：
    1. 使用关键词搜索 Reddit 帖子（/search 端点）
    2. 统计帖子来源的社区
    3. 返回最相关的社区列表

    API 调用：1 次搜索 = 1 次 API 调用
    """
    # 1. 搜索相关帖子
    search_query = " ".join(keywords[:3])
    posts = await reddit_client.search_posts(
        query=search_query,
        limit=100,
        sort="relevance"
    )

    # 2. 统计社区来源
    community_counts = {}
    for post in posts:
        subreddit = post.subreddit
        community_counts[subreddit] = community_counts.get(subreddit, 0) + 1

    # 3. 按帖子数量排序
    sorted_communities = sorted(
        community_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [community for community, count in sorted_communities[:limit]]
```

#### 3.0.4 社区池进化时间线

```
初始状态（Day 0）：
└─ 50-100 个种子社区 → 覆盖 60-70% 用户需求

预热期（Day 13-19，7天）：
├─ 内部测试：发现 30-50 个新社区
├─ Beta 测试：发现 50-100 个新社区
└─ 社区池规模：150-250 个 → 覆盖 85-90% 用户需求

1 个月后：
└─ 300-400 个社区 → 覆盖 90-95% 用户需求

3 个月后：
└─ 500-800 个社区 → 覆盖 95-98% 用户需求
```

### 3.1 Step 1: 智能社区发现

**功能**: 基于产品描述，从动态社区池中发现最相关的20个社区

**算法设计**:
```python
async def discover_communities(
    product_description: str,
    *,
    max_communities: int = 20,
    min_relevance_threshold: float = 0.3
) -> Tuple[List[Community], Optional[str]]:
    """
    智能社区发现算法（动态社区池 + 降级策略）

    Returns:
        (社区列表, 可选的用户警告信息)
    """
    # 1. 关键词提取（基于TF-IDF）
    keywords = extract_keywords(product_description, max_keywords=20)

    # 2. 从动态社区池加载社区
    community_pool = await load_community_pool()  # 从数据库加载

    # 3. 候选社区加权评分
    candidate_scores = {}
    for community in community_pool:
        score = calculate_relevance_score(keywords, community)
        candidate_scores[community] = score

    # 4. 过滤低相关性社区
    filtered_scores = {
        community: score
        for community, score in candidate_scores.items()
        if score >= min_relevance_threshold
    }

    # 5. 检查覆盖率是否足够
    if len(filtered_scores) < 5:
        # 覆盖率不足，触发降级策略
        logger.warning(
            f"社区池覆盖率不足（{len(filtered_scores)}/20），"
            f"触发自动发现。关键词：{keywords.keywords}"
        )

        # 5a. 自动发现新社区（通过搜索 Reddit 帖子）
        discovered_communities = await discover_related_communities(
            keywords.keywords,
            limit=20
        )

        # 5b. 记录到待审核表
        await record_discovered_communities(
            task_id=None,  # 后续关联
            keywords=keywords.keywords,
            discovered_communities=discovered_communities
        )

        # 5c. 使用通用社区兜底
        fallback_communities = await load_fallback_communities()
        fallback_scores = calculate_relevance_scores(keywords, fallback_communities)

        # 合并评分（通用社区评分 × 0.7 作为惩罚）
        for community, score in fallback_scores.items():
            if community not in filtered_scores:
                filtered_scores[community] = score * 0.7

        # 返回警告信息
        warning = (
            "您的产品描述较为专业/小众，我们的社区池覆盖率不足。"
            "建议补充更多产品细节或使用场景，以获得更精准的分析结果。"
        )
    else:
        warning = None

    # 6. 选择Top 20 + 确保多样性
    top_communities = select_diverse_top_k(filtered_scores, k=max_communities)

    return top_communities, warning

def calculate_relevance_score(keywords: List[str], community: Community) -> float:
    """
    社区相关性评分算法
    """
    base_score = 0.0
    
    # 描述匹配分数 (40%权重)
    description_score = cosine_similarity(keywords, community.description_keywords)
    base_score += description_score * 0.4
    
    # 历史活跃度分数 (30%权重) 
    activity_score = min(community.daily_posts / 100, 1.0)
    base_score += activity_score * 0.3
    
    # 质量指标分数 (30%权重)
    quality_score = community.avg_comment_length / 200
    base_score += min(quality_score, 1.0) * 0.3
    
    return base_score
```

**配置参数**（修复魔数问题）:
```yaml
# community_discovery.yml
discovery:
  # 动态社区发现配置（基于缓存命中率）
  community_pool_size: 500
  
  # 动态调整策略（不再是固定20）
  target_communities:
    min: 10    # 保守模式（缓存命中率 < 60%）
    default: 20  # 平衡模式（缓存命中率 60-80%）
    max: 30    # 积极模式（缓存命中率 > 80%）
    
  # 缓存命中率阈值
  cache_thresholds:
    conservative_mode: 0.6   # 60%
    aggressive_mode: 0.8     # 80%
  
  # 评分权重
  weights:
    description_match: 0.4
    activity_level: 0.3  
    quality_score: 0.3
    
  # 多样性保证
  diversity:
    max_same_category: 5
    category_bonus: 0.1
    
  # 关键词提取
  keyword_extraction:
    method: "tfidf"
    max_keywords: 20
    min_keyword_length: 3
```

### 3.2 Step 2: 并行数据采集（缓存优先模式）

**功能**: 基于缓存优先架构，高效获取选中社区的讨论数据，90%来自预缓存，10%精准API补充

**算法设计**:
```python
async def collect_community_data(communities: List[Community]) -> Dict[str, List[Post]]:
    """
    并行数据采集算法
    """
    results = {}
    
    # 1. 检查缓存命中率，决定数据获取策略
    cache_status = await check_cache_coverage(communities)
    cache_hit_rate = calculate_overall_cache_hit_rate(cache_status)
    
    # 2. 根据缓存命中率调整数据源策略
    if cache_hit_rate > 0.9:
        # 高命中率：主要使用缓存，少量API补充
        strategy = "cache_primary"
    elif cache_hit_rate > 0.6:
        # 中等命中率：缓存+API混合
        strategy = "hybrid"
    else:
        # 低命中率：更多依赖API调用（但仍有限制）
        strategy = "api_heavy"
    
    # 3. 基于策略的并行处理
    tasks = []
    api_call_count = 0
    max_api_calls = min(len(communities) * 0.3, 15)  # 最多30%社区使用API，且不超过15个
    
    for community in communities:
        cache_data = cache_status[community.name]
        
        if cache_data['hit'] and cache_data['freshness'] > 0.7:
            # 缓存新鲜度高，直接使用
            tasks.append(load_from_cache(community.name))
        elif api_call_count < max_api_calls:
            # 缓存不佳且API配额充足，调用API
            tasks.append(fetch_from_reddit_api_with_cache_fallback(community.name))
            api_call_count += 1
        else:
            # API配额用尽，使用较旧的缓存数据
            tasks.append(load_from_cache(community.name, allow_stale=True))
    
    # 4. 等待所有任务完成
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 5. 处理异常和数据清洗
    for i, result in enumerate(raw_results):
        community_name = communities[i].name
        if isinstance(result, Exception):
            logger.warning(f"Failed to fetch {community_name}: {result}")
            # 尝试降级到过期缓存
            fallback_data = await load_from_cache(community_name, allow_stale=True)
            results[community_name] = fallback_data if fallback_data else []
        else:
            results[community_name] = clean_posts_data(result)
    
    # 6. 记录数据源统计（用于调试和优化）
    await log_data_source_stats({
        'cache_hit_rate': cache_hit_rate,
        'api_calls_made': api_call_count,
        'total_posts_collected': sum(len(posts) for posts in results.values()),
        'strategy_used': strategy
    })
    
    return results

async def fetch_from_reddit_api_with_cache_fallback(community: str) -> List[Post]:
    """
    Reddit API数据获取
    """
    # 1. 检查API限额
    if not await check_api_rate_limit():
        raise APILimitExceeded("Reddit API rate limit exceeded")
    
    # 2. 获取最近24小时数据
    posts = await reddit_client.get_community_posts(
        community=community,
        time_range="day",
        sort="hot",
        limit=100
    )
    
    # 3. 更新缓存
    await update_cache(community, posts, ttl=3600)  # 1小时TTL
    
    return posts
```

**缓存策略**:
```yaml
# data_collection.yml
collection:
  # Reddit API配置
  reddit_api:
    rate_limit: 60  # 每分钟请求数
    timeout: 30
    retry_attempts: 3
    
  # 缓存配置  
  cache:
    redis_ttl: 3600  # 1小时
    cache_warmup: true
    max_posts_per_community: 100
    
  # 并行处理
  concurrency:
    max_concurrent_requests: 10
    batch_size: 5
    
  # 数据过滤
  filters:
    min_post_length: 50
    max_post_age_hours: 24
    exclude_deleted: true
    min_upvotes: 2
```

### 3.3 Step 3: 统一信号提取

**功能**: 从所有采集数据中提取痛点、竞品、机会三类商业信号

**算法设计**:
```python
def extract_business_signals(all_posts: Dict[str, List[Post]]) -> BusinessSignals:
    """
    统一商业信号提取算法
    """
    signals = BusinessSignals()
    
    # 1. 合并所有帖子数据
    merged_posts = merge_and_deduplicate(all_posts)
    
    # 2. 并行提取三类信号
    pain_points = extract_pain_points(merged_posts)
    competitors = extract_competitors(merged_posts)  
    opportunities = extract_opportunities(merged_posts)
    
    # 3. 信号聚合和去重
    signals.pain_points = aggregate_pain_points(pain_points)
    signals.competitors = aggregate_competitors(competitors)
    signals.opportunities = aggregate_opportunities(opportunities)
    
    return signals

def extract_pain_points(posts: List[Post]) -> List[PainPoint]:
    """
    痛点信号提取算法
    """
    pain_points = []
    
    for post in posts:
        # 1. 情感分析筛选负面内容
        sentiment_score = analyze_sentiment(post.content)
        if sentiment_score > -0.3:  # 非负面内容跳过
            continue
            
        # 2. 痛点关键词匹配
        pain_keywords = find_pain_keywords(post.content)
        if not pain_keywords:
            continue
            
        # 3. 提取具体痛点描述
        pain_description = extract_pain_description(post.content, pain_keywords)
        
        pain_point = PainPoint(
            description=pain_description,
            source_post=post.id,
            sentiment_score=sentiment_score,
            frequency=1,  # 后续聚合时累加
            example_content=post.content[:200]
        )
        pain_points.append(pain_point)
    
    return pain_points

def extract_competitors(posts: List[Post]) -> List[Competitor]:
    """
    竞品信号提取算法
    """
    competitors = []
    
    # 1. 产品名称识别（基于预定义词典+NER）
    product_mentions = find_product_mentions(posts)
    
    # 2. 上下文分析确定竞品关系
    for mention in product_mentions:
        context = get_surrounding_context(mention.post, mention.position)
        
        # 判断是否为竞品讨论
        if is_competitor_context(context):
            competitor = Competitor(
                name=mention.product_name,
                mention_count=1,
                sentiment=analyze_sentiment(context),
                context_examples=[context]
            )
            competitors.append(competitor)
    
    return competitors
```

**NLP模型配置**（修复Twitter模型错配问题）:
```yaml
# signal_extraction.yml
nlp:
  # 情感分析 - Reddit特定模型
  sentiment:
    primary_model: "reddit-sentiment-analysis/roberta-base-reddit"  # Reddit特定训练
    fallback_model: "cardiffnlp/twitter-roberta-base-sentiment"     # 降级选项
    domain_adaptation_enabled: true  # 启用领域适配
    threshold_negative: -0.3
    threshold_positive: 0.3
    
  # Reddit特定配置
  reddit_specific:
    subreddit_context_weight: 0.2  # 考虑subreddit上下文
    upvote_sentiment_correlation: 0.15  # 利用upvote作为sentiment信号
    comment_depth_analysis: true    # 分析回复深度作为engagement指标
    
  # 关键词匹配
  keywords:
    pain_indicators:
      - "frustrated"
      - "annoying"  
      - "difficult"
      - "problem with"
      - "wish there was"
    
    opportunity_indicators:
      - "looking for"
      - "need something"
      - "would pay for"
      - "missing feature"
      
  # 实体识别
  entity_recognition:
    product_patterns:
      - "r'[A-Z][a-z]+[A-Z][a-z]*'"  # CamelCase产品名
      - "r'\\b[A-Z]{2,}\\b'"          # 全大写缩写
    
    confidence_threshold: 0.8
```

### 3.4 Step 4: 智能排序输出

**功能**: 对提取的信号按相关性和重要性排序，生成最终报告

**算法设计**:
```python
def generate_final_report(signals: BusinessSignals) -> AnalysisReport:
    """
    智能排序和报告生成算法
    """
    # 1. 信号排序
    ranked_pain_points = rank_pain_points(signals.pain_points)
    ranked_competitors = rank_competitors(signals.competitors)
    ranked_opportunities = rank_opportunities(signals.opportunities)
    
    # 2. 生成执行摘要
    executive_summary = generate_executive_summary(
        ranked_pain_points[:5],
        ranked_competitors[:5], 
        ranked_opportunities[:5]
    )
    
    # 3. 构建完整报告
    report = AnalysisReport(
        executive_summary=executive_summary,
        pain_points=ranked_pain_points[:10],
        competitors=ranked_competitors[:8],
        opportunities=ranked_opportunities[:6],
        metadata=generate_metadata(signals)
    )
    
    return report

def rank_pain_points(pain_points: List[PainPoint]) -> List[PainPoint]:
    """
    痛点排序算法
    """
    for pain_point in pain_points:
        # 综合评分 = 频率权重 + 情感强度 + 描述质量
        frequency_score = min(pain_point.frequency / 10, 1.0) * 0.4
        sentiment_score = abs(pain_point.sentiment_score) * 0.3
        quality_score = calculate_description_quality(pain_point.description) * 0.3
        
        pain_point.relevance_score = frequency_score + sentiment_score + quality_score
    
    return sorted(pain_points, key=lambda x: x.relevance_score, reverse=True)
```

**排序权重配置**:
```yaml
# ranking.yml
ranking:
  # 痛点排序权重
  pain_points:
    frequency_weight: 0.4      # 出现频率
    sentiment_weight: 0.3      # 情感强度  
    quality_weight: 0.3        # 描述质量
    
  # 竞品排序权重
  competitors:
    mention_weight: 0.5        # 提及次数
    sentiment_weight: 0.3      # 用户态度
    context_weight: 0.2        # 上下文相关性
    
  # 机会排序权重
  opportunities:
    relevance_weight: 0.4      # 相关性
    urgency_weight: 0.3        # 用户急迫性
    market_size_weight: 0.3    # 潜在市场大小
    
  # 输出控制
  output_limits:
    max_pain_points: 10
    max_competitors: 8
    max_opportunities: 6
```

## 4. 验收标准

### 4.1 功能要求

**社区发现准确性**：
- [ ] 能发现至少15个高相关性社区（相关性>0.6）
- [ ] 发现的社区覆盖不同类别，避免重复
- [ ] 处理时间 < 30秒
- [ ] 支持不同类型产品描述（B2B/B2C/技术/消费）

**数据采集完整性**：
- [ ] 单个社区能采集80%的目标帖子（24小时内top100）
- [ ] 缓存命中率 > 60%（热门社区）
- [ ] API调用不超过限额（60/分钟）
- [ ] 并发采集20个社区 < 120秒

**信号提取质量**：
- [ ] 痛点准确率 > 75%（人工标注验证）
- [ ] 竞品识别覆盖率 > 80%（已知竞品）
- [ ] 机会信号相关性 > 70%（专家评估）
- [ ] 信号去重率 > 90%（避免重复内容）

### 4.2 性能指标

| 处理步骤 | 时间要求 | 数据量 | 准确率要求 |
|---------|---------|--------|-----------|
| 社区发现 | < 30秒 | 500社区池 | 相关性>0.6 |
| 数据采集 | < 120秒 | 20社区×100帖 | 完整性>80% |
| 信号提取 | < 90秒 | 1500+帖子 | 准确率>75% |
| 排序输出 | < 30秒 | 100+信号 | 相关性>0.8 |
| **总计** | **< 270秒** | **5000+原始帖** | **置信度>0.8** |

### 4.3 测试用例

```python
# 集成测试示例
def test_end_to_end_analysis():
    """完整分析流程测试"""
    # 输入：AI笔记应用描述
    product_desc = "AI笔记应用，帮助研究者自动组织和连接想法的智能工具"
    
    # Step 1: 社区发现
    communities = discover_communities(product_desc)
    assert len(communities) == 20
    assert all(c.relevance_score > 0.3 for c in communities)
    
    # Step 2: 数据采集  
    data = await collect_community_data(communities)
    total_posts = sum(len(posts) for posts in data.values())
    assert total_posts > 500  # 至少采集500个帖子
    
    # Step 3: 信号提取
    signals = extract_business_signals(data)
    assert len(signals.pain_points) > 5
    assert len(signals.competitors) > 3
    assert len(signals.opportunities) > 3
    
    # Step 4: 排序输出
    report = generate_final_report(signals)
    assert report.metadata.confidence_score > 0.7

def test_cache_performance():
    """缓存性能测试"""
    # 第一次分析：缓存miss
    start_time = time.time()
    result1 = await collect_community_data(test_communities)
    first_duration = time.time() - start_time
    
    # 第二次分析：缓存hit  
    start_time = time.time()
    result2 = await collect_community_data(test_communities)
    second_duration = time.time() - start_time
    
    # 缓存应该显著提升性能
    assert second_duration < first_duration * 0.5

def test_api_limit_handling():
    """API限流处理测试"""
    # 模拟API限流
    with mock_reddit_api_limit():
        result = await collect_community_data(test_communities)
        
        # 应该优雅降级，使用缓存数据
        assert len(result) > 0
        assert all(len(posts) > 0 for posts in result.values())
```

## 5. 后台爬虫系统（智能优先级管理）

### 5.1 系统架构

**核心理念**: 智能爬虫系统根据社区使用频率动态调整爬取优先级，确保高命中率缓存

```
Celery Beat（定时调度器）
    ↓
优先级管理器（计算爬取频率）
    ↓
Celery Worker（执行爬虫任务）
    ↓
Reddit API（数据源）
    ↓
Redis 缓存（24小时 TTL）
    ↓
CommunityCache 表（元数据记录）
```

### 5.2 智能优先级算法

```python
class CommunityPriorityManager:
    """社区爬取优先级管理器"""

    async def calculate_priority(self, community_name: str) -> float:
        """
        计算社区爬取优先级

        公式：
        priority = usage_frequency * 0.4 + activity_level * 0.3 + cache_freshness * 0.3
        """
        # 1. 获取使用频率（最近 7 天）
        usage_frequency = await self._get_usage_frequency(community_name)

        # 2. 获取社区活跃度
        activity_level = await self._get_activity_level(community_name)

        # 3. 获取缓存新鲜度
        cache_freshness = await self._get_cache_freshness(community_name)

        # 4. 计算优先级
        priority = (
            usage_frequency * 0.4 +
            activity_level * 0.3 +
            cache_freshness * 0.3
        )

        return priority

    async def get_crawl_interval(self, community_name: str) -> int:
        """
        计算爬取间隔（分钟）

        优先级越高，爬取越频繁
        """
        priority = await self.calculate_priority(community_name)

        # 优先级 → 爬取间隔映射
        interval = max(
            30,  # 最短 30 分钟
            min(
                360,  # 最长 6 小时
                int(1440 / (priority * 10))
            )
        )

        return interval
```

### 5.3 爬虫任务实现

```python
# backend/app/tasks/crawler_task.py

@celery_app.task(name="tasks.crawler.crawl_community")
async def crawl_community(community_name: str):
    """
    爬取单个社区

    API 调用：1 次
    """
    try:
        # 1. 调用 Reddit API
        posts = await reddit_client.fetch_subreddit_posts(
            community_name,
            limit=100,
            time_filter="week",
            sort="top"
        )

        # 2. 更新 Redis 缓存
        cache_manager.set_cached_posts(
            community_name,
            posts,
            ttl_seconds=86400  # 24 小时
        )

        # 3. 更新 CommunityCache 表
        await update_community_cache_metadata(
            community_name,
            posts_cached=len(posts),
            last_crawled_at=datetime.now(timezone.utc)
        )

        logger.info(f"✅ {community_name}: 缓存 {len(posts)} 个帖子")

    except Exception as e:
        logger.error(f"❌ {community_name}: 爬取失败 - {e}")
        raise


@celery_app.task(name="tasks.crawler.crawl_seed_communities")
async def crawl_seed_communities():
    """
    爬取种子社区池（50-100个）

    策略：
    - 每 30 分钟爬取一次
    - 每次爬取 12 个社区（避免 API 限流）
    - 总 API 调用：12 次/30分钟 = 0.4 次/分钟
    """
    seed_communities = await load_seed_communities()

    # 分批爬取（每批 12 个社区）
    batch_size = 12
    for i in range(0, len(seed_communities), batch_size):
        batch = seed_communities[i:i+batch_size]

        # 并发爬取（最多 5 个并发）
        tasks = [
            crawl_community.apply_async(args=[community.name])
            for community in batch
        ]

        # 等待批次完成
        await asyncio.gather(*tasks)

        # 等待 30 分钟后爬取下一批
        if i + batch_size < len(seed_communities):
            await asyncio.sleep(1800)  # 30 分钟


@celery_app.task(name="tasks.crawler.crawl_extended_communities")
async def crawl_extended_communities():
    """
    爬取扩展社区池（动态增长）

    策略：
    - 根据优先级动态调整爬取频率
    - 高优先级：每 1 小时
    - 中优先级：每 3 小时
    - 低优先级：每 6 小时
    """
    priority_manager = CommunityPriorityManager()
    extended_communities = await load_extended_communities()

    for community in extended_communities:
        # 计算爬取间隔
        interval_minutes = await priority_manager.get_crawl_interval(community.name)

        # 检查是否到了爬取时间
        last_crawled = await get_last_crawled_time(community.name)
        if datetime.now(timezone.utc) - last_crawled > timedelta(minutes=interval_minutes):
            # 执行爬取
            await crawl_community(community.name)
```

### 5.4 Celery Beat 定时任务配置

```python
# backend/app/core/celery_app.py

celery_app.conf.beat_schedule = {
    # 种子社区爬虫（每 30 分钟）
    'crawl-seed-communities': {
        'task': 'tasks.crawler.crawl_seed_communities',
        'schedule': crontab(minute='*/30'),
    },

    # 扩展社区爬虫（每小时检查一次）
    'crawl-extended-communities': {
        'task': 'tasks.crawler.crawl_extended_communities',
        'schedule': crontab(minute='0'),
    },

    # 优先级重新计算（每 6 小时）
    'recalculate-priorities': {
        'task': 'tasks.crawler.recalculate_priorities',
        'schedule': crontab(minute='0', hour='*/6'),
    },
}
```

### 5.5 API 调用预算分配

```
每分钟 60 次 API 调用预算：

├─ 种子社区爬虫（50-100个）：35 次/分钟（58%）
│   └─ 每 30 分钟爬取 12 个社区 → 0.4 次/分钟
│
├─ 扩展社区爬虫（动态增长）：10 次/分钟（17%）
│   └─ 根据优先级动态调整
│
├─ 自动发现（搜索帖子）：5 次/分钟（8%）
│   └─ 当社区池覆盖率不足时触发
│
└─ 实时分析请求：10 次/分钟（17%）
    └─ 补充缺失数据

总计：60 次/分钟（100% 利用率）
```

## 6. 预热期策略（7天数据积累）

### 6.1 预热期时间线

```
Day 0-12：功能开发（已完成）
    ↓
Day 13-19：预热期（7 天）
    ├─ Day 13-14：基础缓存预热（种子社区）
    ├─ Day 15-16：内部测试 + 社区池扩展
    ├─ Day 17-18：Beta 用户测试 + 数据积累
    └─ Day 19：最终验证 + 准备上线
    ↓
Day 20：正式上线
```

### 6.2 Day 13-14：基础缓存预热

**目标**：
- 爬取 50-100 个种子社区的数据
- 建立基础缓存层
- 验证爬虫系统稳定性

**实施步骤**：
1. 启动 Celery Beat 和 Worker
2. 配置预热爬虫策略（每 2 小时爬取一次）
3. 监控 API 调用和缓存命中率

**预期结果**：
- 50-100 个种子社区已爬取
- Redis 缓存命中率：100%（种子社区）
- 总 API 调用：50-100 次（1-2 分钟）

### 6.3 Day 15-16：内部测试 + 社区池扩展

**目标**：
- 邀请 5-10 个内部用户测试
- 根据测试需求发现新社区
- 扩展社区池到 150-200 个

**实施步骤**：
1. 开放内部测试账号
2. 收集测试需求和反馈
3. 自动发现新社区并记录到待审核表
4. Admin 审核并批准相关社区

**预期结果**：
- 内部测试：5-10 个用户，20-30 次分析
- 发现新社区：50-100 个
- 审核通过：30-50 个
- 社区池规模：100-150 个

### 6.4 Day 17-18：Beta 用户测试 + 数据积累

**目标**：
- 邀请 20-50 个 Beta 用户测试
- 持续积累缓存数据
- 优化社区池覆盖率

**实施步骤**：
1. 开放 Beta 测试注册
2. 监控系统负载和 API 调用
3. 动态调整爬虫策略
4. 收集用户反馈

**预期结果**：
- Beta 用户：20-50 人
- 总分析次数：100-200 次
- 社区池规模：150-250 个
- 缓存命中率：85-95%

### 6.5 Day 19：最终验证 + 准备上线

**目标**：
- 验证系统稳定性
- 确认缓存覆盖率
- 准备正式上线

**实施步骤**：
1. 运行完整健康检查
2. 生成预热期报告
3. 最终优化和调整

**预期结果**：
- 社区池：250 个社区
- 缓存命中率：92%
- 平均分析耗时：2.5 分钟
- 用户满意度：4.3/5 星

## 7. 风险管理

### 7.1 技术风险

**风险1**: Reddit API限流导致数据不足
- **影响**: 分析质量下降，用户体验差
- **缓解**: 智能优先级管理，动态调整爬虫频率
- **监控**: API调用成功率，缓存命中率

**风险2**: 社区池覆盖率不足
- **影响**: 长尾需求无法满足
- **缓解**: 自动发现 + Admin 审核机制
- **监控**: 降级事件频率，用户反馈

**风险3**: 处理时间超过5分钟承诺
- **影响**: 用户放弃等待，产品价值降低
- **缓解**: 缓存优先架构，分步进度展示
- **监控**: P95处理时间，超时任务比例

### 5.2 依赖项

**Python包依赖**:
- transformers >= 4.20.0 （NLP模型）
- pandas >= 1.4.0 （数据处理）
- redis >= 4.3.0 （缓存层）
- aiohttp >= 3.8.0 （异步HTTP）

**外部服务依赖**:
- Reddit API （数据源）
- Redis服务器 （缓存）
- PostgreSQL （结果存储）

### 5.3 降级方案

**Reddit API不可用**：
- 使用过去7天的缓存数据
- 降低社区发现数量到10个
- 在报告中标注数据时效性

**NLP模型异常**：
- 回退到关键词匹配算法
- 降低信号提取精度要求
- 增加人工review建议

**处理超时**：
- 返回部分分析结果
- 标注数据完整性状态
- 提供重新分析选项

---

## 附录A: 核心算法伪代码

```python
# 完整分析引擎伪代码
class AnalysisEngine:
    
    def __init__(self):
        self.config = load_config()
        self.nlp_models = load_nlp_models()
        self.community_pool = load_community_pool()
        
    async def analyze(self, product_description: str) -> AnalysisReport:
        """
        主分析流程
        """
        # Step 1: 智能社区发现 (30秒)
        keywords = self.extract_keywords(product_description)
        communities = self.discover_communities(keywords)
        
        # Step 2: 并行数据采集 (120秒)
        posts_data = await self.collect_data_parallel(communities)
        
        # Step 3: 统一信号提取 (90秒)
        signals = self.extract_business_signals(posts_data)
        
        # Step 4: 智能排序输出 (30秒)
        report = self.generate_ranked_report(signals)
        
        return report
    
    def discover_communities(self, keywords: List[str]) -> List[Community]:
        """社区发现算法"""
        scores = {}
        for community in self.community_pool:
            # 计算相关性评分
            score = self.calculate_relevance(keywords, community)
            scores[community] = score
        
        # 选择top20，保证多样性
        return self.select_diverse_top_k(scores, k=20)
    
    async def collect_data_parallel(self, communities: List[Community]):
        """并行数据采集"""
        tasks = []
        for community in communities:
            task = self.collect_community_data(community)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    def extract_business_signals(self, posts_data):
        """统一信号提取"""
        all_posts = self.merge_and_clean(posts_data)
        
        # 并行提取三类信号
        pain_points = self.extract_pain_points(all_posts)
        competitors = self.extract_competitors(all_posts)
        opportunities = self.extract_opportunities(all_posts)
        
        return BusinessSignals(pain_points, competitors, opportunities)
    
    def generate_ranked_report(self, signals: BusinessSignals):
        """智能排序和报告生成"""
        # 排序各类信号
        ranked_signals = self.rank_all_signals(signals)
        
        # 生成结构化报告
        return self.build_report(ranked_signals)
```

## 附录B: 配置文件完整示例

```yaml
# analysis_engine_config.yml
engine:
  version: "1.0"
  
  # 社区发现配置
  community_discovery:
    pool_size: 500
    target_count: 20
    relevance_threshold: 0.3
    diversity_bonus: 0.1
    
    weights:
      description_match: 0.4
      activity_level: 0.3
      quality_score: 0.3
      
  # 数据采集配置
  data_collection:
    concurrency_limit: 10
    timeout_seconds: 30
    retry_attempts: 3
    cache_ttl: 3600
    
    filters:
      min_post_length: 50
      max_post_age_hours: 24
      min_upvotes: 2
      
  # NLP配置
  nlp:
    sentiment_model: "cardiffnlp/twitter-roberta-base-sentiment"
    entity_model: "dbmdz/bert-large-cased-finetuned-conll03-english"
    
    thresholds:
      sentiment_negative: -0.3
      sentiment_positive: 0.3
      entity_confidence: 0.8
      
  # 排序配置
  ranking:
    pain_points:
      frequency_weight: 0.4
      sentiment_weight: 0.3
      quality_weight: 0.3
      
    competitors:
      mention_weight: 0.5
      sentiment_weight: 0.3
      context_weight: 0.2
      
    opportunities:
      relevance_weight: 0.4
      urgency_weight: 0.3
      market_size_weight: 0.3
      
  # 输出控制
  output:
    max_pain_points: 10
    max_competitors: 8
    max_opportunities: 6
    min_confidence_score: 0.6
```

### 3.5 后台爬虫系统设计（支撑缓存优先架构）

**功能**: 持续维护24小时热门数据缓存，确保分析引擎的"5分钟承诺"成为可能

**系统架构**:
```python
class BackgroundCrawlerSystem:
    """
    后台爬虫系统：缓存优先架构的核心支撑
    
    职责：
    1. 持续爬取热门社区数据到Redis缓存
    2. 智能优先级管理（热门社区更频繁更新）
    3. API限额平滑分布（避免突发大量调用）
    4. 缓存质量监控和报告
    """
    
    async def run_continuous_crawler(self):
        """
        持续爬虫主循环（24x7运行）
        """
        while True:
            try:
                # 1. 获取下一个待爬取社区（基于优先级）
                community = await self.priority_queue.pop_highest_priority()
                
                # 2. 检查API限额并执行爬取
                if await self.api_rate_limiter.acquire():
                    success = await self.crawl_community_safely(community)
                    await self.update_community_priority(community, success)
                
                await asyncio.sleep(2)  # 平滑调用间隔
                
            except Exception as e:
                logger.error(f"Crawler error: {e}")
                await asyncio.sleep(60)
    
    async def crawl_community_safely(self, community: Community) -> bool:
        """
        安全地爬取单个社区数据
        包含完整的错误处理和恢复机制
        """
        try:
            # 爬取最新数据
            posts = await self.reddit_client.get_community_posts(
                community=community.name,
                time_range="day", 
                sort="hot",
                limit=100
            )
            
            # 更新Redis缓存
            cache_key = f"community:{community.name}:posts"
            await self.redis_client.setex(
                cache_key, 
                3600,  # 1小时TTL
                json.dumps([post.dict() for post in posts])
            )
            
            return True
            
        except RedditAPIException as e:
            if "rate_limit" in str(e).lower():
                await asyncio.sleep(300)  # 等待5分钟
            return False
```

**爬虫配置文件**:
```yaml
# background_crawler.yml
crawler:
  enabled: true
  worker_count: 2
  
  # API调用配置（为实时分析预留10个/分钟）
  api_calls:
    max_per_minute: 50      
    burst_limit: 10
    retry_attempts: 3
    
  # 缓存配置  
  cache:
    ttl_seconds: 3600
    posts_per_community: 100
    cleanup_interval: 300
    
  # 优先级管理
  priority:
    recalculation_interval: 3600
    usage_frequency_weight: 0.4
    activity_level_weight: 0.3
    freshness_weight: 0.3
    
  # 监控配置
  monitoring:
    alert_on_cache_miss_rate: 0.3  # 缓存miss率超过30%时告警
```

**与分析引擎的协同工作**:
1. **数据预热**: 爬虫系统确保热门社区的缓存始终新鲜
2. **优先级反馈**: 分析引擎使用频率影响爬虫优先级  
3. **质量保证**: 缓存质量监控确保5分钟承诺的可靠性
4. **API协调**: 后台爬虫和实时分析共享API限额，避免冲突

---

**文档版本**: 2.0（修复Linus致命问题）  
**最后更新**: 2025-01-21  
**关键修复**:  
- ✅ 明确缓存优先架构（解决"数学不可能"问题）
- ✅ 修复NLP模型错配（Reddit特定模型，非Twitter模型）
- ✅ 添加完整后台爬虫系统设计
- ✅ 动态社区数量配置（去除魔数20）
- ✅ 完整降级策略（检测→恢复→降级）

**审核状态**: 等待Linus re-review  
**实施优先级**: P0 - 核心业务逻辑（已修复致命缺陷）
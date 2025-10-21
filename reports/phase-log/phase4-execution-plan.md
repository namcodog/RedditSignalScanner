# Phase 4 执行计划：迭代与延伸

**创建时间**: 2025-10-20  
**预估工期**: 12 天（T+18~30 天）  
**任务总数**: 44 个（1 个根任务 + 6 个主任务 + 37 个子任务）

---

## 📊 Phase 4 总览

**目标**: 两周总结、NER、趋势分析、证据图谱

| 任务 | 描述 | 子任务数 | 预估时间 | 优先级 | 依赖 |
|------|------|----------|----------|--------|------|
| **T4.1** | 生成两周迭代总结 | 6 | 2h | P0 | T3.6 |
| **T4.2** | 实现轻量 NER | 6 | 4h | P1 | T4.1 |
| **T4.3** | 实现趋势分析 | 6 | 3h | P1 | T4.1 |
| **T4.4** | 实现证据图谱 | 7 | 4h | P1 | T4.1 |
| **T4.5** | 实现实体词典 | 7 | 3h | P2 | T4.2 |
| **T4.6** | 实现态度极性过滤 | 6 | 2h | P1 | T4.1 |

---

## 🎯 T4.1: 生成两周迭代总结

### 目标
复盘社区扩容、规则改造、阈值调整效果，生成总结报告并规划下一月工作。

### 验收标准
- ✅ 总结报告已生成（`reports/phase-log/phase5-summary.md`）
- ✅ 下一月计划已制定

### 实施要点

#### T4.1.1: 收集社区扩容数据
```sql
-- 查询社区数量增长
SELECT 
    DATE(created_at) as date,
    COUNT(DISTINCT subreddit) as community_count
FROM posts_raw
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
```

#### T4.1.2: 收集样本量提升数据
```sql
-- 查询样本量增长
SELECT 
    DATE(created_at) as date,
    COUNT(*) as post_count
FROM posts_raw
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
```

#### T4.1.3: 收集规则优化数据
```python
# 读取阈值优化结果
import pandas as pd
df = pd.read_csv('reports/threshold_optimization.csv')
best_threshold = df.loc[df['precision_at_50'].idxmax()]
print(f"最优阈值: {best_threshold['threshold']:.2f}")
print(f"Precision@50: {best_threshold['precision_at_50']:.2f}")
print(f"F1 Score: {best_threshold['f1_score']:.2f}")
```

#### T4.1.4: 收集红线触发次数
```python
# 从日志或数据库统计红线触发次数
# 示例：grep "Red line triggered" logs/celery.log | wc -l
```

#### T4.1.5-T4.1.6: 写入总结报告并规划下一月工作
**报告模板**:
```markdown
# Phase 5 迭代总结

## 数据增长
- 社区数量: 102 → 300 (+194%)
- 样本量: 3K → 15K+ (+400%)

## 规则优化
- Precision@50: 0.45 → 0.62 (+38%)
- F1 Score: 0.52 → 0.68 (+31%)

## 红线触发
- 红线 1（有效帖子不足）: 3 次
- 红线 2（缓存命中率低）: 1 次
- 红线 3（重复率高）: 0 次
- 红线 4（精准率低）: 2 次

## 下一月计划
1. 实现 NER 提升实体识别能力
2. 实现趋势分析支持时间序列洞察
3. 实现证据图谱增强可解释性
```

---

## 🤖 T4.2: 实现轻量 NER

### 目标
使用 spaCy 或词典+正则提取实体（产品、功能、受众、行业）。

### 验收标准
- ✅ 实体提取准确率 ≥70%
- ✅ 集成到评分器

### 最佳实践（来自 exa-code）

#### spaCy NER 基础用法
```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp("Apple is looking at buying U.K. startup for $1 billion")

for ent in doc.ents:
    print(ent.text, ent.label_)
# Output:
# Apple ORG
# U.K. GPE
# $1 billion MONEY
```

#### Entity Ruler（自定义实体）
```python
from spacy.lang.en import English

nlp = English()
ruler = nlp.add_pipe("entity_ruler")
patterns = [
    {"label": "PRODUCT", "pattern": "CRM"},
    {"label": "PRODUCT", "pattern": "ERP"},
    {"label": "FEATURE", "pattern": [{"LOWER": "export"}, {"LOWER": "feature"}]}
]
ruler.add_patterns(patterns)

doc = nlp("Our CRM export feature is broken.")
print([(ent.text, ent.label_) for ent in doc.ents])
# Output: [('CRM', 'PRODUCT'), ('export feature', 'FEATURE')]
```

### 实施要点

#### T4.2.1: 安装 spaCy 和模型
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

#### T4.2.2-T4.2.4: 创建 EntityExtractor 类
**文件**: `backend/app/services/analysis/entity_extractor.py`

```python
import spacy
from typing import Dict, List, Set

class EntityExtractor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        # 添加自定义实体规则
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        patterns = self._load_entity_patterns()
        ruler.add_patterns(patterns)
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """提取实体并分类为产品、功能、受众、行业"""
        doc = self.nlp(text)
        entities = {
            "products": [],
            "features": [],
            "audiences": [],
            "industries": []
        }
        
        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "ORG"]:
                entities["products"].append(ent.text)
            elif ent.label_ == "FEATURE":
                entities["features"].append(ent.text)
            elif ent.label_ in ["PERSON", "NORP"]:
                entities["audiences"].append(ent.text)
            elif ent.label_ == "INDUSTRY":
                entities["industries"].append(ent.text)
        
        return entities
    
    def _load_entity_patterns(self) -> List[Dict]:
        """加载自定义实体模式"""
        return [
            {"label": "PRODUCT", "pattern": "CRM"},
            {"label": "PRODUCT", "pattern": "ERP"},
            {"label": "FEATURE", "pattern": "export"},
            # ... 更多模式
        ]
```

#### T4.2.5: 集成到 OpportunityScorer
```python
# 在 OpportunityScorer 中
from app.services.analysis.entity_extractor import EntityExtractor

class OpportunityScorer:
    def __init__(self):
        self.entity_extractor = EntityExtractor()
    
    def score(self, post: RedditPost) -> float:
        # ... 原有评分逻辑
        
        # 实体匹配加分
        entities = self.entity_extractor.extract_entities(post.body)
        entity_bonus = 0.0
        if entities["products"]:
            entity_bonus += 0.1
        if entities["features"]:
            entity_bonus += 0.05
        
        return base_score + entity_bonus
```

---

## 📈 T4.3: 实现趋势分析

### 目标
输出主题趋势曲线（7/14/30 天），支持时间序列可视化。

### 验收标准
- ✅ 趋势图生成成功
- ✅ 支持 7/14/30 天窗口

### 最佳实践（来自 exa-code）

#### Matplotlib 时间序列可视化
```python
import matplotlib.pyplot as plt
import pandas as pd

# 准备数据
df = pd.DataFrame({
    'date': pd.date_range('2023-01-01', periods=30, freq='D'),
    'count': [10, 12, 15, 18, 20, ...]
})

# 绘制趋势图
plt.figure(figsize=(12, 6))
plt.plot(df['date'], df['count'], marker='o', label='帖子数量')
plt.xlabel('日期')
plt.ylabel('帖子数量')
plt.title('30 天趋势分析')
plt.legend()
plt.grid(True)
plt.savefig('reports/trends/2023-01-30.png')
```

### 实施要点

#### T4.3.1-T4.3.2: 创建 TrendAnalyzer 类
**文件**: `backend/app/services/analysis/trend_analyzer.py`

```python
from datetime import date, timedelta
from typing import List, Dict
import pandas as pd
import matplotlib.pyplot as plt

class TrendAnalyzer:
    async def analyze_trends(
        self,
        *,
        window_days: int = 30,
        keywords: List[str] = None,
        session_factory = SessionFactory
    ) -> pd.DataFrame:
        """分析趋势数据"""
        async with session_factory() as session:
            # 查询数据
            query = select(
                func.date(PostsRaw.created_at).label('date'),
                func.count(PostsRaw.id).label('count')
            ).where(
                PostsRaw.created_at >= date.today() - timedelta(days=window_days)
            ).group_by(
                func.date(PostsRaw.created_at)
            ).order_by('date')
            
            result = await session.execute(query)
            rows = result.all()
            
            return pd.DataFrame(rows, columns=['date', 'count'])
    
    def plot_trends(
        self,
        df: pd.DataFrame,
        output_path: str,
        title: str = "趋势分析"
    ):
        """绘制趋势图"""
        plt.figure(figsize=(12, 6))
        plt.plot(df['date'], df['count'], marker='o', linewidth=2)
        plt.xlabel('日期')
        plt.ylabel('帖子数量')
        plt.title(title)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        plt.close()
```

---

## 🕸️ T4.4: 实现证据图谱

### 目标
构建证据图谱数据结构，支持机会-证据关系可视化。

### 验收标准
- ✅ 证据图谱生成成功
- ✅ JSON 格式正确（node-link 格式）

### 最佳实践（来自 exa-code）

#### NetworkX 图谱构建与导出
```python
import networkx as nx
from networkx.readwrite import json_graph
import json

# 创建图
G = nx.DiGraph()

# 添加节点
G.add_node("opp1", type="opportunity", problem="CRM export broken")
G.add_node("post1", type="evidence", title="Export doesn't work")

# 添加边
G.add_edge("opp1", "post1", relevance=0.95)

# 导出 JSON
data = json_graph.node_link_data(G)
with open('evidence_graph.json', 'w') as f:
    json.dump(data, f, indent=2)
```

### 实施要点

#### T4.4.1-T4.4.6: 创建 EvidenceGraph 类
**文件**: `backend/app/services/reporting/evidence_graph.py`

```python
import networkx as nx
from networkx.readwrite import json_graph
from typing import List, Dict, Any
import json

class EvidenceGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def add_opportunity_node(
        self,
        opportunity_id: str,
        problem_definition: str,
        priority: float
    ):
        """添加机会节点"""
        self.graph.add_node(
            opportunity_id,
            type="opportunity",
            problem=problem_definition,
            priority=priority
        )
    
    def add_evidence_node(
        self,
        post_id: str,
        title: str,
        url: str | None,
        score: float
    ):
        """添加证据节点"""
        self.graph.add_node(
            post_id,
            type="evidence",
            title=title,
            url=url,
            score=score
        )
    
    def add_edge(
        self,
        opportunity_id: str,
        post_id: str,
        relevance_score: float
    ):
        """添加边（机会 → 证据）"""
        self.graph.add_edge(
            opportunity_id,
            post_id,
            relevance=relevance_score
        )
    
    def to_json(self) -> Dict[str, Any]:
        """导出 JSON 格式"""
        return json_graph.node_link_data(self.graph)
    
    def save(self, output_path: str):
        """保存到文件"""
        with open(output_path, 'w') as f:
            json.dump(self.to_json(), f, indent=2)
```

---

## 📚 T4.5: 实现实体词典

### 目标
建立行业实体词典，支持槽位匹配。

### 验收标准
- ✅ 词典创建成功（`config/entity_dictionary.yaml`）
- ✅ 槽位匹配生效

### 实施要点

#### T4.5.1-T4.5.5: 创建实体词典配置文件
**文件**: `config/entity_dictionary.yaml`

```yaml
products:
  - CRM
  - ERP
  - SaaS
  - API
  - Dashboard
  - Analytics
  - Workflow

features:
  - export
  - import
  - integration
  - automation
  - reporting
  - analytics
  - collaboration

audiences:
  - startup
  - enterprise
  - SMB
  - developer
  - marketer
  - sales team
  - product manager

industries:
  - fintech
  - healthcare
  - e-commerce
  - SaaS
  - AI
  - edtech
  - logistics

competitors:
  - Salesforce
  - HubSpot
  - Zendesk
  - Intercom
  - Slack
```

#### T4.5.6: 实现槽位匹配逻辑
```python
import yaml
from typing import Dict, List, Set

class EntityDictionary:
    def __init__(self, config_path: str = "config/entity_dictionary.yaml"):
        with open(config_path) as f:
            self.dictionary = yaml.safe_load(f)
    
    def match_entity_slots(self, text: str) -> Dict[str, List[str]]:
        """匹配文本中的实体槽位"""
        text_lower = text.lower()
        matches = {
            "products": [],
            "features": [],
            "audiences": [],
            "industries": [],
            "competitors": []
        }
        
        for category, entities in self.dictionary.items():
            for entity in entities:
                if entity.lower() in text_lower:
                    matches[category].append(entity)
        
        return matches
```

---

## 😡 T4.6: 实现态度极性过滤

### 目标
定义强负面词库并过滤，避免将抱怨误判为机会。

### 验收标准
- ✅ 负面帖子被过滤
- ✅ 抱怨不被当成机会

### 实施要点

#### T4.6.1: 创建负面词库配置
**文件**: `config/negative_keywords.yaml`

```yaml
strong_negative:
  - hate
  - terrible
  - awful
  - useless
  - garbage
  - worst

moderate_negative:
  - doesn't work
  - broken
  - frustrating
  - annoying
  - disappointing
  - confusing
```

#### T4.6.2-T4.6.4: 实现极性检测和过滤逻辑
```python
import yaml

class SentimentFilter:
    def __init__(self, config_path: str = "config/negative_keywords.yaml"):
        with open(config_path) as f:
            self.keywords = yaml.safe_load(f)
    
    def detect_sentiment_polarity(self, text: str) -> tuple[str, float]:
        """检测情感极性，返回 (极性, 降权系数)"""
        text_lower = text.lower()
        
        # 检查强负面词
        for keyword in self.keywords["strong_negative"]:
            if keyword in text_lower:
                return ("strong_negative", 0.0)  # 直接过滤
        
        # 检查中等负面词
        for keyword in self.keywords["moderate_negative"]:
            if keyword in text_lower:
                return ("moderate_negative", 0.5)  # 降权 50%
        
        return ("neutral", 1.0)  # 无降权
```

---

## 📅 推荐执行顺序

### 第 1 天：迭代总结
- ✅ T4.1.1-T4.1.6: 生成两周迭代总结（2 小时）

### 第 2-3 天：NER 实现
- ✅ T4.2.1-T4.2.6: 实现轻量 NER（4 小时）
- ✅ T4.6.1-T4.6.6: 实现态度极性过滤（2 小时）

### 第 4-5 天：趋势分析
- ✅ T4.3.1-T4.3.6: 实现趋势分析（3 小时）

### 第 6-7 天：证据图谱
- ✅ T4.4.1-T4.4.7: 实现证据图谱（4 小时）

### 第 8-9 天：实体词典
- ✅ T4.5.1-T4.5.7: 实现实体词典（3 小时）

### 第 10-12 天：集成测试与优化
- ✅ 集成所有功能到分析引擎
- ✅ 端到端测试
- ✅ 性能优化

---

## 📁 预计新增文件

### 后端文件（8 个）
- `backend/app/services/analysis/entity_extractor.py`
- `backend/app/services/analysis/trend_analyzer.py`
- `backend/app/services/reporting/evidence_graph.py`
- `backend/tests/services/analysis/test_entity_extractor.py`
- `backend/tests/services/analysis/test_trend_analyzer.py`
- `backend/tests/services/reporting/test_evidence_graph.py`

### 配置文件（3 个）
- `config/entity_dictionary.yaml`
- `config/negative_keywords.yaml`

### 报告文件
- `reports/phase-log/phase5-summary.md`
- `reports/trends/YYYY-MM-DD.png`（趋势图）
- `reports/evidence_graphs/YYYY-MM-DD.json`（证据图谱）

---

## 🎯 成功标准

1. **T4.1**: 总结报告完整，数据准确
2. **T4.2**: NER 准确率 ≥70%，集成到评分器
3. **T4.3**: 趋势图清晰，支持 7/14/30 天窗口
4. **T4.4**: 证据图谱 JSON 格式正确，可导入前端
5. **T4.5**: 实体词典覆盖主要领域，槽位匹配生效
6. **T4.6**: 负面帖子被正确过滤，抱怨不被误判为机会

---

**创建人**: AI Agent  
**创建日期**: 2025-10-20


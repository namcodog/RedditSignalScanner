# Phase 3 执行计划：评测与优化

**生成时间**: 2025-10-20
**状态**: 规划完成，待执行
**预估总时间**: 18-20 小时
**依赖**: Phase 1 (T1.1-T1.8) 和 Phase 2 (T2.1-T2.10) 已完成

---

## 📋 总览

Phase 3 包含 **6 个主任务** 和 **49 个子任务**，涵盖：

1. **T3.1**: 抽样标注数据集（500 条，人工标注）
2. **T3.2**: 阈值网格搜索（Precision@50 ≥0.6）
3. **T3.3**: 每日跑分脚本（自动化指标收集）
4. **T3.4**: 红线检查逻辑（4 条红线，自动降级）
5. **T3.5**: 改造报告模版（行动位）
6. **T3.6**: 集成行动位到 API（前后端集成）

---

## 🎯 任务详情

### T3.1: 抽样标注数据集

**目标**: 从冷库抽样 500 条帖子进行人工标注
**预估时间**: 4 小时（代码 1h + 人工标注 3h）
**依赖**: T2.10（去重集成）
**优先级**: P0（阻塞 T3.2）

#### 子任务

| 任务 | 描述 | 预估时间 | 依赖 | 可并行 |
|------|------|----------|------|--------|
| T3.1.1 | 实现抽样函数 `sample_posts_for_labeling` | 20min | - | ✅ |
| T3.1.2 | 创建标注 CSV 模板 | 10min | - | ✅ |
| T3.1.3 | 实现 CSV 导出函数 `export_samples_to_csv` | 15min | T3.1.1, T3.1.2 | ❌ |
| T3.1.4 | 创建标注验证函数 `validate_labels` | 15min | T3.1.2 | ✅ |
| T3.1.5 | **用户标注（人工任务）** | 3h | T3.1.3 | ❌ |
| T3.1.6 | 加载标注数据函数 `load_labeled_data` | 10min | T3.1.2 | ✅ |
| T3.1.7 | 测试标注流程 | 10min | T3.1.1-T3.1.6 | ❌ |

#### 实现要点

1. **抽样策略**（T3.1.1）：
   - 从 `posts_raw` 表随机抽样 500 条（最近 30 天）
   - 确保多样性：
     - 不同社区（至少 20 个社区）
     - 不同分数区间（0-10, 10-50, 50-100, 100+）
   - 使用 SQL `ORDER BY RANDOM()` 或 Python `random.sample()`

2. **CSV 格式**（T3.1.2）：
   ```csv
   post_id,title,body,subreddit,score,label,strength,notes
   abc123,"Need a CRM","Looking for...",startups,45,opportunity,strong,""
   ```
   - `label`: `opportunity` / `non-opportunity`
   - `strength`: `strong` / `medium` / `weak`

3. **验证逻辑**（T3.1.4）：
   - 检查 500 条全部标注
   - 检查 `label` 和 `strength` 字段有效性
   - 检查无空值（除 `notes`）

#### 验收标准

- ✅ 500 条样本已抽样并导出到 `data/labeled_samples_template.csv`
- ✅ 用户完成标注，保存到 `data/labeled_samples.csv`
- ✅ 验证函数通过，无错误

---

### T3.2: 实现阈值网格搜索

**目标**: 网格搜索最优阈值（Precision@50 ≥0.6）
**预估时间**: 2 小时
**依赖**: T3.1（标注数据集）
**优先级**: P0（核心功能）

#### 子任务

| 任务 | 描述 | 预估时间 | 依赖 | 可并行 |
|------|------|----------|------|--------|
| T3.2.1 | 实现评分函数 `score_posts` | 15min | T3.1 | ❌ |
| T3.2.2 | 实现 Precision@K 计算 | 20min | T3.2.1 | ❌ |
| T3.2.3 | 实现 F1 Score 计算 | 20min | T3.2.1 | ✅ |
| T3.2.4 | 实现网格搜索函数 `grid_search_threshold` | 30min | T3.2.2, T3.2.3 | ❌ |
| T3.2.5 | 选择最优阈值 | 10min | T3.2.4 | ❌ |
| T3.2.6 | 更新配置文件 | 10min | T3.2.5 | ❌ |
| T3.2.7 | 测试阈值优化 | 15min | T3.2.6 | ❌ |

#### 实现要点

1. **评分函数**（T3.2.1）：
   ```python
   def score_posts(labeled_df: pd.DataFrame) -> pd.DataFrame:
       """对标注数据集中的每条帖子计算 OpportunityScorer 分数"""
       scorer = OpportunityScorer()
       labeled_df['predicted_score'] = labeled_df.apply(
           lambda row: scorer.score(f"{row['title']} {row['body']}").base_score,
           axis=1
       )
       return labeled_df
   ```

2. **Precision@K 计算**（T3.2.2）：
   ```python
   def calculate_precision_at_k(df: pd.DataFrame, threshold: float, k: int = 50) -> float:
       """给定阈值，计算 Top-K 的精准率"""
       df_sorted = df.sort_values('predicted_score', ascending=False).head(k)
       true_positives = (df_sorted['label'] == 'opportunity').sum()
       return true_positives / k
   ```

3. **网格搜索**（T3.2.4）：
   - 阈值范围：`np.arange(0.3, 0.95, 0.05)`
   - 记录每个阈值的 Precision@50 和 F1
   - 输出结果到 `reports/threshold_optimization.csv`

4. **最佳实践**（来自 exa-code）：
   - 使用 sklearn 的 `TunedThresholdClassifierCV`（可选）
   - 优先 Precision@50 ≥0.6，其次最大化 F1

#### 验收标准

- ✅ 最优阈值 Precision@50 ≥0.6
- ✅ 配置文件已更新（`config/thresholds.yaml`）
- ✅ 网格搜索结果保存到 `reports/threshold_optimization.csv`

---

### T3.3: 创建每日跑分脚本

**目标**: 生成每日指标报告（自动化）
**预估时间**: 3 小时
**依赖**: T1.4（埋点功能）
**优先级**: P1（监控基础设施）

#### 子任务

| 任务 | 描述 | 预估时间 | 依赖 | 可并行 |
|------|------|----------|------|--------|
| T3.3.1 | 创建每日指标模型 `DailyMetrics` | 15min | - | ✅ |
| T3.3.2 | 实现指标收集函数 `collect_daily_metrics` | 30min | T3.3.1 | ❌ |
| T3.3.3 | 实现 CSV 写入函数 `write_metrics_to_csv` | 20min | T3.3.1 | ✅ |
| T3.3.4 | 创建 Celery 定时任务 | 30min | T3.3.2, T3.3.3 | ❌ |
| T3.3.5 | 更新 Celery Beat 配置 | 15min | T3.3.4 | ❌ |
| T3.3.6 | 测试跑分脚本 | 30min | T3.3.5 | ❌ |

#### 实现要点

1. **每日指标模型**（T3.3.1）：
   ```python
   @dataclass
   class DailyMetrics:
       date: date
       cache_hit_rate: float
       valid_posts_24h: int
       total_communities: int
       duplicate_rate: float
       precision_at_50: float
       avg_score: float
   ```

2. **指标收集**（T3.3.2）：
   - 从 `crawl_metrics` 表聚合当日数据（按 `metric_date` 分组）
   - 计算 `duplicate_rate = total_duplicates / (total_new_posts + total_updated_posts + total_duplicates)`
   - 计算 `precision_at_50`（需要标注数据集）

3. **CSV 格式**（T3.3.3）：
   - 文件路径：`reports/daily_metrics/YYYY-MM.csv`
   - 追加写入（不覆盖）
   - 字段：`date,cache_hit_rate,valid_posts_24h,total_communities,duplicate_rate,precision_at_50,avg_score`

4. **Celery 定时任务**（T3.3.4-T3.3.5）：
   ```python
   @celery_app.task(name="tasks.metrics.generate_daily")
   def generate_daily_metrics_task():
       metrics = collect_daily_metrics()
       write_metrics_to_csv(metrics)

   # Celery Beat 配置
   celery_app.conf.beat_schedule["generate-daily-metrics"] = {
       "task": "tasks.metrics.generate_daily",
       "schedule": crontab(hour=0, minute=0),  # 每日 0 点
   }
   ```

#### 验收标准

- ✅ 每日自动生成报告（Celery Beat 定时任务）
- ✅ CSV 格式正确，数据完整
- ✅ 手动触发测试通过

---

### T3.4: 实现红线检查逻辑

**目标**: 检查红线触发条件并自动降级
**预估时间**: 2 小时
**依赖**: T3.3（每日跑分）
**优先级**: P1（质量保障）

#### 子任务

| 任务 | 描述 | 预估时间 | 依赖 | 可并行 |
|------|------|----------|------|--------|
| T3.4.1 | 创建红线配置 `RedLineConfig` | 15min | - | ✅ |
| T3.4.2 | 实现红线检查函数 `check_red_lines` | 20min | T3.4.1 | ❌ |
| T3.4.3 | 实现降级策略 1（保守模式） | 15min | T3.4.2 | ✅ |
| T3.4.4 | 实现降级策略 2（提升抓取频率） | 15min | T3.4.2 | ✅ |
| T3.4.5 | 实现降级策略 3（改进去重） | 15min | T3.4.2 | ✅ |
| T3.4.6 | 实现降级策略 4（提高阈值） | 15min | T3.4.2 | ✅ |
| T3.4.7 | 集成红线检查到每日跑分 | 10min | T3.4.3-T3.4.6 | ❌ |
| T3.4.8 | 测试红线触发 | 20min | T3.4.7 | ❌ |

#### 实现要点

1. **红线配置**（T3.4.1）：
   ```python
   @dataclass
   class RedLineConfig:
       min_valid_posts: int = 1500
       min_cache_hit_rate: float = 0.60
       max_duplicate_rate: float = 0.20
       min_precision_at_50: float = 0.60
   ```

2. **4 条红线**：
   - **红线 1**: `valid_posts_24h < 1500` → 提高阈值 +0.1（保守模式）
   - **红线 2**: `cache_hit_rate < 60%` → 触发补抓任务（提升抓取频率）
   - **红线 3**: `duplicate_rate > 20%` → 降低 MinHash 阈值到 0.80（改进去重）
   - **红线 4**: `precision_at_50 < 0.6` → 阈值 +0.05（提高阈值）

3. **降级策略实现**：
   ```python
   def check_red_lines(metrics: DailyMetrics) -> List[str]:
       """检查红线，返回触发的红线列表"""
       triggered = []

       if metrics.valid_posts_24h < 1500:
           triggered.append("RED_LINE_1: 保守模式")
           # 提高阈值 +0.1
           update_threshold(current_threshold + 0.1)

       if metrics.cache_hit_rate < 0.60:
           triggered.append("RED_LINE_2: 提升抓取频率")
           # 触发补抓任务
           trigger_补抓_task()

       # ... 其他红线

       return triggered
   ```

#### 验收标准

- ✅ 红线触发自动降级
- ✅ 降级策略生效（日志记录）
- ✅ 测试覆盖 4 条红线

---

### T3.5: 改造报告模版

**目标**: 添加行动位到报告模版
**预估时间**: 3 小时
**依赖**: T2.10（去重集成）
**优先级**: P1（产品价值）

#### 子任务

| 任务 | 描述 | 预估时间 | 依赖 | 可并行 |
|------|------|----------|------|--------|
| T3.5.1 | 创建 `OpportunityReport` 数据类 | 15min | - | ✅ |
| T3.5.2 | 实现 `problem_definition` 提取 | 20min | T3.5.1 | ❌ |
| T3.5.3 | 实现 `evidence_chain` 构建 | 25min | T3.5.1 | ✅ |
| T3.5.4 | 实现 `suggested_actions` 生成 | 20min | T3.5.2 | ❌ |
| T3.5.5 | 实现评分函数（confidence/urgency/product_fit） | 30min | T3.5.1 | ✅ |
| T3.5.6 | 实现 `priority` 计算 | 10min | T3.5.5 | ❌ |
| T3.5.7 | 更新 `AnalysisResult` 结构 | 15min | T3.5.1-T3.5.6 | ❌ |
| T3.5.8 | 测试报告生成 | 25min | T3.5.7 | ❌ |

#### 实现要点

1. **OpportunityReport 数据类**（T3.5.1）：
   ```python
   @dataclass
   class OpportunityReport:
       problem_definition: str
       evidence_chain: List[Dict[str, Any]]  # 2-3 条证据
       suggested_actions: List[str]
       confidence: float  # 0-1
       urgency: float  # 0-1
       product_fit: float  # 0-1
       priority: float  # confidence × urgency × product_fit
   ```

2. **problem_definition 提取**（T3.5.2）：
   - 从机会信号的 `summary` 字段提取
   - 模板：`"用户需要 {功能}，但现有方案 {痛点}"`

3. **evidence_chain 构建**（T3.5.3）：
   - 选择 Top 2-3 条最相关的帖子
   - 字段：`post_id`, `title`, `url`, `score`, `snippet`

4. **suggested_actions 生成**（T3.5.4）：
   - 模板化建议：
     - "调研用户需求：{problem_definition}"
     - "验证市场规模：约 {potential_users} 个潜在用户"
     - "设计 MVP：{功能} 的最小可行产品"

5. **评分函数**（T3.5.5）：
   - `confidence`: 基于信号强度（关键词匹配度、分数）
   - `urgency`: 基于时间关键词（urgent, asap, now）
   - `product_fit`: 基于产品相关性（关键词匹配度）

#### 验收标准

- ✅ 报告包含行动位（problem_definition, evidence_chain, suggested_actions）
- ✅ 优先级计算正确（priority = confidence × urgency × product_fit）
- ✅ 测试覆盖所有字段

---

### T3.6: 集成行动位到 API

**目标**: 在 API 和前端展示行动位
**预估时间**: 2 小时
**依赖**: T3.5（报告模版）
**优先级**: P1（前后端集成）

#### 子任务

| 任务 | 描述 | 预估时间 | 依赖 | 可并行 |
|------|------|----------|------|--------|
| T3.6.1 | 更新 `AnalysisResult` Schema | 15min | T3.5 | ❌ |
| T3.6.2 | 更新 `/analyze` API 响应 | 15min | T3.6.1 | ❌ |
| T3.6.3 | 前端：创建 `ActionItem` 组件 | 30min | T3.6.2 | ❌ |
| T3.6.4 | 前端：实现证据链链接 | 15min | T3.6.3 | ❌ |
| T3.6.5 | 前端：实现优先级星级展示 | 15min | T3.6.3 | ✅ |
| T3.6.6 | 前端：集成到分析结果页面 | 15min | T3.6.3-T3.6.5 | ❌ |
| T3.6.7 | 测试前后端集成 | 15min | T3.6.6 | ❌ |

#### 实现要点

1. **API Schema 更新**（T3.6.1）：
   ```python
   class AnalysisResultSchema(BaseModel):
       insights: Dict[str, List[Dict[str, Any]]]
       sources: Dict[str, Any]
       report_html: str
       action_items: List[OpportunityReportSchema]  # 新增
   ```

2. **前端 ActionItem 组件**（T3.6.3）：
   ```tsx
   interface ActionItemProps {
       problemDefinition: string;
       evidenceChain: Evidence[];
       suggestedActions: string[];
       priority: number;
   }

   const ActionItem: React.FC<ActionItemProps> = ({ ... }) => {
       return (
           <Card>
               <h3>{problemDefinition}</h3>
               <EvidenceChain items={evidenceChain} />
               <ActionList actions={suggestedActions} />
               <PriorityStars value={priority} />
           </Card>
       );
   };
   ```

3. **优先级星级展示**（T3.6.5）：
   - 5 星制：`priority ∈ [0, 1]` → `stars ∈ [0, 5]`
   - 映射：`stars = Math.round(priority * 5)`

#### 验收标准

- ✅ API 返回 `action_items` 字段
- ✅ 前端正确展示问题定义、证据链、建议动作、优先级
- ✅ 证据链可点击跳转到 Reddit 原帖

---

## 📊 执行顺序与并行策略

### 串行任务（必须按顺序执行）

1. **T3.1 → T3.2**：标注数据集 → 阈值优化
2. **T3.3 → T3.4**：每日跑分 → 红线检查
3. **T3.5 → T3.6**：报告模版 → API 集成

### 可并行任务

- **T3.1 + T3.3**：标注数据集 + 每日跑分（无依赖）
- **T3.1 + T3.5**：标注数据集 + 报告模版（无依赖）
- **T3.3 + T3.5**：每日跑分 + 报告模版（无依赖）

### 推荐执行顺序

```
Day 1: T3.1 (抽样标注) + T3.3 (每日跑分)
Day 2: T3.1.5 (用户标注，3h) + T3.5 (报告模版)
Day 3: T3.2 (阈值优化) + T3.4 (红线检查)
Day 4: T3.6 (API 集成) + 测试
```

---

## ✅ 验收标准总结

| 任务 | 验收标准 |
|------|----------|
| T3.1 | 500 条样本已标注，数据保存成功 |
| T3.2 | 最优阈值 Precision@50 ≥0.6，配置文件已更新 |
| T3.3 | 每日自动生成报告，CSV 格式正确 |
| T3.4 | 红线触发自动降级，降级策略生效 |
| T3.5 | 报告包含行动位，优先级计算正确 |
| T3.6 | API 返回行动位，前端正确展示 |

---

## 🚀 下一步

Phase 3 完成后，进入 **Phase 4: 迭代与延伸**（T4.1-T4.3）：
- T4.1: 生成两周迭代总结
- T4.2: 实现轻量 NER（spaCy）
- T4.3: 实现趋势分析（7/14/30 天）

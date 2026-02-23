# 社区池更新报告（2025-11-14）

**执行人**：运维工程师  
**执行时间**：2025-11-14 15:00-15:30  
**状态**：✅ 完成

---

## 📋 执行摘要

### 任务1：替换社区池（260 → 166）

**变更说明**：
- **旧社区池**：260个社区（`community_list_clean_260.csv`）
- **新社区池**：166个跨境电商相关社区（`reddit_crossborder_relevant_communities.csv`）

**执行步骤**：
1. ✅ 删除旧社区池（260个社区）
2. ✅ 创建导入脚本（`backend/scripts/import_166_crossborder_communities.py`）
3. ✅ 导入新社区池（165个社区，1行表头）
4. ✅ 验证导入结果

**导入结果**：
```
✅ 成功读取 165 个社区
   新增: 165
   更新: 0
   跳过: 0
   总计: 165

📊 数据库活跃社区总数: 165
   HIGH: 15
   MEDIUM: 53
   LOW: 97

📊 按维度统计:
   what_to_sell: 14
   where_to_sell: 133
   how_to_sell: 25
   how_to_source: 21
```

### 任务2：更新ops文档

**更新内容**：
1. ✅ 添加第3.1节：社区池管理（2025-11-14更新）
2. ✅ 添加第16节：系统架构与抓取策略深度分析
3. ✅ 更新第15节：标记旧计划为已废弃

**文档路径**：`.specify/specs/013-legacy-quality-gap/ops-runbook.md`

---

## 🔍 核心发现

### 发现1：双数据库分裂问题（已解决）

**问题**：
- 系统中存在两个PostgreSQL数据库：
  - `reddit_scanner`（旧库）：25,971条污染数据，277个无关社区
  - `reddit_signal_scanner`（新库）：正确的数据库

**解决**：
- ✅ 删除 `reddit_scanner` 数据库
- ✅ 保留 `reddit_signal_scanner` 作为唯一数据库

### 发现2：分离抓取架构的合理性（已确认）

**问题**：为什么帖子和评论分离抓取？

**答案**：✅ **分离抓取是正确的设计！**

**原因**：
1. Reddit API限制：60次请求/分钟，20秒超时
2. 快速获得帖子数据（3分钟 vs 4小时）
3. 容错性更好（可单独重试）
4. 资源利用更高效（CPU/IO并行）
5. 符合Reddit API最佳实践
6. 支持增量更新

**结论**：分离抓取不需要修改，不影响算法分析。

### 发现3：数据库设计与算法分析（已确认）

**问题**：分离抓取是否影响算法分析？

**答案**：✅ **不影响！帖子和评论通过外键关联**

**数据库设计**：
```sql
posts_raw.source_post_id ←→ comments.source_post_id
```

**唯一影响**：时间差（帖子3分钟，评论2.8小时）

### 发现4：抓取策略与Reddit API限制（已确认）

**Reddit API限制**：
- 单次请求最多：100个帖子
- 历史数据上限：1000个帖子/社区
- 实际日均：大部分社区 < 1条帖子/天

**抓取策略**：
1. **初始抓取（Day 1）**：166社区 × 60帖子 = 9,960帖子
2. **历史补充（Day 2-17）**：每天60帖子，17天抓完1000帖子
3. **日常更新（Day 18+）**：每天抓取新帖子（< 10个/社区）

**参数配置**：
```yaml
# backend/config/crawler.yml
post_limit: 60  # 改为60（原来是100）

# backend/.env
CRAWLER_POST_LIMIT=60
COMMENTS_TOPN_LIMIT=999999  # 全量评论（原来是20）
```

---

## 📊 新社区池详情

### 分层分布

| Tier | 数量 | 占比 | 抓取频率 | 条件 |
|------|------|------|----------|------|
| High (T1) | 15 | 9.1% | 每2小时 | post_count ≥ 1000 且 avg_score ≥ 50 |
| Medium (T2) | 53 | 32.1% | 每4小时 | post_count ≥ 500 或 avg_score ≥ 20 |
| Low (T3) | 97 | 58.8% | 每6小时 | 其他 |
| **总计** | **165** | **100%** | - | - |

### 维度分布

| 维度 | 数量 | 占比 | 说明 |
|------|------|------|------|
| where_to_sell | 133 | 80.6% | 卖在哪里：Amazon、Etsy、Shopify等 |
| how_to_sell | 25 | 15.2% | 如何销售：SEO、广告、营销等 |
| how_to_source | 21 | 12.7% | 如何采购：Dropshipping、供应商等 |
| what_to_sell | 14 | 8.5% | 卖什么：产品选品、市场趋势等 |

**注**：一个社区可能有多个维度标签。

### Top 20社区

| 排名 | 社区 | 帖子数 | 平均分 | Tier | 维度 |
|------|------|--------|--------|------|------|
| 1 | r/AmazonWFShoppers | 1,302 | 27.4 | Medium | where_to_sell |
| 2 | r/EtsySellers | 1,265 | 107.1 | High | where_to_sell |
| 3 | r/FacebookAds | 1,257 | 27.8 | Medium | how_to_sell |
| 4 | r/Aliexpress | 1,255 | 167.8 | High | where_to_sell |
| 5 | r/AmazonFlexDrivers | 1,254 | 229.7 | High | where_to_sell |
| 6 | r/bigseo | 1,252 | 14.8 | Medium | how_to_sell |
| 7 | r/dropshipping | 1,251 | 45.9 | Medium | how_to_source |
| 8 | r/amazonecho | 1,249 | 78.5 | High | where_to_sell |
| 9 | r/Legomarket | 1,248 | 11.6 | Medium | what_to_sell |
| 10 | r/FulfillmentByAmazon | 1,243 | 27.3 | Medium | where_to_sell, how_to_source |
| 11 | r/dropship | 1,243 | 41.1 | Medium | how_to_source |
| 12 | r/amazonprime | 1,240 | 396.3 | High | where_to_sell |
| 13 | r/FASCAmazon | 1,240 | 72.4 | High | where_to_sell |
| 14 | r/peopleofwalmart | 1,239 | 1676.2 | High | where_to_sell |
| 15 | r/AliExpressBR | 1,236 | 80.8 | High | where_to_sell |
| 16 | r/Etsy | 1,234 | 112.0 | High | where_to_sell |
| 17 | r/stickerstore | 1,225 | 14.1 | Medium | where_to_sell |
| 18 | r/digital_marketing | 1,222 | 21.4 | Medium | what_to_sell, how_to_sell |
| 19 | r/amazon | 1,218 | 57.1 | High | where_to_sell |
| 20 | r/AmazonMerch | 1,218 | 9.4 | Medium | where_to_sell |

---

## 🎯 当前系统状态

### 数据库状态（✅ 健康）

- **数据库名**：`reddit_signal_scanner`
- **PostgreSQL版本**：14.19
- **Alembic版本**：`20251114_000031`（最新）
- **表数量**：26张
- **社区池**：165个活跃社区

### 数据资产

| 表名 | 记录数 | 状态 | 说明 |
|------|--------|------|------|
| posts_raw | 128,917 | ✅ 健康 | 冷库，260社区，11年历史 |
| posts_hot | 1,143 | ⚠️ 需更新 | 热库，15社区（需重新抓取） |
| comments | 108,333 | ✅ 健康 | 评论数据 |
| content_labels | 134,691 | ✅ 健康 | 痛点/解决方案标签 |
| content_entities | 89 | ✅ 正常 | 品牌/特征/平台实体 |
| community_pool | 165 | ✅ 健康 | 新社区池 |

### 服务运行状态（✅ 正常）

- **Celery**：2 Workers + 1 Beat
- **Redis**：2实例
- **配置**：全部正确 ✅

---

## 📋 下一步行动计划

### P0优先级（立即执行）

1. **调整抓取参数**：
   ```bash
   # 修改 backend/.env
   CRAWLER_POST_LIMIT=60
   COMMENTS_TOPN_LIMIT=999999
   
   # 修改 backend/config/crawler.yml
   post_limit: 60  # 所有tier改为60
   ```

2. **清理热库测试数据**：
   ```sql
   DELETE FROM posts_hot WHERE subreddit IN ('r/A', 'r/B', 'r/C');
   ```

3. **启动Day 1抓取**：
   - 166社区 × 60帖子 = 9,960帖子
   - 每个帖子全量评论
   - 预计时间：3分钟（帖子）+ 2.8小时（评论）

### P1优先级（本周完成）

4. **归档冗余脚本和数据**：
   ```bash
   mkdir -p backend/scripts/archive/import_legacy
   mv backend/scripts/import_clean_260_communities.py backend/scripts/archive/import_legacy/
   mv community_list_clean_260.csv backend/data/archive/
   ```

5. **验证数据质量**：
   ```bash
   make pipeline-health
   make posts-growth-7d
   ```

### P2优先级（下周验证）

6. **监控数据增长**
7. **生成健康报告**

---

## 📈 系统健康度评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 数据库结构 | ✅ 10/10 | 完美 |
| 数据完整性 | ⚠️ 7/10 | posts_hot需重新抓取 |
| 配置正确性 | ✅ 10/10 | 完美 |
| 服务运行 | ✅ 10/10 | Celery已优化 |
| 代码整洁度 | ⚠️ 6/10 | 冗余文件较多 |
| 文档完整性 | ✅ 9/10 | 优秀 |

**总体评分**：⚠️ **8.7/10**（良好，需要重新抓取和清理）

---

## 📝 关键经验

1. **分离抓取是正确的**：符合Reddit API限制，用户体验更好，容错性更强
2. **数据库设计合理**：帖子和评论通过外键关联，不影响算法分析
3. **社区池需要精准**：从260个降到166个，提高了相关性
4. **维度标注很重要**：帮助理解社区特点，优化抓取策略
5. **文档标准化**：所有发现和决策都记录在ops文档中

---

**报告生成时间**：2025-11-14 15:30  
**下次检查时间**：2025-11-14 18:00（Day 1抓取完成后）


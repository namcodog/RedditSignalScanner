# DEPRECATED

> 本文档已归档，不再作为当前口径。请以 docs/2025-10-10-文档阅读指南.md 指定的文档为准。

# 开发需求文档：JSONL 批量入库与水位线同步工具

**日期**: 2025-12-01  
**作者**: 架构组 (Key)  
**状态**: Draft (待评审)  
**目标**: 构建标准化工具，将 `crawl_incremental.py` (System B) 抓取的离线数据合规地导入生产数据库，并平滑移交给 Celery (System A) 接管。

---

## 1. 背景与痛点 (Context)

### 1.1 现状
系统存在两套平行的数据获取机制：
*   **System A (Celery)**: 生产环境的常驻服务，负责高频、增量抓取。依赖数据库中的 `last_crawled_at` 水位线。
*   **System B (脚本)**: `scripts/crawl_incremental.py`，用于快速抓取大量历史数据（Backfill），输出为本地 JSONL 文件。

### 1.2 问题
目前缺失一个**标准化的导入工具** (`Ingest Tool`)。
*   System B 抓取的数据（JSONL）无法自动进入数据库。
*   历史数据即使被（手动）导入，往往没有正确更新 `community_cache` 的水位线。
*   **后果**: Celery (System A) 不知道历史数据已补齐，可能会重复抓取旧数据，或因水位线过旧而触发大量无效 API 请求，甚至导致数据断层。

---

## 2. 需求目标 (Requirements)

开发一个 CLI 脚本 `backend/scripts/ingest_jsonl.py`，实现以下功能：

### 2.1 核心功能
1.  **读取**: 支持流式读取大型 JSONL 文件（避免内存爆炸）。
2.  **过滤**: **强制复用** `IncrementalCrawler` 中的垃圾过滤逻辑 (`_is_spam_post` 和黑名单)，确保入库数据干净。
3.  **写入**: 调用 `IncrementalCrawler.ingest_posts_batch` 实现冷热双写 (Dual Write)。
4.  **同步**: **关键一步** —— 统计入库数据的最大 `created_utc`，并更新 `community_cache` 表的 `last_seen_created_at` (水位线)。

### 2.2 非功能需求
*   **性能**: 支持批量提交 (Batch Commit)，建议 batch_size=1000。
*   **幂等性**: 重复运行脚本不应导致数据重复或报错（依赖数据库的 UNIQUE 约束和 SCD2 逻辑）。
*   **可观测性**: 输出详细的进度条 (tqdm) 和统计报告 (New/Updated/Skipped/Spam)。

---

## 3. 技术设计 (Technical Design)

### 3.1 架构位置
```mermaid
[crawl_incremental.py] --(产生)--> [file.jsonl] 
                                      |
                                      v
                             [ingest_jsonl.py] <--(本需求)
                                      |
                                      +--> 调用 Service: IncrementalCrawler
                                                |
                                                +--> [Database] (更新 Post & Watermark)
```

### 3.2 接口设计 (CLI Interface)
```bash
python backend/scripts/ingest_jsonl.py \
  --file backend/data/reddit_corpus/ecommerce.jsonl \
  --community r/ecommerce \
  --batch-size 500 \
  --update-watermark  # 显式开关，决定是否推进水位线
```

### 3.3 核心逻辑伪代码
```python
async def main(file_path, community_name, update_watermark):
    # 1. 初始化服务
    crawler = IncrementalCrawler(db_session, reddit_client)
    
    # 2. 流式读取 JSONL
    batch = []
    max_created_at = 0
    
    for line in file:
        post_data = json.loads(line)
        post = RedditPost(**post_data)  # 转换为标准模型
        
        # 3. 过滤 (复用现有逻辑)
        if crawler._is_spam_post(post):
            continue
            
        batch.append(post)
        
        # 4. 批量写入
        if len(batch) >= 500:
            await crawler.ingest_posts_batch(community_name, batch)
            # 更新 max_created_at
            batch = []
            
    # 5. 处理剩余 batch
    if batch:
        await crawler.ingest_posts_batch(...)
        
    # 6. 更新水位线 (The Handover)
    if update_watermark and max_created_at > current_watermark:
        await crawler._update_watermark(community_name, ..., max_created_at)
        print(f"✅ 水位线已推进至 {max_created_at}，Celery 将从此接手。")
```

---

## 4. 验收标准 (Acceptance Criteria)

1.  **垃圾拦截验证**:
    *   构造一个包含 "Welcome to AmazonFC" 的 JSONL 文件，运行脚本后，数据库中**不应**出现该垃圾贴。
2.  **水位线同步验证**:
    *   导入一批 `created_at` 为 "2025-11-28" 的数据后，查询 `community_cache`表，该社区的 `last_seen_created_at` 应更新为 "2025-11-28"。
3.  **Celery 衔接验证**:
    *   在导入完成后，观察 Celery 日志。Celery 应从 2025-11-28 之后开始抓取，而不是从头开始。

---

## 5. 风险评估 (Risk Assessment)

*   **风险**: 如果 JSONL 文件里的数据是乱序的，更新水位线时可能会取错最大值。
    *   **对策**: 脚本内部必须维护一个 `global_max_created_at` 变量，遍历所有数据后取最大值，而不是简单取最后一条。
*   **风险**: 数据库写入过快导致 IO 飙升。
    *   **对策**: 默认 `batch-size` 设为 500，保留流控能力。

---

**批准请回复**: "Approved" 或提出修改意见。

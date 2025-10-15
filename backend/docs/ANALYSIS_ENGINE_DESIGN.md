# Analysis Engine Design (Day 5 Draft)

Status: Drafted on Day 5 to unblock Phase 3 implementation. Derived directly
from `docs/PRD/PRD-03-分析引擎.md` and ADR-003.

---

## 1. Objectives

- Honour the 5-minute SLA (`PRD-03 §1.1`): generate a complete report within
  270 seconds using a cache-first approach.
- Implement the four-step pipeline described in `PRD-03 §2`:
  1. **社区发现** (Community Discovery)
  2. **并行数据采集** (Data Collection)
  3. **信号提取** (Signal Extraction)
  4. **智能排序输出** (Ranking & Report generation)
- Provide deterministic, testable heuristics for Phase 1 while leaving hooks
  for future ML/TF-IDF upgrades.

---

## 2. High-Level Architecture

```
┌────────────────────────────┐
│ TaskSummary (product text) │
└──────────────┬─────────────┘
               │
               ▼
      ┌───────────────────┐
      │ Step 1: 社区发现  │
      │  • 关键词提取     │
      │  • 社区评分       │
      │  • 多样性约束     │
      └─────────┬─────────┘
                │ List[CommunityProfile]
                ▼
      ┌───────────────────┐
      │ Step 2: 数据采集  │
      │  • 缓存命中优先   │
      │  • 并发采集       │
      │  • 数据清洗       │
      └─────────┬─────────┘
                │ List[CollectedCommunity]
                ▼
      ┌───────────────────┐
      │ Step 3: 信号提取  │
      │  • 痛点识别       │
      │  • 竞品识别       │
      │  • 机会发现       │
      └─────────┬─────────┘
                │ Dict[str, List[Signal]]
                ▼
      ┌───────────────────┐
      │ Step 4: 排序输出  │
      │  • 相关性打分     │
      │  • 报告渲染       │
      └─────────┬─────────┘
                │ AnalysisResult
                ▼
        Analysis / Report ORM
```

---

## 3. Module Layout

| Path                                             | Responsibility                                                  |
|--------------------------------------------------|-----------------------------------------------------------------|
| `app/services/analysis/community_discovery.py`   | Step 1 keyword extraction, scoring, diversity selection         |
| `app/services/analysis/data_collection.py` (TBD) | Step 2 async fetch + cache wrappers                             |
| `app/services/analysis/signal_extraction.py` (TBD)| Step 3 heuristics + sentiment/competitor/opportunity synthesis |
| `app/services/analysis/reporting.py` (TBD)       | Step 4 ranking, HTML/JSON report builders                       |
| `app/services/analysis_engine.py`                | Orchestrator combining the four stages (already present)        |

Each module exposes an async function returning typed payloads defined in
`app/schemas/analysis.py` or Day 6+ additions.

---

## 4. Configuration Blueprint (`backend/config/analysis_engine.yml.example`)

```yaml
engine:
  version: "1.0"

  community_discovery:
    max_communities: 30
    default_communities: 20
    min_communities: 10
    cache_thresholds:
      aggressive: 0.80   # hit rate >= 80%
      balanced: 0.60     # 60% <= hit rate < 80%
    weights:
      description_match: 0.40
      activity_level: 0.30
      quality_score: 0.30
    diversity:
      max_per_category: 5
      minimum_categories: 4

  data_collection:
    concurrency: 10
    request_timeout_seconds: 30
    retry_attempts: 3
    cache_ttl_seconds: 3600
    max_posts_per_community: 100

  signal_extraction:
    sentiment_negative_tokens:
      - slow
      - confusing
      - expensive
      - integration
      - support
    opportunity_positive_themes:
      - automation
      - insight
      - workflow
      - collaboration
      - report
    competitor_bank_seed: 42

  ranking:
    pain_points:
      frequency_weight: 0.4
      sentiment_weight: 0.3
      quality_weight: 0.3
    opportunities:
      relevance_weight: 0.6
      coverage_gap_weight: 0.4
    output_limits:
      max_pain_points: 10
      max_competitors: 8
      max_opportunities: 6
```

Implementation will hydrate this config via `yaml.safe_load` guarded by a Pydantic
settings model in Day 6.

---

## 5. Data Contracts

### 5.1 Step 1 (Community Discovery)

- Input: `product_description: str`, `cache_hit_rate: float`
- Output: `List[Community]` (new schema with fields `name`, `categories`,
  `daily_posts`, `relevance_score`)
- Error handling: raise `ValueError` if input text < 10 chars (aligns with
  `TaskCreate` validation).

### 5.2 Step 2 (Data Collection)

- Input: `List[Community]`
- Output: `List[CollectedCommunity]` containing raw post summaries and cache hit/miss counts.
- Observability: record `analysis_duration_seconds`, `cache_hit_rate`,
  `reddit_api_calls` for PRD KPI reporting.

### 5.3 Step 3 (Signal Extraction)

- Input: aggregated posts, description keywords.
- Output: dictionaries for `pain_points`, `competitors`, `opportunities` matching `Analysis` JSON schema.

### 5.4 Step 4 (Reporting)

- Input: Step 3 structures + metrics.
- Output: HTML report and metadata (already partially implemented in
  `analysis_engine.py`).

---

## 6. Execution Timeline (Day 5–Day 9)

| Day | Focus (Backend A)                                | Deliverables                                                 |
|-----|---------------------------------------------------|--------------------------------------------------------------|
| 5   | Design + Step 1 skeleton                          | This document, config template, placeholder module/tests     |
| 6   | Implement Step 1 fully (关键词提取 + 多样性)       | Functional `discover_communities`, unit tests                |
| 7   | Step 2 data collection (cache-first orchestrator) | Async fetch stubs, cache integration, tests                  |
| 8   | Step 3 signal extraction                          | Pain/competitor/opportunity heuristics + coverage metrics    |
| 9   | Step 4 integration + performance validation       | Full pipeline, profiling, config tuning                      |

---

## 7. Testing Strategy

- **Unit Tests**: Each module receives direct tests (Day 5 seeds `test_community_discovery.py`).
- **Integration Tests**: Day 8 adds pipeline tests mocking Reddit API/cache.
- **Performance Harness**: By Day 9, run synthetic workloads verifying runtime
  (< 270s) and cache hit rate (> 60%).

---

## 8. Observability & Metrics

- Emit structured logs per step: `step`, `duration_ms`, `cache_hit_rate`,
  `communities_selected`.
- Record counters for retries and cache misses (feeds `reports/phase-log`).
- Hook into `TaskStatusCache` to push progress milestones: `"community_discovery"`,
  `"data_collection"`, etc. (TODO: align with PRD fallback schema).

---

## 9. Risks & Mitigations

| Risk                                 | Mitigation                                                         |
|--------------------------------------|--------------------------------------------------------------------|
| TF-IDF stub too naive                | Provide deterministic heuristic now; replace with sklearn TF-IDF on Day 6 |
| Cache miss leads to long runtimes    | Enforce `max_posts_per_community` and concurrency limits           |
| Frontend contract drift              | Document SSE progress steps + add integration tests                |
| Config sprawl                        | Centralise under `analysis_engine.yml` and load via typed settings |

---

## 10. Next Actions (Day 6 Kick-off)

1. Flesh out `extract_keywords` using sklearn TF-IDF with fallback heuristics.
2. Populate community catalogue from config/fixture (500+ entries).
3. Wire config loader + dependency injection into `analysis_engine.py`.
4. Update task status progress events to reflect new step names and percentages.


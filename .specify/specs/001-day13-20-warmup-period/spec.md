# Feature Specification: Day 13-20 预热期与社区池扩展

**Feature ID**: 001-day13-20-warmup-period  
**Status**: Planning  
**Created**: 2025-10-15  
**Owner**: Lead  
**PRD Reference**: PRD-09 动态社区池与预热期实施计划

---

## Executive Summary

实施为期 7 天的预热期（Day 13-19），通过后台爬虫系统预先缓存 Reddit 数据，确保正式上线时（Day 20）能够兑现"5 分钟分析承诺"。预热期包括种子社区爬取、内部测试、Beta 用户测试和数据积累，最终达到 90%+ 缓存命中率。

---

## Problem Statement

### Current State
- Day 1-12: 核心功能开发完成
- 缓存为空状态，首次分析需要大量实时 API 调用
- 无法满足"5 分钟承诺"（需要 90% 缓存命中率）
- 社区池规模未知，覆盖率无法保证

### Desired State
- Day 20 上线时：250+ 社区已缓存
- 缓存命中率 > 90%
- 平均分析耗时 < 3 分钟
- 用户满意度 > 4.0/5.0

### Success Metrics
- 社区池规模: 250+ 社区
- 缓存帖子数: 25,000+ 帖子
- 缓存命中率: 92%+
- API 调用: < 60 次/分钟（峰值）
- 系统正常运行时间: > 99.5%

---

## User Stories

### US-001: 种子社区预热（Day 13-14）
**As a** System Administrator  
**I want** 后台爬虫自动爬取 100 个种子社区  
**So that** 系统启动时已有基础缓存数据

**Acceptance Criteria**:
- [ ] 100 个种子社区列表已定义（来自 Git 仓库）
- [ ] Celery Beat 定时任务每 2 小时爬取一次
- [ ] 每个社区缓存 100 个帖子（top/week）
- [ ] 爬取速率 < 60 次/分钟
- [ ] 缓存数据存入 Redis，元数据存入 `community_cache` 表
- [ ] Day 14 结束时缓存命中率 100%（种子社区）

### US-002: 内部测试与社区发现（Day 15-16）
**As a** Internal Tester  
**I want** 使用真实产品描述进行分析测试  
**So that** 系统能够发现并扩展新社区

**Acceptance Criteria**:
- [ ] 5-10 个内部测试账号已创建
- [ ] 测试用户可提交产品描述并获得分析报告
- [ ] 系统自动从测试任务中发现新社区（TF-IDF + 搜索）
- [ ] 发现的社区记录到 `discovered_communities` 表
- [ ] Admin 可审核并批准新社区
- [ ] 批准后自动触发首次爬取
- [ ] Day 16 结束时社区池扩展到 150 个

### US-003: Beta 用户测试（Day 17-18）
**As a** Beta User  
**I want** 免费使用系统并提供反馈  
**So that** 帮助改进产品质量

**Acceptance Criteria**:
- [ ] 20-50 个 Beta 用户注册
- [ ] Beta 用户可正常使用所有功能
- [ ] 系统监控 API 调用频率（< 55 次/分钟）
- [ ] 缓存命中率 > 85%
- [ ] 平均分析耗时 < 3 分钟
- [ ] 用户满意度调查 > 4.0/5.0
- [ ] Day 18 结束时社区池 200-250 个

### US-004: 自适应爬虫调整（Day 13-19）
**As a** System  
**I want** 根据缓存命中率动态调整爬虫频率  
**So that** 在节省 API 配额的同时保证缓存质量

**Acceptance Criteria**:
- [ ] 缓存命中率 > 90%: 降低频率到每 4 小时
- [ ] 缓存命中率 70-90%: 保持每 2 小时
- [ ] 缓存命中率 < 70%: 提高到每 1 小时
- [ ] API 调用监控：接近 55 次/分钟时暂停新注册
- [ ] 爬虫策略调整记录到日志

### US-005: 最终验证与上线准备（Day 19）
**As a** Lead  
**I want** 完整的系统健康检查和预热期报告  
**So that** 确认系统已准备好正式上线

**Acceptance Criteria**:
- [ ] 系统健康检查全部通过（Redis/PostgreSQL/Celery/Reddit API）
- [ ] 预热期报告生成（社区池/缓存/API 使用/用户测试/性能）
- [ ] 缓存覆盖率 > 90%
- [ ] 平均分析耗时 < 3 分钟
- [ ] 系统正常运行时间 > 99.5%
- [ ] 上线公告已准备

---

## Functional Requirements

### FR-001: 种子社区管理
- 系统应从 Git 仓库加载种子社区列表
- 支持社区优先级配置（高优先级更频繁爬取）
- 支持社区黑名单（禁用低质量社区）

### FR-002: 后台爬虫系统
- Celery Beat 定时调度爬虫任务
- Celery Worker 并发执行爬虫（concurrency=2）
- 爬虫速率限制：< 60 次/分钟
- 错误重试机制：3 次重试，指数退避

### FR-003: 社区发现机制
- 从用户产品描述中提取关键词（TF-IDF）
- 使用 Reddit Search API 发现相关社区
- 统计社区出现频率，记录到待审核表
- Admin 审核界面（批准/拒绝/待定）

### FR-004: 缓存管理
- Redis 存储帖子数据（TTL 24 小时）
- PostgreSQL `community_cache` 表存储元数据
- 缓存失效策略：超过 24 小时自动刷新
- 缓存命中率统计与监控

### FR-005: 监控与告警
- API 调用频率监控（每分钟统计）
- 缓存命中率监控（每小时统计）
- 系统资源监控（内存/CPU/磁盘）
- 告警规则：API > 55 次/分钟、缓存 < 70%、资源 > 90%

---

## Non-Functional Requirements

### NFR-001: Performance
- 爬虫任务执行时间: < 2 分钟（100 个社区）
- 缓存写入延迟: < 100ms
- 社区发现延迟: < 5 秒

### NFR-002: Scalability
- 支持社区池扩展到 500+ 社区
- 支持 100 并发用户测试
- 支持每日 10,000+ API 调用

### NFR-003: Reliability
- 爬虫失败自动重试（3 次）
- 系统正常运行时间 > 99.5%
- 数据一致性保证（Redis + PostgreSQL）

### NFR-004: Compliance
- 严格遵守 Reddit API 60 次/分钟限制
- 使用 OAuth2 认证
- 正确的 User-Agent 头
- 缓存数据仅用于分析，不转售

---

## Technical Constraints

### TC-001: Reddit API Limits
- 60 requests/minute (hard limit)
- OAuth2 authentication required
- User-Agent: "RedditSignalScanner/1.0"

### TC-002: Infrastructure
- Redis: 单实例，内存 < 2GB
- PostgreSQL: 单实例，连接池 20
- Celery: 2 workers, concurrency=2

### TC-003: Data Retention
- Redis 缓存: 24 小时 TTL
- PostgreSQL 历史: 永久保留
- 日志: 7 天滚动

---

## Dependencies

### Internal Dependencies
- PRD-01: 数据模型（`community_cache` 表）
- PRD-03: 分析引擎（社区发现算法）
- PRD-04: 任务系统（Celery 配置）
- PRD-07: Admin 后台（社区审核界面）

### External Dependencies
- Reddit API: OAuth2 认证 + 数据访问
- Git 仓库: 种子社区列表
- Redis: 缓存存储
- PostgreSQL: 元数据存储

---

## Out of Scope

### Not Included in This Feature
- ❌ 实时爬虫（仅定时爬虫）
- ❌ 用户自定义社区（仅 Admin 审核）
- ❌ 多语言支持（仅英文社区）
- ❌ 历史数据分析（仅最近 7 天）
- ❌ 付费功能（Beta 期间全部免费）

---

## Review & Acceptance Checklist

### Specification Quality
- [ ] All user stories have clear acceptance criteria
- [ ] Functional requirements are testable
- [ ] Non-functional requirements have measurable targets
- [ ] Dependencies are documented
- [ ] Out of scope is clearly defined

### PRD Alignment
- [ ] All requirements trace back to PRD-09
- [ ] No requirements contradict existing PRDs
- [ ] Constitution principles are followed

### Stakeholder Review
- [ ] Lead approved
- [ ] Backend Agents reviewed
- [ ] QA Agent reviewed
- [ ] No unresolved questions

---

**Next Steps**: 
1. Create implementation plan (`/speckit.plan`)
2. Generate task breakdown (`/speckit.tasks`)
3. Execute implementation (`/speckit.implement`)


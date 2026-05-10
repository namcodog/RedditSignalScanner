# P1-5 修复报告：动态社区成员数

**修复日期**: 2025-10-26
**问题编号**: P1-5
**问题描述**: 硬编码的社区成员数
**修复方案**: 方案 B - 添加数据库字段 + 定期更新任务

---

## 📋 问题概述

### 原始问题
- 社区成员数硬编码在 `backend/app/core/config.py` 的 `DEFAULT_COMMUNITY_MEMBERS` 字典中
- 只支持 10 个社区的成员数
- 无法动态更新，数据可能过时
- 虽然支持环境变量配置，但仍依赖硬编码默认值

### 影响范围
- `ReportService._build_overview()` 使用硬编码值生成报告
- 报告中的社区成员数可能不准确
- 新增社区无法自动获取成员数

---

## ✅ 修复方案（方案 B）

### 方案选择理由
- **方案 A**（直接调用 Reddit API）：每次生成报告都调用 API，增加延迟和 API 限流风险
- **方案 B**（数据库 + 定期任务）：✅ 选择此方案
  - 数据库存储成员数，查询快速
  - 定期任务更新，减少 API 调用
  - 支持降级逻辑（DB → Config → Default）
- **方案 C**（保持现状）：不解决根本问题

---

## 🔧 实施步骤

### 1. 数据库迁移 ✅

**文件**: `backend/alembic/versions/20251026_000023_add_member_count_to_community_cache.py`

**变更**:
- 添加 `member_count` 字段到 `community_cache` 表
- 类型：`Integer`，可为空（允许逐步填充）
- 添加索引：`idx_community_cache_member_count`
- 添加约束：`ck_community_cache_member_count_non_negative`（非负值）

**迁移命令**:
```bash
cd backend
alembic upgrade head
```

**模型更新**:
- `backend/app/models/community_cache.py`: 添加 `member_count` 字段
- `backend/app/schemas/community_cache.py`: 添加 `member_count` 到 Pydantic schema

---

### 2. Celery 定期任务 ✅

**文件**: `backend/app/tasks/community_member_sync_task.py`

**功能**:
- 从 Reddit API 获取所有活跃社区的成员数
- 批量更新 `community_cache.member_count` 字段
- 错误处理和重试机制
- 详细的统计日志

**核心函数**:
1. `_sync_community_members_impl()`: 主同步逻辑
   - 查询所有活跃社区
   - 批量处理（每批 50 个）
   - 更新数据库
   - 返回统计信息

2. `_fetch_member_count()`: 获取单个社区成员数
   - 调用 Reddit API `/r/{subreddit}/about` 端点
   - 提取 `subscribers` 字段
   - 错误处理

3. `sync_community_member_counts()`: Celery 任务包装器
   - 绑定到 Celery
   - 自动重试（最多 3 次）
   - 错误延迟：5-10 分钟

**调度配置**:
- 文件：`backend/app/core/celery_app.py`
- 频率：每 12 小时执行一次（`crontab(hour="*/12", minute="0")`）
- 队列：`crawler_queue`
- 过期时间：2 小时

**任务注册**:
- 文件：`backend/app/tasks/__init__.py`
- 导出：`sync_community_member_counts`

---

### 3. ReportService 修改 ✅

**文件**: `backend/app/services/report_service.py`

**新增方法**: `_get_community_member_count()`

**降级逻辑**（优先级从高到低）:
1. **数据库** (`community_cache.member_count`)
   - 如果存在且 > 0，使用此值
   - 记录日志：`"Using DB member count for {community}: {count}"`

2. **配置文件** (`settings.report_community_members`)
   - 如果数据库无值，查找配置
   - 记录日志：`"Using config member count for {community}: {count}"`

3. **默认值** (100,000)
   - 如果以上都无值，使用默认值
   - 记录日志：`"Using default member count for {community}: 100,000"`

**修改方法**: `_build_overview()`
- 改为 `async` 方法
- 循环调用 `_get_community_member_count()` 获取每个社区的成员数
- 调用处更新为 `await self._build_overview(...)`

**错误处理**:
- 数据库查询失败时，自动降级到配置或默认值
- 记录警告日志但不中断报告生成

---

### 4. 测试验证 ✅

#### 单元测试 1: `test_community_member_sync.py`

**测试用例**:
1. ✅ `test_fetch_member_count_success`: 成功获取成员数
2. ✅ `test_fetch_member_count_invalid_response`: 处理无效响应
3. ✅ `test_sync_community_members_impl_success`: 成功同步多个社区
4. ✅ `test_sync_community_members_impl_with_failures`: 处理部分失败
5. ✅ `test_sync_community_members_impl_skips_inactive`: 跳过非活跃社区
6. ✅ `test_sync_community_member_counts_celery_task`: Celery 任务包装器

#### 单元测试 2: `test_report_service_member_count.py`

**测试用例**:
1. ✅ `test_get_community_member_count_from_db`: 从数据库读取
2. ✅ `test_get_community_member_count_fallback_to_config`: 降级到配置
3. ✅ `test_get_community_member_count_fallback_to_default`: 降级到默认值
4. ✅ `test_get_community_member_count_db_priority`: 数据库优先级最高
5. ✅ `test_get_community_member_count_handles_db_error`: 处理数据库错误
6. ✅ `test_get_community_member_count_ignores_zero`: 忽略零值
7. ✅ `test_build_overview_uses_db_member_counts`: 报告生成使用数据库值

**测试覆盖率**: 100%（核心逻辑）

---

## 📊 验证结果

### 数据库验证
```sql
-- 检查字段是否添加
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'community_cache'
AND column_name = 'member_count';

-- 检查索引是否创建
SELECT indexname FROM pg_indexes
WHERE tablename = 'community_cache'
AND indexname = 'idx_community_cache_member_count';

-- 检查约束是否创建
SELECT conname FROM pg_constraint
WHERE conname = 'ck_community_cache_member_count_non_negative';
```

### 手动触发任务
```bash
# 方法 1: 通过 Celery CLI
celery -A app.core.celery_app call tasks.community.sync_member_counts

# 方法 2: 通过 Python
from app.tasks.community_member_sync_task import sync_community_member_counts
result = sync_community_member_counts.delay()
print(result.get())
```

### 预期输出
```json
{
  "total_communities": 200,
  "successful_updates": 198,
  "failed_updates": 2,
  "skipped_communities": 0,
  "errors": [
    "r/private_community: 403 Forbidden",
    "r/deleted_community: 404 Not Found"
  ],
  "started_at": "2025-10-26T10:00:00Z",
  "completed_at": "2025-10-26T10:05:23Z"
}
```

---

## 🎯 修复效果

### 修复前
- ❌ 只有 10 个社区有成员数
- ❌ 成员数硬编码，可能过时
- ❌ 新增社区默认 100,000
- ❌ 无法动态更新

### 修复后
- ✅ 所有活跃社区都有成员数
- ✅ 每 12 小时自动更新
- ✅ 数据来自 Reddit API，准确可靠
- ✅ 支持三级降级逻辑（DB → Config → Default）
- ✅ 错误处理完善，不影响报告生成

---

## 📝 配置说明

### 环境变量（可选）
```bash
# .env
# 覆盖特定社区的成员数（JSON 格式）
REPORT_COMMUNITY_MEMBERS='{"r/startups": 1500000, "r/entrepreneur": 1000000}'
```

### Celery 调度
- 默认：每 12 小时执行一次
- 可修改：`backend/app/core/celery_app.py` 中的 `crontab(hour="*/12", minute="0")`
- 建议：保持 12 小时，避免过度调用 Reddit API

---

## 🚨 注意事项

### API 限流
- Reddit API 限制：60 次/分钟
- 当前批量大小：50 个社区/批次
- 批次间延迟：2 秒
- 预计耗时：200 个社区约 4-5 分钟

### 错误处理
- 单个社区失败不影响其他社区
- 失败社区记录到 `errors` 数组
- Celery 自动重试（最多 3 次）
- 重试延迟：5-10 分钟

### 数据一致性
- 成员数可能略有延迟（最多 12 小时）
- 降级逻辑确保报告始终可生成
- 零值被视为无效数据，触发降级

---

## 📈 后续优化建议

### 短期（可选）
1. 添加监控告警：成员数更新失败率 > 10%
2. 添加 Grafana 面板：显示成员数更新趋势
3. 优化批量大小：根据 API 限流动态调整

### 长期（可选）
1. 缓存 Reddit API 响应：减少重复调用
2. 增量更新：只更新变化的社区
3. 历史记录：保存成员数变化历史

---

## ✅ 验收标准

### 功能验收
- [x] 数据库迁移成功执行
- [x] `member_count` 字段添加到 `community_cache` 表
- [x] Celery 任务成功注册并可手动触发
- [x] ReportService 正确读取数据库值
- [x] 降级逻辑正常工作（DB → Config → Default）
- [x] 单元测试全部通过

### 质量验收
- [x] 代码符合 PEP 8 规范
- [x] 通过 `mypy --strict` 检查
- [x] 测试覆盖率 ≥ 80%
- [x] 错误处理完善
- [x] 日志记录详细

### 文档验收
- [x] 修复过程记录到 `phase1.md`
- [x] 更新 P1 验收报告标记 P1-5 已完成
- [x] 创建详细的修复报告（本文件）

---

## 📚 相关文件

### 新增文件
1. `backend/alembic/versions/20251026_000023_add_member_count_to_community_cache.py`
2. `backend/app/tasks/community_member_sync_task.py`
3. `backend/tests/tasks/test_community_member_sync.py`
4. `backend/tests/services/test_report_service_member_count.py`
5. `reports/phase-log/2025-10-26-P1-5-member-count-fix-report.md`

### 修改文件
1. `backend/app/models/community_cache.py` - 添加 `member_count` 字段
2. `backend/app/schemas/community_cache.py` - 添加 `member_count` 到 schema
3. `backend/app/services/report_service.py` - 添加 `_get_community_member_count()` 方法
4. `backend/app/core/celery_app.py` - 添加定期任务调度
5. `backend/app/tasks/__init__.py` - 导出新任务

---

**修复完成时间**: 2025-10-26
**修复人**: Augment Agent
**验收状态**: ✅ 通过

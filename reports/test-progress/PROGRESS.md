# Test Fixing Progress

## Summary
- **Before**: 68 failed, 151 passed
- **After**: 63 failed, 156 passed
- **Improvement**: 5 tests fixed, 5 more passing

## Fixed Issues

### 1. Community Name Format Constraint ✅
**Problem**: Tests using community names without `r/` prefix
**Solution**: Updated all test community names to use `r/xxx` format
**Files**:
- `tests/services/test_incremental_crawler_dedup.py`
- `tests/services/test_incremental_crawler_metrics.py`
- `tests/services/test_recrawl_scheduler.py`
- `tests/services/test_community_discovery_service.py`

### 2. API Method Name Change ✅
**Problem**: Tests calling `crawl_communities()` but method is `crawl_community_incremental()`
**Solution**: Updated all test calls
**Files**:
- `tests/services/test_incremental_crawler_metrics.py`

### 3. Missing Error Handling ✅
**Problem**: `IncrementalCrawler` not recording failure metrics on API errors
**Solution**: Added try-catch block to record `failure_hit` before re-raising
**Files**:
- `backend/app/services/incremental_crawler.py`

### 4. Wrong Column Reference ✅
**Problem**: `PostHot.id` doesn't exist (should be `source_post_id`)
**Solution**: Fixed column reference in metrics query
**Files**:
- `backend/app/services/incremental_crawler.py`

### 5. Missing Database Constraint ✅
**Problem**: `crawl_metrics` table missing unique constraint on `(metric_date, metric_hour)`
**Solution**: Added constraint via SQL
**Command**: `ALTER TABLE crawl_metrics ADD CONSTRAINT uq_crawl_metrics_date_hour UNIQUE (metric_date, metric_hour);`

## Remaining Issues (63 failures)

### High Priority
1. **Community Import Tests** (2 failures)
   - `test_import_success_creates_communities_and_history`
   - `test_import_validation_and_duplicates`
   - Status: Returns 'error' instead of 'success'

2. **Incremental Crawler Metrics** (3 failures)
   - Tests still failing after fixes
   - Need to investigate actual vs expected metrics

3. **Community Discovery** (2 failures)
   - Constraint violations on `pending_communities`

### Medium Priority
4. **Cleanup Tasks** (1 failure)
   - `test_cleanup_removes_expired_posts`

5. **Recrawl Scheduler** (1 failure)
   - `test_find_low_quality_candidates_filters_by_thresholds`

## Next Steps
1. Debug community import service error messages
2. Fix remaining constraint violations
3. Verify metrics recording logic
4. Run full test suite again
5. Update CI/CD to pass

## CI/CD Status
- Commit: `3404566d`
- Pushed to: `origin/main`
- Waiting for GitHub Actions results

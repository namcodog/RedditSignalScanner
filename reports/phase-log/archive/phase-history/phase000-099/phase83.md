# Phase 83 - Monitoring tasks routed away from analysis_queue

## Goal
Prevent monitoring tasks from occupying analysis_queue and starving label jobs.

## Changes
- Added task route for tasks.monitoring.monitor_warmup_metrics to monitoring_queue.
- Set beat schedule options for monitoring tasks to monitoring_queue:
  - monitor-warmup-metrics
  - monitor-api-calls
  - monitor-cache-health
  - monitor-crawler-health

## Tests
- python -m pytest backend/tests/tasks/test_celery_beat_schedule.py

## Expected effect
Monitoring tasks no longer land in analysis_queue; label jobs can be consumed normally.

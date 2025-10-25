"""Integration tests for Celery Beat schedule configuration.

Tests verify that:
1. Beat schedule is properly configured
2. Warmup crawler task is scheduled every 2 hours
3. Monitoring tasks are scheduled correctly
4. All scheduled tasks are registered
"""

from __future__ import annotations

import pytest
from celery.schedules import crontab  # type: ignore[import-untyped]

from app.core.celery_app import celery_app, trigger_auto_crawl_bootstrap


class TestCeleryBeatSchedule:
    """Test Celery Beat schedule configuration (PRD-09 Phase 4)."""

    def test_beat_schedule_exists(self) -> None:
        """Test that beat_schedule is configured."""
        assert hasattr(celery_app.conf, "beat_schedule")
        assert celery_app.conf.beat_schedule is not None
        assert isinstance(celery_app.conf.beat_schedule, dict)

    def test_warmup_crawler_scheduled(self) -> None:
        """Test that warmup crawler is scheduled every 2 hours."""
        schedule = celery_app.conf.beat_schedule
        
        # Check warmup crawler task exists
        assert "warmup-crawl-seed-communities" in schedule
        
        warmup_task = schedule["warmup-crawl-seed-communities"]
        assert warmup_task["task"] == "tasks.crawler.crawl_seed_communities"
        
        # Verify schedule is every 2 hours (minute=0, hour=*/2)
        task_schedule = warmup_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {0}  # At minute 0
        assert task_schedule.hour == {0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22}  # Every 2 hours

    def test_auto_crawl_incremental_runs_twice_per_hour(self) -> None:
        """Auto crawl incremental should run至少每30分钟一次，并且落在crawler_queue。"""
        schedule = celery_app.conf.beat_schedule

        assert "auto-crawl-incremental" in schedule

        crawl_task = schedule["auto-crawl-incremental"]
        assert crawl_task["task"] == "tasks.crawler.crawl_seed_communities_incremental"

        task_schedule = crawl_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {0, 30}

        options = crawl_task.get("options", {})
        assert options.get("queue") == "crawler_queue"
        assert options.get("expires") == 1800

    def test_auto_crawl_bootstrap_uses_worker_signal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bootstrap 任务通过 worker_ready signal 触发且只发送一次。"""
        sent_tasks: list[str] = []

        def fake_send_task(task_name: str, *args, **kwargs) -> None:
            sent_tasks.append(task_name)

        # reset bootstrap flag to ensure deterministic behaviour
        if hasattr(celery_app, "_auto_crawl_bootstrap_sent"):
            setattr(celery_app, "_auto_crawl_bootstrap_sent", False)
        monkeypatch.setattr(celery_app, "send_task", fake_send_task)

        first = trigger_auto_crawl_bootstrap(celery_app)
        second = trigger_auto_crawl_bootstrap(celery_app)

        assert first is True
        assert second is False
        assert sent_tasks == ["tasks.crawler.crawl_seed_communities_incremental"]
        setattr(celery_app, "_auto_crawl_bootstrap_sent", False)

    def test_monitor_warmup_metrics_scheduled(self) -> None:
        """Test that warmup metrics monitoring is scheduled every 15 minutes."""
        schedule = celery_app.conf.beat_schedule
        
        # Check monitoring task exists
        assert "monitor-warmup-metrics" in schedule
        
        monitor_task = schedule["monitor-warmup-metrics"]
        assert monitor_task["task"] == "tasks.monitoring.monitor_warmup_metrics"
        
        # Verify schedule is every 15 minutes
        task_schedule = monitor_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {0, 15, 30, 45}  # Every 15 minutes

    def test_monitor_api_calls_scheduled(self) -> None:
        """Test that API call monitoring is scheduled every minute."""
        schedule = celery_app.conf.beat_schedule
        
        assert "monitor-api-calls" in schedule
        monitor_task = schedule["monitor-api-calls"]
        assert monitor_task["task"] == "tasks.monitoring.monitor_api_calls"
        
        # Verify schedule is every minute
        task_schedule = monitor_task["schedule"]
        assert isinstance(task_schedule, crontab)
        # Every minute means all 60 minutes
        assert len(task_schedule.minute) == 60

    def test_monitor_cache_health_scheduled(self) -> None:
        """Test that cache health monitoring is scheduled every 5 minutes."""
        schedule = celery_app.conf.beat_schedule
        
        assert "monitor-cache-health" in schedule
        monitor_task = schedule["monitor-cache-health"]
        assert monitor_task["task"] == "tasks.monitoring.monitor_cache_health"
        
        # Verify schedule is every 5 minutes
        task_schedule = monitor_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}

    def test_storage_maintenance_tasks_scheduled(self) -> None:
        """存储层维护任务应全部注册并调度正确。"""
        schedule = celery_app.conf.beat_schedule

        assert "refresh-posts-latest" in schedule
        refresh_task = schedule["refresh-posts-latest"]
        assert refresh_task["task"] == "tasks.maintenance.refresh_posts_latest"
        assert isinstance(refresh_task["schedule"], crontab)
        assert refresh_task["schedule"].minute == {5}
        assert refresh_task["schedule"].hour == set(range(24))

        assert "cleanup-expired-posts-hot" in schedule
        hot_cleanup_task = schedule["cleanup-expired-posts-hot"]
        assert isinstance(hot_cleanup_task["schedule"], crontab)
        assert hot_cleanup_task["schedule"].minute == {15}
        assert hot_cleanup_task["schedule"].hour == set(range(24))

        assert "cleanup-old-posts" in schedule
        cold_cleanup_task = schedule["cleanup-old-posts"]
        assert cold_cleanup_task["task"] == "tasks.maintenance.cleanup_old_posts"
        assert isinstance(cold_cleanup_task["schedule"], crontab)
        assert cold_cleanup_task["schedule"].minute == {30}
        assert cold_cleanup_task["schedule"].hour == {3}

        assert "collect-storage-metrics" in schedule
        metrics_task = schedule["collect-storage-metrics"]
        assert metrics_task["task"] == "tasks.maintenance.collect_storage_metrics"
        assert isinstance(metrics_task["schedule"], crontab)
        assert metrics_task["schedule"].minute == {10}
        assert metrics_task["schedule"].hour == set(range(24))

        assert "archive-old-posts" in schedule
        archive_task = schedule["archive-old-posts"]
        assert archive_task["task"] == "tasks.maintenance.archive_old_posts"
        assert isinstance(archive_task["schedule"], crontab)
        assert archive_task["schedule"].minute == {45}
        assert archive_task["schedule"].hour == {2}

        assert "check-storage-capacity" in schedule
        capacity_task = schedule["check-storage-capacity"]
        assert capacity_task["task"] == "tasks.maintenance.check_storage_capacity"
        assert isinstance(capacity_task["schedule"], crontab)
        assert capacity_task["schedule"].minute == {40}
        assert capacity_task["schedule"].hour == {0, 6, 12, 18}

    def test_all_scheduled_tasks_registered(self) -> None:
        """Test that all scheduled tasks are registered in Celery."""
        schedule = celery_app.conf.beat_schedule
        
        # Get all registered task names
        registered_tasks = set(celery_app.tasks.keys())
        
        # Check each scheduled task is registered
        for task_name, task_config in schedule.items():
            task_path = task_config["task"]
            # Note: Celery may register tasks with or without the full path
            # We check if the task exists in any form
            assert any(
                task_path in registered_task or registered_task.endswith(task_path.split(".")[-1])
                for registered_task in registered_tasks
            ), f"Scheduled task '{task_path}' (from '{task_name}') not found in registered tasks"

    def test_legacy_crawler_still_exists(self) -> None:
        """Test that legacy crawler task still exists for backward compatibility."""
        schedule = celery_app.conf.beat_schedule
        
        # Check legacy task exists
        assert "crawl-seed-communities" in schedule
        
        legacy_task = schedule["crawl-seed-communities"]
        assert legacy_task["task"] == "tasks.crawler.crawl_seed_communities"
        
        # Verify it's still every 30 minutes
        task_schedule = legacy_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {0, 30}

    def test_monitoring_tasks_count(self) -> None:
        """Test that all expected monitoring tasks are scheduled."""
        schedule = celery_app.conf.beat_schedule
        
        # Expected monitoring tasks
        expected_monitoring = [
            "monitor-warmup-metrics",
            "monitor-api-calls",
            "monitor-cache-health",
            "monitor-crawler-health",
            "monitor-e2e-tests",
            "collect-test-logs",
            "update-performance-dashboard",
        ]
        
        for task_name in expected_monitoring:
            assert task_name in schedule, f"Expected monitoring task '{task_name}' not found"

    def test_schedule_intervals_valid(self) -> None:
        """Test that all schedule intervals are valid crontab expressions."""
        schedule = celery_app.conf.beat_schedule
        
        for task_name, task_config in schedule.items():
            task_schedule = task_config["schedule"]
            if isinstance(task_schedule, (int, float)):
                assert task_config.get("one_off") is True, f"Non-crontab schedule for '{task_name}' must be one-off"
                continue
            assert isinstance(task_schedule, crontab), f"Task '{task_name}' schedule is not a crontab"
            
            # Verify crontab has valid minute/hour sets
            assert isinstance(task_schedule.minute, set)
            assert isinstance(task_schedule.hour, set)
            
            # Verify minute values are in valid range (0-59)
            assert all(0 <= m <= 59 for m in task_schedule.minute)
            
            # Verify hour values are in valid range (0-23)
            assert all(0 <= h <= 23 for h in task_schedule.hour)

    def test_warmup_period_tasks_priority(self) -> None:
        """Test that warmup period tasks are properly configured."""
        schedule = celery_app.conf.beat_schedule
        
        # Warmup crawler should run less frequently than monitoring
        warmup_schedule = schedule["warmup-crawl-seed-communities"]["schedule"]
        monitor_schedule = schedule["monitor-warmup-metrics"]["schedule"]
        
        # Warmup runs every 2 hours (12 times per day)
        warmup_runs_per_day = len(warmup_schedule.hour)
        assert warmup_runs_per_day == 12
        
        # Monitor runs every 15 minutes (96 times per day)
        monitor_runs_per_hour = len(monitor_schedule.minute)
        assert monitor_runs_per_hour == 4  # 4 times per hour (every 15 min)


class TestCeleryBeatTaskRouting:
    """Test that scheduled tasks are routed to correct queues."""

    def test_crawler_tasks_routed_to_crawler_queue(self) -> None:
        """Test that crawler tasks are routed to crawler_queue."""
        task_routes = celery_app.conf.task_routes
        
        assert "tasks.crawler.crawl_seed_communities" in task_routes
        assert task_routes["tasks.crawler.crawl_seed_communities"]["queue"] == "crawler_queue"

    def test_monitoring_tasks_routed_to_monitoring_queue(self) -> None:
        """Test that monitoring tasks are routed to monitoring_queue."""
        task_routes = celery_app.conf.task_routes
        
        monitoring_tasks = [
            "tasks.monitoring.monitor_api_calls",
            "tasks.monitoring.monitor_cache_health",
            "tasks.monitoring.monitor_crawler_health",
        ]
        
        for task_name in monitoring_tasks:
            assert task_name in task_routes
            assert task_routes[task_name]["queue"] == "monitoring_queue"


class TestCeleryBeatConfiguration:
    """Test overall Celery Beat configuration."""

    def test_celery_app_configured(self) -> None:
        """Test that Celery app is properly configured."""
        assert celery_app is not None
        assert celery_app.conf is not None

    def test_timezone_configured(self) -> None:
        """Test that timezone is set to UTC."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_serializer_configured(self) -> None:
        """Test that JSON serializer is configured."""
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

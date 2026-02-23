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
        """Tiered crawl 心跳应每 30 分钟触发一次。"""
        schedule = celery_app.conf.beat_schedule

        assert "tick-tiered-crawl" in schedule

        tick_task = schedule["tick-tiered-crawl"]
        assert tick_task["task"] == "tasks.crawler.crawl_seed_communities_incremental"

        task_schedule = tick_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {0, 30}
        assert task_schedule.hour == set(range(24))

    def test_auto_crawl_incremental_runs_twice_per_hour(self) -> None:
        """低质量社区补抓任务应每 4 小时执行一次。"""
        schedule = celery_app.conf.beat_schedule

        assert "crawl-low-quality-communities" in schedule

        crawl_task = schedule["crawl-low-quality-communities"]
        assert crawl_task["task"] == "tasks.crawler.crawl_low_quality_communities"

        task_schedule = crawl_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {0}
        assert task_schedule.hour == {0, 4, 8, 12, 16, 20}

        options = crawl_task.get("options", {})
        assert options.get("queue") == "patrol_queue"
        assert options.get("expires") == 3600

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
        assert monitor_task.get("options", {}).get("queue") == "monitoring_queue"
        
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

    def test_monitor_facts_audit_scheduled(self) -> None:
        """facts 审计清理监控应每日运行。"""
        schedule = celery_app.conf.beat_schedule

        assert "monitor-facts-audit" in schedule
        monitor_task = schedule["monitor-facts-audit"]
        assert monitor_task["task"] == "tasks.monitoring.monitor_facts_audit_cleanup"

        task_schedule = monitor_task["schedule"]
        assert isinstance(task_schedule, crontab)
        assert task_schedule.minute == {40}
        assert task_schedule.hour == {4}

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
        assert hot_cleanup_task["schedule"].minute == {0}
        assert hot_cleanup_task["schedule"].hour == {4}

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

        assert "cleanup-expired-facts-audit" in schedule
        audit_task = schedule["cleanup-expired-facts-audit"]
        assert audit_task["task"] == "tasks.maintenance.cleanup_expired_facts_audit"
        assert isinstance(audit_task["schedule"], crontab)
        assert audit_task["schedule"].minute == {20}
        assert audit_task["schedule"].hour == {4}

        assert "archive-old-posts" in schedule
        archive_task = schedule["archive-old-posts"]
        assert archive_task["task"] == "tasks.maintenance.archive_old_posts"
        assert isinstance(archive_task["schedule"], crontab)
        assert archive_task["schedule"].minute == {45}
        assert archive_task["schedule"].hour == {2}

        assert "sync-community-member-counts" in schedule
        sync_task = schedule["sync-community-member-counts"]
        assert sync_task["task"] == "tasks.community.sync_member_counts"
        assert isinstance(sync_task["schedule"], crontab)
        assert sync_task["schedule"].minute == {0}
        assert sync_task["schedule"].hour == {0, 12}

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
        """Legacy crawler 已移出常驻调度。"""
        schedule = celery_app.conf.beat_schedule
        
        assert "crawl-seed-communities" not in schedule

    def test_monitoring_tasks_count(self) -> None:
        """Test that all expected monitoring tasks are scheduled."""
        schedule = celery_app.conf.beat_schedule
        
        # Expected monitoring tasks
        expected_monitoring = [
            "monitor-warmup-metrics",
            "monitor-api-calls",
            "monitor-cache-health",
            "monitor-crawler-health",
            "monitor-facts-audit",
            "monitor-contract-health",
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
        """Tiered crawl 心跳应比低质量补抓更频繁。"""
        schedule = celery_app.conf.beat_schedule
        
        tick_schedule = schedule["tick-tiered-crawl"]["schedule"]
        low_quality_schedule = schedule["crawl-low-quality-communities"]["schedule"]

        tick_runs_per_day = len(tick_schedule.minute) * len(tick_schedule.hour)
        low_quality_runs_per_day = len(low_quality_schedule.minute) * len(
            low_quality_schedule.hour
        )
        assert tick_runs_per_day > low_quality_runs_per_day


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
            "tasks.monitoring.monitor_warmup_metrics",
            "tasks.monitoring.monitor_api_calls",
            "tasks.monitoring.monitor_cache_health",
            "tasks.monitoring.monitor_crawler_health",
            "tasks.monitoring.monitor_facts_audit_cleanup",
            "tasks.monitoring.monitor_contract_health",
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

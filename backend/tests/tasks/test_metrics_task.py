from __future__ import annotations

from datetime import date
from pathlib import Path

from app.tasks.metrics_task import generate_daily_metrics_task
from app.services.metrics.daily_metrics import DailyMetrics


def test_generate_daily_metrics_task_invokes_collect_and_write(monkeypatch, tmp_path: Path) -> None:
    metrics = DailyMetrics(
        date=date(2025, 10, 20),
        cache_hit_rate=0.7,
        valid_posts_24h=2000,
        total_communities=35,
        duplicate_rate=0.1,
        precision_at_50=0.62,
        avg_score=0.55,
    )

    async def fake_collect(**kwargs):
        return metrics

    written: dict[str, Path] = {}

    def fake_write(received_metrics: DailyMetrics, output_directory: Path = Path(".")) -> Path:
        written["metrics"] = received_metrics
        path = output_directory / "2025-10.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("dummy", encoding="utf-8")
        return path

    monkeypatch.setattr(
        "app.tasks.metrics_task.collect_daily_metrics",
        fake_collect,
    )
    monkeypatch.setattr(
        "app.tasks.metrics_task.write_metrics_to_csv",
        fake_write,
    )

    result = generate_daily_metrics_task(
        labeled_data_path=str(tmp_path / "labeled.csv"),
        threshold_config_path=str(tmp_path / "thresholds.yaml"),
        dedup_config_path=str(tmp_path / "dedup.yaml"),
        output_directory=str(tmp_path),
    )

    assert written["metrics"] == metrics
    assert Path(result).exists()

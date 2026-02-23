from app import models
from app.db.base import Base


def test_crawler_run_tables_registered() -> None:
    assert "crawler_runs" in Base.metadata.tables
    assert "crawler_run_targets" in Base.metadata.tables

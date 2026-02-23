import asyncio
import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Add backend to sys.path to allow imports
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.metrics import QualityMetrics
from app.services.metrics.collector import save_metrics

# Configure logging to stdout to verify the ERROR log appears
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

async def main():
    # Connect to TEST DB
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test",
        echo=False,
    )
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create invalid metric (rate > 1.0)
        invalid = QualityMetrics(
            date=date(2099, 1, 1),
            collection_success_rate=Decimal("1.5"), # VIOLATION of ck_quality_metrics_collection_rate_range
            deduplication_rate=Decimal("0.5"),
            processing_time_p50=Decimal("1.0"),
            processing_time_p95=Decimal("2.0"),
        )
        
        print("\n--- Attempting to save invalid metrics (Expecting Error Log below) ---")
        try:
            await save_metrics(session, invalid, output_dir=Path("/tmp"))
        except Exception as e:
            print(f"\n--- Caught Expected Exception: {type(e).__name__} ---")
            print(f"Exception message contains constraint name: {'ck_quality_metrics_collection_rate_range' in str(e)}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

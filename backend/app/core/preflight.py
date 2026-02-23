import os
import sys
import logging
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.llm.clients.openai_client import resolve_llm_api_key

# Configure basic logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_connection() -> bool:
    """
    Verify database connectivity using the configured DATABASE_URL.
    """
    db_url = settings.database_url
    if not db_url:
        logger.error("❌ DATABASE_URL is not set in environment or config.")
        return False
    
    # Force sync driver for this check if it's async
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "+psycopg")
    
    # Mask password for logging
    safe_url = db_url.split("@")[-1] if "@" in db_url else "******"
    logger.info(f"🔌 Testing connection to: ...@{safe_url}")

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection established.")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

def check_openai_key(strict: bool = False) -> bool:
    """
    Check if OpenAI API key is present.
    """
    key = resolve_llm_api_key()
    if not key:
        msg = "⚠️ LLM API key is missing (OPENAI_API_KEY/OPENROUTER_API_KEY). LLM features will degrade to templates."
        if strict:
            logger.error(f"❌ {msg}")
            return False
        else:
            logger.warning(msg)
            return True
    
    logger.info("✅ LLM API key found.")
    return True

def run_preflight_checks(strict_llm: bool = False) -> bool:
    """
    Run all system checks. Returns True if healthy, False otherwise.
    """
    logger.info("🚀 Starting Pre-flight Checks...")
    
    checks = [
        check_database_connection(),
        check_openai_key(strict=strict_llm)
    ]
    
    if all(checks):
        logger.info("✅ System is READY for takeoff.")
        return True
    else:
        logger.error("❌ System failed pre-flight checks.")
        return False

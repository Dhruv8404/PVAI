import os
import sys
import asyncio
import logging

# Configure basic logging for script output
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("startup_check")

# Add backend directory to python path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

try:
    from app.core.config import settings
    from app.core.database import engine
    from sqlalchemy import text
except ImportError as e:
    logger.error(f"Failed to import backend modules: {e}")
    logger.error("Make sure to run this script inside the virtual environment or with backend/ in path.")
    sys.exit(1)


async def check_database() -> bool:
    logger.info("Checking database connection...")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Database Connection: PASS")
        return True
    except Exception as e:
        logger.error(f"✗ Database Connection: FAIL ({e})")
        return False


def check_storage() -> bool:
    logger.info("Checking storage directory structures...")
    required_folders = [
        "storage",
        "storage/uploads",
        "storage/templates",
        "storage/reports",
        "storage/logs"
    ]
    all_pass = True
    for folder in required_folders:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", folder)
        if os.path.exists(path):
            logger.info(f"✓ Storage Folder '{folder}': PASS")
        else:
            try:
                os.makedirs(path, exist_ok=True)
                logger.info(f"✓ Storage Folder '{folder}': PASS (Created)")
            except Exception as e:
                logger.error(f"✗ Storage Folder '{folder}': FAIL (Could not create: {e})")
                all_pass = False
    return all_pass


def check_security() -> bool:
    logger.info("Checking security configurations...")
    all_pass = True
    
    # 1. SECRET_KEY
    if not settings.SECRET_KEY:
        logger.error("✗ SECRET_KEY: FAIL (Missing)")
        all_pass = False
    elif settings.SECRET_KEY == "7aef83b519c2f6d90d8a4362b2e8a1c97f6c3d9e8b7a6e5d4c3b2a10f9e8d7c6":
        if settings.ENV.lower() == "production":
            logger.error("✗ SECRET_KEY: FAIL (Default mock key is active in production environment)")
            all_pass = False
        else:
            logger.warning("⚠ SECRET_KEY: WARN (Using default development key)")
    else:
        logger.info("✓ SECRET_KEY: PASS")
        
    # 2. JWT_ALGORITHM
    if not settings.JWT_ALGORITHM:
        logger.error("✗ JWT_ALGORITHM: FAIL (Missing)")
        all_pass = False
    else:
        logger.info("✓ JWT_ALGORITHM: PASS")
        
    return all_pass


async def main():
    logger.info("=== STARTING STARTUP DEPENDENCY CHECKS ===")
    
    db_ok = await check_database()
    storage_ok = check_storage()
    security_ok = check_security()
    
    logger.info("==========================================")
    if db_ok and storage_ok and security_ok:
        logger.info("STARTUP VERIFICATION: SUCCESS (All critical services ready)")
        sys.exit(0)
    else:
        logger.error("STARTUP VERIFICATION: FAILED (Check critical issues above)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

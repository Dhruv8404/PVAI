import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("deployment_check")


def run_check_script(script_name: str) -> int:
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    logger.info(f"Running sub-check script: {script_name}...")
    try:
        # Run python process
        res = subprocess.run(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        print(res.stdout)
        return res.returncode
    except Exception as e:
        logger.error(f"Failed to execute sub-script {script_name}: {e}")
        return 1


def main():
    logger.info("==========================================")
    logger.info("PVAI PRODUCTION DEPLOYMENT CHECKS STARTING")
    logger.info("==========================================")
    
    # 1. Run Startup check (Critical)
    startup_code = run_check_script("startup_check.py")
    
    # 2. Run AI services check (Optional)
    ai_code = run_check_script("ai_check.py")

    # 3. Run Runtime Production check (Optional)
    prod_code = run_check_script("production_check.py")
    
    logger.info("==========================================")
    logger.info("CONSOLIDATED DEPLOYMENT REPORT")
    logger.info("==========================================")
    
    if startup_code == 0:
        logger.info("✓ CRITICAL SERVICES: PASS")
    else:
        logger.error("✗ CRITICAL SERVICES: FAIL (Startup would abort in production)")
        
    if ai_code == 0:
        logger.info("✓ AI OPTIONAL SERVICES: PASS")
    else:
        logger.warning("⚠ AI OPTIONAL SERVICES: WARN / FAIL")

    if prod_code == 0:
        logger.info("✓ RUNTIME PRODUCTION CONFIGS: PASS")
    else:
        logger.warning("⚠ RUNTIME PRODUCTION CONFIGS: WARN / FAIL")
        
    logger.info("==========================================")
    if startup_code == 0:
        logger.info("OVERALL DEPLOYMENT READINESS: READY TO DEPLOY!")
        sys.exit(0)
    else:
        logger.error("OVERALL DEPLOYMENT READINESS: NOT READY (Critical issues present)")
        sys.exit(1)


if __name__ == "__main__":
    main()

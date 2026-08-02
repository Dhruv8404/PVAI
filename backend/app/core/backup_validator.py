import os
import glob
import logging
from app.core.config import settings

logger = logging.getLogger("app.startup")


def validate_backups():
    """Performs validation checks on application data backups.
    
    Checks database dump files, ChromaDB directories, uploaded files,
    and generated reports. Logs warnings only, never blocks startup.
    """
    logger.info("Executing database and storage backup validation checks...")
    
    backup_dir = "storage/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    warnings = []
    
    # 1. Validate Database Backup existence (*.sql or *.dump)
    db_backups = glob.glob(os.path.join(backup_dir, "*.sql")) + glob.glob(os.path.join(backup_dir, "*.dump"))
    if not db_backups:
        warnings.append(
            f"No database SQL dump backups (*.sql, *.dump) found in '{backup_dir}'."
        )
    else:
        # Check size of newest backup
        newest_db_backup = max(db_backups, key=os.path.getmtime)
        size_mb = os.path.getsize(newest_db_backup) / (1024 * 1024)
        logger.info(f"Newest database backup file: {os.path.basename(newest_db_backup)} ({size_mb:.2f} MB)")
        if size_mb == 0:
            warnings.append(f"Database backup file '{os.path.basename(newest_db_backup)}' is empty (0 bytes).")
            
    # 2. Validate ChromaDB backup snapshots
    chroma_backup_dir = os.path.join(backup_dir, "chromadb")
    if not os.path.exists(chroma_backup_dir) or not os.listdir(chroma_backup_dir):
        warnings.append(
            f"No ChromaDB vector database snapshot backups found in '{chroma_backup_dir}'."
        )
    else:
        logger.info(f"ChromaDB backup directory verified at '{chroma_backup_dir}'.")
        
    # 3. Validate Uploads backup
    uploads_backup_dir = os.path.join(backup_dir, "uploads")
    if not os.path.exists(uploads_backup_dir) or not os.listdir(uploads_backup_dir):
        warnings.append(
            f"No raw uploads backup files found in '{uploads_backup_dir}'."
        )
    else:
        logger.info(f"Uploads backup directory verified at '{uploads_backup_dir}'.")
        
    # 4. Validate Generated Reports backup
    reports_backup_dir = os.path.join(backup_dir, "reports")
    if not os.path.exists(reports_backup_dir) or not os.listdir(reports_backup_dir):
        warnings.append(
            f"No generated PDF/HTML reports backups found in '{reports_backup_dir}'."
        )
    else:
        logger.info(f"Reports backup directory verified at '{reports_backup_dir}'.")
        
    # Log warnings
    for warn in warnings:
        logger.warning(f"[BACKUP WARNING] {warn}")
        
    if not warnings:
        logger.info("Backup integrity validation succeeded (all components present).")
    else:
        logger.info("Backup integrity validation finished with warnings.")

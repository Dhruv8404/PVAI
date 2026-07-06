import uuid
from datetime import datetime, UTC
from typing import List, Tuple
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.storage import get_storage
from app.modules.downloads.model import DownloadLog
from app.modules.downloads.repository import download_log_repository
from app.modules.documents.repository import document_repository
from app.modules.users.model import User


class DownloadService:
    async def get_document_for_download(
        self,
        db: AsyncSession,
        *,
        doc_id: uuid.UUID,
        user: User,
        client_ip: str,
        file_format: str = "HTML"
    ) -> Tuple[bytes, str]:
        # Fetch document
        doc = await document_repository.get(db, doc_id)
        if not doc:
            raise NotFoundException("Document record not found")

        # Verify ownership (Admins can download any, User can only download their own)
        user_roles = [r.name for r in user.roles]
        if "Admin" not in user_roles and doc.user_id != user.id:
            raise ForbiddenException("Access restricted. You are not authorized to download this file")

        # Retrieve file path depending on format
        target_path = doc.html_path
        if file_format.upper() == "PDF":
            if not doc.pdf_path:
                raise NotFoundException("PDF layout has not been compiled for this document yet")
            target_path = doc.pdf_path

        # Handle legacy client side draft fallback
        if not target_path or target_path == "client_side_draft":
            file_bytes = b"<html><body><h3>Client Side Draft Report</h3><p>This draft was generated on the client side without server-side file persistence.</p></body></html>"
        # Download from Cloudinary if path is a URL
        elif target_path.startswith("http://") or target_path.startswith("https://"):
            import urllib.request
            import asyncio
            
            def fetch_url(url: str) -> bytes:
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req) as response:
                    return response.read()
            
            loop = asyncio.get_running_loop()
            try:
                file_bytes = await loop.run_in_executor(None, fetch_url, target_path)
            except Exception as e:
                raise NotFoundException(f"Failed to retrieve report file from Cloudinary storage: {str(e)}")
        # Read local file
        else:
            storage = get_storage()
            try:
                file_bytes = await storage.get_file(target_path)
            except Exception as e:
                # If local file is missing, try checking if the file resides relatively
                try:
                    import os
                    if not os.path.isabs(target_path) and not target_path.startswith("storage/"):
                        fallback_path = os.path.join("storage", target_path)
                        file_bytes = await storage.get_file(fallback_path)
                    else:
                        raise e
                except Exception:
                    raise NotFoundException(f"Report file not found in local storage path: {target_path}")

        # Record download audit log
        log_in = {
            "generated_document_id": doc.id,
            "user_id": user.id,
            "format": file_format.upper(),
            "ip_address": client_ip
        }
        await download_log_repository.create(db, obj_in_data=log_in)

        # Increment download statistics
        doc.download_count = (doc.download_count or 0) + 1
        doc.last_downloaded_at = datetime.now(UTC)
        db.add(doc)
        await db.flush()

        # Return file bytes and suggested filename
        file_extension = "html" if file_format.upper() == "HTML" else "pdf"
        suggested_filename = f"{doc.name}.{file_extension}"
        
        return file_bytes, suggested_filename

    async def list_logs(self, db: AsyncSession, *, limit: int = 100) -> List[DownloadLog]:
        stmt = select(DownloadLog).order_by(desc(DownloadLog.timestamp)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())


download_service = DownloadService()

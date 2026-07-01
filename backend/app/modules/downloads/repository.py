from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.repository import BaseRepository
from app.modules.downloads.model import DownloadLog


class DownloadLogRepository(BaseRepository[DownloadLog]):
    def __init__(self):
        super().__init__(DownloadLog)


download_log_repository = DownloadLogRepository()

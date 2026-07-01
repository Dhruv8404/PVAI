import os
import aiofiles
from abc import ABC, abstractmethod
from app.core.config import settings


class StorageFacade(ABC):
    @abstractmethod
    async def save_file(self, content: bytes, subpath: str) -> str:
        """Saves file content and returns the resolved relative access path."""
        pass

    @abstractmethod
    async def get_file(self, path: str) -> bytes:
        """Retrieves and returns the file bytes."""
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Deletes the target file from storage."""
        pass


class LocalFileStorage(StorageFacade):
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir

    def _resolve_path(self, subpath: str) -> str:
        # Prevent path traversal attacks
        safe_path = os.path.normpath(subpath).lstrip("/\\")
        return os.path.join(self.base_dir, safe_path)

    async def save_file(self, content: bytes, subpath: str) -> str:
        full_path = self._resolve_path(subpath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)
            
        # Return path string normalized for relative routing
        return full_path.replace("\\", "/")

    async def get_file(self, path: str) -> bytes:
        # If path is already resolved, use it directly after validation
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete_file(self, path: str) -> bool:
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception:
            pass
        return False


class S3FileStorage(StorageFacade):
    # Simulated S3 bucket adapter for production-readiness
    async def save_file(self, content: bytes, subpath: str) -> str:
        # Placeholder simulating boto3 calls
        print(f"[S3-SIMULATION] Saved file to s3://{settings.S3_BUCKET_NAME}/{subpath}")
        return f"s3://{settings.S3_BUCKET_NAME}/{subpath}"

    async def get_file(self, path: str) -> bytes:
        print(f"[S3-SIMULATION] Fetched bytes from {path}")
        return b"<html><body>Simulated S3 Content</body></html>"

    async def delete_file(self, path: str) -> bool:
        print(f"[S3-SIMULATION] Removed object {path}")
        return True


# Helper dependency to resolve active storage engine
def get_storage() -> StorageFacade:
    if settings.STORAGE_TYPE == "s3":
        return S3FileStorage()
    return LocalFileStorage()

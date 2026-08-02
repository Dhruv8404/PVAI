import os
import shutil
import logging
from abc import ABC, abstractmethod
import httpx
import aiofiles
from app.core.config import settings

logger = logging.getLogger("app.startup")


# =========================================================================
# 1. NEW ENTERPRISE STORAGE PROVIDER ABSTRACTIONS (Step 4)
# =========================================================================

class BaseStorageProvider(ABC):
    """Abstract Base Class specifying the File Storage Provider contract."""
    
    @abstractmethod
    def upload_file(self, local_file_path: str, remote_destination_name: str) -> str:
        """Uploads a local file to the storage provider and returns the public URL or relative file path."""
        pass

    @abstractmethod
    def download_file(self, source_path_or_url: str, local_destination_path: str) -> bool:
        """Downloads a file from the storage provider to the local filesystem."""
        pass

    @abstractmethod
    def delete_file(self, file_path_or_url: str) -> bool:
        """Deletes a file from the storage provider database."""
        pass


class LocalStorageProvider(BaseStorageProvider):
    """Local disk filesystem storage provider."""
    
    def __init__(self, upload_dir: str = "storage/uploads"):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    def upload_file(self, local_file_path: str, remote_destination_name: str) -> str:
        dest_path = os.path.join(self.upload_dir, remote_destination_name)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        # Avoid copying the file to itself
        if os.path.abspath(local_file_path) != os.path.abspath(dest_path):
            shutil.copy2(local_file_path, dest_path)
        logger.info(f"[STORAGE] Local copy completed: {local_file_path} -> {dest_path}")
        # Return relative path as target URL identifier
        return dest_path.replace("\\", "/")

    def download_file(self, source_path_or_url: str, local_destination_path: str) -> bool:
        if os.path.exists(source_path_or_url):
            os.makedirs(os.path.dirname(local_destination_path), exist_ok=True)
            if os.path.abspath(source_path_or_url) != os.path.abspath(local_destination_path):
                shutil.copy2(source_path_or_url, local_destination_path)
            return True
        logger.warning(f"[STORAGE] Local file not found: {source_path_or_url}")
        return False

    def delete_file(self, file_path_or_url: str) -> bool:
        if os.path.exists(file_path_or_url):
            try:
                os.remove(file_path_or_url)
                logger.info(f"[STORAGE] Local file deleted: {file_path_or_url}")
                return True
            except Exception as e:
                logger.error(f"[STORAGE] Local delete exception for {file_path_or_url}: {e}")
        return False


class CloudinaryStorageProvider(BaseStorageProvider):
    """Cloudinary media storage cloud provider."""
    
    def __init__(self):
        import cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )

    def upload_file(self, local_file_path: str, remote_destination_name: str) -> str:
        import cloudinary.uploader
        # Extract name without extension for public_id
        public_id = os.path.splitext(remote_destination_name)[0]
        res = cloudinary.uploader.upload(
            local_file_path,
            public_id=public_id,
            resource_type="auto"
        )
        url = res.get("secure_url")
        if not url:
            raise Exception("Cloudinary secure_url is empty in response payload.")
        logger.info(f"[STORAGE] Cloudinary upload success: {url}")
        return url

    def download_file(self, source_path_or_url: str, local_destination_path: str) -> bool:
        if not source_path_or_url.startswith("http"):
            # Fallback to local copy if path is a local file
            if os.path.exists(source_path_or_url):
                shutil.copy2(source_path_or_url, local_destination_path)
                return True
            return False
            
        logger.info(f"[STORAGE] Cloudinary HTTP fetch starting: {source_path_or_url}")
        os.makedirs(os.path.dirname(local_destination_path), exist_ok=True)
        try:
            with open(local_destination_path, "wb") as f:
                with httpx.Client() as client:
                    r = client.get(source_path_or_url)
                    if r.status_code == 200:
                        f.write(r.content)
                        return True
            logger.warning(f"[STORAGE] Cloudinary HTTP download failed (Status {r.status_code})")
        except Exception as e:
            logger.error(f"[STORAGE] Cloudinary HTTP download exception: {e}")
        return False

    def delete_file(self, file_path_or_url: str) -> bool:
        import cloudinary.uploader
        try:
            basename = os.path.basename(file_path_or_url)
            public_id = os.path.splitext(basename)[0]
            res = cloudinary.uploader.destroy(public_id)
            logger.info(f"[STORAGE] Cloudinary file deleted: {public_id} (Result: {res})")
            return res.get("result") == "ok"
        except Exception as e:
            logger.error(f"[STORAGE] Cloudinary delete exception: {e}")
            return False


class S3StorageProvider(BaseStorageProvider):
    """AWS S3 Enterprise cloud storage provider stub (Future-ready)."""
    
    def upload_file(self, local_file_path: str, remote_destination_name: str) -> str:
        logger.info(f"[STORAGE STUB] S3 Mock upload: {local_file_path} -> s3://{settings.S3_BUCKET_NAME}/{remote_destination_name}")
        return f"https://s3.amazonaws.com/{settings.S3_BUCKET_NAME}/{remote_destination_name}"

    def download_file(self, source_path_or_url: str, local_destination_path: str) -> bool:
        logger.info(f"[STORAGE STUB] S3 Mock download: {source_path_or_url} -> {local_destination_path}")
        return True

    def delete_file(self, file_path_or_url: str) -> bool:
        logger.info(f"[STORAGE STUB] S3 Mock delete: {file_path_or_url}")
        return True


class AzureBlobStorageProvider(BaseStorageProvider):
    """Azure Blob cloud storage provider stub (Future-ready)."""
    
    def upload_file(self, local_file_path: str, remote_destination_name: str) -> str:
        logger.info(f"[STORAGE STUB] Azure Blob Mock upload: {local_file_path} -> azureblob://vault/{remote_destination_name}")
        return f"https://azureblob.core.windows.net/vault/{remote_destination_name}"

    def download_file(self, source_path_or_url: str, local_destination_path: str) -> bool:
        logger.info(f"[STORAGE STUB] Azure Blob Mock download: {source_path_or_url} -> {local_destination_path}")
        return True

    def delete_file(self, file_path_or_url: str) -> bool:
        logger.info(f"[STORAGE STUB] Azure Blob Mock delete: {file_path_or_url}")
        return True


class StorageProviderFactory:
    """Resolves active storage provider based on environment type."""
    
    @staticmethod
    def get_provider() -> BaseStorageProvider:
        storage_type = settings.STORAGE_TYPE.lower()
        if storage_type == "cloudinary":
            return CloudinaryStorageProvider()
        elif storage_type == "s3":
            return S3StorageProvider()
        elif storage_type == "azure":
            return AzureBlobStorageProvider()
        else:
            return LocalStorageProvider()


# =========================================================================
# 2. LEGACY STORAGE INTERFACES (For Backwards Compatibility)
# =========================================================================

class StorageFacade(ABC):
    """Abstract interface defining the legacy file storage structure."""

    @abstractmethod
    async def save_file(self, content: bytes, subpath: str) -> str:
        pass

    @abstractmethod
    async def get_file(self, path: str) -> bytes:
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        pass


class LocalFileStorage(StorageFacade):
    """Legacy Local File Storage implementation."""

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, subpath: str) -> str:
        # Standardize relative subpath directories
        clean_subpath = subpath.lstrip("/")
        if not clean_subpath.startswith("storage/"):
            return os.path.join(self.base_dir, clean_subpath)
        return clean_subpath

    async def save_file(self, content: bytes, subpath: str) -> str:
        full_path = self._resolve_path(subpath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)
        return full_path.replace("\\", "/")

    async def get_file(self, path: str) -> bytes:
        resolved = self._resolve_path(path)
        async with aiofiles.open(resolved, "rb") as f:
            return await f.read()

    async def delete_file(self, path: str) -> bool:
        resolved = self._resolve_path(path)
        try:
            if os.path.exists(resolved):
                os.remove(resolved)
                return True
        except Exception:
            pass
        return False


class S3FileStorage(StorageFacade):
    """Legacy Simulated S3 Adapter."""

    async def save_file(self, content: bytes, subpath: str) -> str:
        logger.info(f"[S3-SIMULATION] Saved file to s3://{settings.S3_BUCKET_NAME}/{subpath}")
        return f"s3://{settings.S3_BUCKET_NAME}/{subpath}"

    async def get_file(self, path: str) -> bytes:
        return b"<html><body>Simulated S3 Content</body></html>"

    async def delete_file(self, path: str) -> bool:
        return True


def get_storage() -> StorageFacade:
    """Legacy storage factory resolver."""
    if settings.STORAGE_TYPE == "s3":
        return S3FileStorage()
    return LocalFileStorage()

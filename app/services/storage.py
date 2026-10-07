"""Image storage with local and Supabase Storage backends."""

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO, Iterable, Optional
from urllib.parse import quote

import httpx

from app.config import settings


class StorageError(Exception):
    """Raised when a storage operation cannot be completed."""


class StorageService:
    """Store item images locally in development or in Supabase in production."""

    def __init__(
        self,
        backend: Optional[str] = None,
        upload_dir: Optional[str] = None,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        bucket: Optional[str] = None,
        public_bucket: Optional[bool] = None,
    ):
        self.backend = (backend or settings.storage_backend).lower()
        self.upload_dir = Path(upload_dir or settings.upload_dir)
        self.supabase_url = (supabase_url or settings.supabase_url or "").rstrip("/")
        self.service_role_key = service_role_key or settings.supabase_service_role_key or ""
        self.bucket = bucket or settings.supabase_storage_bucket
        self.public_bucket = (
            settings.supabase_storage_public
            if public_bucket is None
            else public_bucket
        )

        if self.backend == "local":
            self.upload_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_remote(self) -> bool:
        return self.backend == "supabase"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }

    @property
    def _storage_api_url(self) -> str:
        return f"{self.supabase_url}/storage/v1"

    def _object_api_url(self, relative_path: str) -> str:
        encoded_path = quote(relative_path, safe="/")
        return f"{self._storage_api_url}/object/{self.bucket}/{encoded_path}"

    @staticmethod
    def _get_relative_path(
        item_id: str,
        image_id: str,
        suffix: str,
        extension: str = "jpg",
    ) -> str:
        return f"items/{item_id}/images/{image_id}/{suffix}.{extension}"

    @staticmethod
    def _extension(content_type: str) -> str:
        return {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
        }.get(content_type, "jpg")

    async def ensure_ready(self) -> None:
        """Ensure the configured Supabase bucket exists."""
        if not self.is_remote:
            return

        bucket_url = f"{self._storage_api_url}/bucket/{quote(self.bucket, safe='')}"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(bucket_url, headers=self._headers)
            if response.status_code == 200:
                return
            if response.status_code != 404:
                raise StorageError(
                    f"Supabase bucket check failed ({response.status_code}): {response.text}"
                )

            create_response = await client.post(
                f"{self._storage_api_url}/bucket",
                headers={**self._headers, "Content-Type": "application/json"},
                json={
                    "id": self.bucket,
                    "name": self.bucket,
                    "public": self.public_bucket,
                    "file_size_limit": settings.max_image_size_bytes,
                    "allowed_mime_types": settings.allowed_image_types_list,
                },
            )
            if create_response.status_code not in {200, 201}:
                raise StorageError(
                    "Could not create the Supabase storage bucket "
                    f"({create_response.status_code}): {create_response.text}"
                )

    async def _upload(
        self,
        data: bytes,
        relative_path: str,
        content_type: str,
    ) -> str:
        if not self.is_remote:
            file_path = self.upload_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                file_path.write_bytes(data)
            except OSError as exc:
                raise StorageError(f"Failed to upload image: {exc}") from exc
            return relative_path

        headers = {
            **self._headers,
            "Content-Type": content_type,
            "Cache-Control": "3600",
            "x-upsert": "true",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self._object_api_url(relative_path),
                headers=headers,
                content=data,
            )
        if response.status_code not in {200, 201}:
            raise StorageError(
                f"Supabase upload failed ({response.status_code}): {response.text}"
            )
        return relative_path

    async def upload_image(
        self,
        file_data: BinaryIO,
        item_id: str,
        image_id: str,
        content_type: str,
        suffix: str = "original",
    ) -> str:
        extension = self._extension(content_type)
        relative_path = self._get_relative_path(item_id, image_id, suffix, extension)
        return await self._upload(file_data.read(), relative_path, content_type)

    async def upload_bytes(
        self,
        data: bytes,
        item_id: str,
        image_id: str,
        content_type: str,
        suffix: str = "processed",
    ) -> str:
        extension = self._extension(content_type)
        relative_path = self._get_relative_path(item_id, image_id, suffix, extension)
        return await self._upload(data, relative_path, content_type)

    async def download_image(self, relative_path: str) -> bytes:
        if not self.is_remote:
            file_path = self.upload_dir / relative_path
            if not file_path.exists():
                raise StorageError(f"Image not found: {relative_path}")
            try:
                return file_path.read_bytes()
            except OSError as exc:
                raise StorageError(f"Failed to download image: {exc}") from exc

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                self._object_api_url(relative_path), headers=self._headers
            )
        if response.status_code != 200:
            raise StorageError(
                f"Supabase download failed ({response.status_code}): {response.text}"
            )
        return response.content

    async def delete_images(self, relative_paths: Iterable[str]) -> int:
        paths = [path for path in relative_paths if path]
        if not paths:
            return 0

        if not self.is_remote:
            deleted = 0
            for relative_path in paths:
                file_path = self.upload_dir / relative_path
                try:
                    if file_path.exists():
                        file_path.unlink()
                        deleted += 1
                except OSError as exc:
                    raise StorageError(f"Failed to delete image: {exc}") from exc
            return deleted

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                "DELETE",
                f"{self._storage_api_url}/object/{self.bucket}",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"prefixes": paths},
            )
        if response.status_code not in {200, 204}:
            raise StorageError(
                f"Supabase delete failed ({response.status_code}): {response.text}"
            )
        return len(paths)

    async def delete_image(self, relative_path: str) -> bool:
        await self.delete_images([relative_path])
        return True

    async def delete_item_images(self, item_id: uuid.UUID) -> int:
        """Delete a local item folder; remote deletion needs known object keys."""
        if self.is_remote:
            raise StorageError(
                "Remote item deletion requires image object keys from the database"
            )
        item_dir = self.upload_dir / "items" / str(item_id)
        if not item_dir.exists():
            return 0
        count = sum(1 for path in item_dir.rglob("*") if path.is_file())
        try:
            shutil.rmtree(item_dir)
        except OSError as exc:
            raise StorageError(f"Failed to delete item images: {exc}") from exc
        return count

    def get_file_url(self, relative_path: str) -> str:
        if self.is_remote and self.public_bucket:
            encoded_path = quote(relative_path, safe="/")
            return (
                f"{self._storage_api_url}/object/public/"
                f"{quote(self.bucket, safe='')}/{encoded_path}"
            )
        return f"/uploads/{relative_path}"

    def get_absolute_path(self, relative_path: str) -> Path:
        if self.is_remote:
            raise StorageError("Remote storage objects do not have a local path")
        return self.upload_dir / relative_path


storage_service = StorageService()

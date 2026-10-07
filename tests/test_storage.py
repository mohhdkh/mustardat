"""Storage backend tests."""

from io import BytesIO

import pytest

from app.services.storage import StorageService


@pytest.mark.asyncio
async def test_local_storage_round_trip(tmp_path):
    storage = StorageService(backend="local", upload_dir=str(tmp_path))

    key = await storage.upload_image(
        BytesIO(b"test-image"),
        item_id="item-1",
        image_id="image-1",
        content_type="image/jpeg",
    )

    assert key == "items/item-1/images/image-1/original.jpg"
    assert await storage.download_image(key) == b"test-image"
    assert storage.get_file_url(key) == f"/uploads/{key}"
    assert await storage.delete_image(key) is True
    assert not storage.get_absolute_path(key).exists()


def test_supabase_public_url():
    storage = StorageService(
        backend="supabase",
        supabase_url="https://example.supabase.co/",
        service_role_key="server-only-key",
        bucket="mustardat-images",
        public_bucket=True,
    )

    key = "items/item-1/images/image-1/original.jpg"
    assert storage.get_file_url(key) == (
        "https://example.supabase.co/storage/v1/object/public/"
        "mustardat-images/items/item-1/images/image-1/original.jpg"
    )

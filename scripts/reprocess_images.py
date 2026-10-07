"""Reprocess uploaded images that previously failed or are still pending."""

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.models.embedding import ImageEmbedding
from app.models.image import Image
from app.services.image_processing import image_processor
from app.services.storage import storage_service


async def reprocess_pending_images() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Image)
            .options(selectinload(Image.embedding))
            .where(Image.is_processed.is_(False))
        )
        images = result.scalars().all()

        if not images:
            print("No pending images found.")
            return

        processed_count = 0
        for image in images:
            try:
                content = await storage_service.download_image(image.file_path_original)
                processed = await image_processor.process_image(content)

                image.file_path_processed = await storage_service.upload_bytes(
                    processed.processed_image,
                    image.item_id,
                    image.id,
                    "image/jpeg",
                    "processed",
                )
                image.file_path_thumbnail = await storage_service.upload_bytes(
                    processed.thumbnail,
                    image.item_id,
                    image.id,
                    "image/jpeg",
                    "thumbnail",
                )
                image.width = processed.width
                image.height = processed.height
                image.exif_data_json = (
                    json.dumps(processed.exif_data) if processed.exif_data else None
                )
                image.is_processed = True
                image.processing_error = None

                embedding = image.embedding or ImageEmbedding(image_id=image.id)
                embedding.embedding_json = json.dumps(processed.embedding.tolist())
                embedding.phash = processed.phash
                embedding.dhash = processed.dhash
                embedding.ahash = processed.ahash
                embedding.orb_descriptors = processed.orb_descriptors
                embedding.orb_keypoints = processed.orb_keypoints
                embedding.orb_keypoints_count = processed.orb_keypoints_count
                embedding.detected_class = processed.detected_class
                embedding.detection_confidence = processed.detection_confidence
                db.add(embedding)

                await db.commit()
                processed_count += 1
                print(f"Processed {image.id}")
            except Exception as exc:
                await db.rollback()
                image.processing_error = str(exc)
                db.add(image)
                await db.commit()
                print(f"Failed {image.id}: {exc}")

        print(f"Processed {processed_count}/{len(images)} pending images.")


if __name__ == "__main__":
    asyncio.run(reprocess_pending_images())

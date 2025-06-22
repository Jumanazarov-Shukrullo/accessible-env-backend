import uuid
import datetime as dt

from fastapi import HTTPException, UploadFile, status

from app.domain.unit_of_work import UnitOfWork
from app.models.location_images_model import LocationImage
from app.models.user_model import User
from app.schemas.location_image_schema import LocationImageCreate
from app.utils.external_storage import MinioClient
from app.utils.kafka_client import KafkaProducerWrapper
from app.utils.rabbitmq_client import RabbitMQPublisherWrapper
from app.utils.logger import get_logger

logger = get_logger("image_service")


class ImageService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self._minio = MinioClient()
        self._kafka = KafkaProducerWrapper()
        self._mq = RabbitMQPublisherWrapper()

    # ------------------------------------------------------------------
    def generate_upload_url(self, location_id: str, filename: str, user: User):
        object_name = f"{location_id}/{uuid.uuid4().hex}_{filename}"
        url = self._minio.presigned_put_url(object_name)

        # Store DB placeholder so we know expected object
        with self.uow:
            img = LocationImage(
                location_id=location_id, image_url=object_name, position=0
            )
            self.uow.location_images.add(img)
            self.uow.commit()

        # Emit events
        self._kafka.send(
            "image.upload.requested",
            {
                "location_id": location_id,
                "image_url": object_name,
                "user_id": user.user_id,
            },
        )
        self._mq.publish(
            "image_uploaded_queue",
            {"location_id": location_id, "image_url": object_name},
        )
        get_url = self._minio.presigned_get_url(object_name)
        return {
            "upload_url": url,
            "object_name": object_name,
            "get_url": get_url,
        }

    def get_presigned_url(self, location_id: str, filename: str):
        object_name = f"{location_id}/{uuid.uuid4().hex}_{filename}"
        url = self._minio.presigned_put_url(object_name)
        return {"upload_url": url, "object_name": object_name}

    def register_metadata(
        self, location_id: str, payload: LocationImageCreate
    ):
        with self.uow:
            img = self.uow.location_images.get_by_object_name_and_loc(
                location_id, payload.image_url
            )
            if not img:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Image placeholder not found",
                )
            img.description = payload.description
            img.position = payload.position
            updated = self.uow.location_images.update(img)
            self.uow.commit()
            return updated

    def upload_images_direct(self, location_id: str, files: list[UploadFile], user: User) -> list[dict]:
        """
        Direct image upload for location images without presigned URLs.
        """
        with self.uow:
            # Verify location exists by trying to get it
            from app.services.location_service import LocationService
            location_service = LocationService(self.uow)
            location = location_service.get_location_detail(location_id)
            if not location:
                raise HTTPException(
                    status_code=404, detail="Location not found"
                )

            # Check permissions - only admins can upload location images
            if user.role_id not in (1, 2):  # Superadmin or Admin
                raise HTTPException(
                    status_code=403, detail="Admin access required to upload location images"
                )

            uploaded_images = []
            for file in files:
                try:
                    # Validate file type
                    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
                    if file.content_type not in allowed_types:
                        logger.warning(f"Invalid file type: {file.content_type}")
                        continue

                    # Generate a unique object key
                    file_extension = (
                        file.filename.split(".")[-1]
                        if file.filename and "." in file.filename
                        else "jpg"
                    )
                    object_key = f"location_images/{location_id}/{uuid.uuid4().hex}.{file_extension}"

                    # Upload file to MinIO
                    self._minio.upload_file(object_key, file)

                    # Create image metadata in database
                    image = LocationImage(
                        location_id=location_id,
                        image_url=object_key,
                        description=f"Image for location {location_id}",
                        position=0,
                        created_at=dt.datetime.now()
                    )

                    self.uow.location_images.add(image)
                    self.uow.commit()
                    self.uow.db.refresh(image)

                    # Get the public URL for the uploaded image
                    public_url = self._minio.get_public_url(object_key)

                    uploaded_images.append({
                        "image_id": image.image_id,
                        "image_url": public_url,
                        "description": image.description,
                        "uploaded_at": image.created_at.isoformat() if image.created_at else None
                    })

                except Exception as e:
                    logger.error(f"Failed to upload {file.filename}: {str(e)}")
                    # Continue with other files
                    continue

            if not uploaded_images:
                raise HTTPException(
                    status_code=400, detail="No images were successfully uploaded"
                )

            return uploaded_images

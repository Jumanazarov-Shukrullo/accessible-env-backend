import uuid

from fastapi import HTTPException, status

from app.domain.unit_of_work import UnitOfWork
from app.models.location_images_model import LocationImage
from app.models.user_model import User
from app.schemas.location_image_schema import LocationImageCreate
from app.utils.external_storage import MinioClient
from app.utils.kafka_client import KafkaProducerWrapper
from app.utils.rabbitmq_client import RabbitMQPublisherWrapper


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
            img = LocationImage(location_id=location_id, image_url=object_name, position=0)
            self.uow.location_images.add(img)
            self.uow.commit()

        # Emit events
        self._kafka.send(
            "image.upload.requested", {"location_id": location_id, "image_url": object_name, "user_id": user.user_id}
        )
        self._mq.publish("image_uploaded_queue", {"location_id": location_id, "image_url": object_name})
        get_url = self._minio.presigned_get_url(object_name)
        return {"upload_url": url, "object_name": object_name, "get_url": get_url}

    def get_presigned_url(self, location_id: str, filename: str):
        object_name = f"{location_id}/{uuid.uuid4().hex}_{filename}"
        url = self._minio.presigned_put_url(object_name)
        return {"upload_url": url, "object_name": object_name}

    def register_metadata(self, location_id: str, payload: LocationImageCreate):
        with self.uow:
            img = self.uow.location_images.get_by_object_name_and_loc(location_id, payload.image_url)
            if not img:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image placeholder not found")
            img.description = payload.description
            img.position = payload.position
            updated = self.uow.location_images.update(img)
            self.uow.commit()
            return updated

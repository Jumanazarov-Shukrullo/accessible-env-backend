from app.utils.cache import cache
from app.utils.external_storage import MinioClient
from app.utils.rabbitmq_client import RabbitMQWorker


def on_image_uploaded(payload: dict):
    object_name = payload["image_url"]
    # For demo, create a thumbnail or audit log (stub)
    print(f"[worker] image uploaded → {object_name}")
    # Invalidate Redis cache for that location gallery
    cache.invalidate(f"gallery:{payload['location_id']}")


if __name__ == "__main__":
    RabbitMQWorker("image_uploaded_queue", on_image_uploaded).start()

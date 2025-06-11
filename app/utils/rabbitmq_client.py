import json
import logging
import pika

from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQPublisherWrapper:
    def __init__(self):
        try:
            params = pika.URLParameters(settings.messaging.rabbitmq_url)
            self._conn = pika.BlockingConnection(params)
            self._chan = self._conn.channel()
        except Exception as e:
            logger.warning(f"RabbitMQ unavailable ({e!r}), continuing without messaging")
            self._conn = None
            self._chan = None

    def publish(self, queue_name: str, message: dict):
        if not self._chan:
            return
        try:
            self._chan.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(content_type="application/json"),
            )
        except Exception as e:
            logger.error(f"Failed to publish to {queue_name}: {e}")


class RabbitMQWorker:
    """Simple blocking worker; production use Celery or aio‑pika."""

    def __init__(self, queue: str, callback):
        params = pika.URLParameters(settings.messaging.rabbitmq_url)
        self._conn = pika.BlockingConnection(params)
        self._chan = self._conn.channel()
        self._chan.queue_declare(queue=queue, durable=True)
        self._chan.basic_consume(queue, self._wrap(callback), auto_ack=False)

    def _wrap(self, fn):
        import json

        def inner(ch, method, properties, body):
            try:
                fn(json.loads(body))
                ch.basic_ack(method.delivery_tag)
            except Exception as e:
                ch.basic_nack(method.delivery_tag, requeue=False)

        return inner

    def start(self):
        self._chan.start_consuming()

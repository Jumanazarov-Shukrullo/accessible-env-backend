import json
import logging

from kafka import KafkaProducer, KafkaConsumer, errors as kafka_errors

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerWrapper:
    def __init__(self, *args, **kwargs):
        try:
            self._producer = KafkaProducer(*args, **kwargs)
        except kafka_errors.NoBrokersAvailable:
            logger.warning("Kafka brokers unreachable—continuing without events")
            self._producer = None

    def send(self, topic: str, value: dict):
        if not self._producer:
            return
        try:
            self._producer.send(topic, value=value)
        except Exception as e:
            logger.error(f"Failed to send Kafka message to {topic}: {e}")


class KafkaConsumerWrapper:
    def __init__(self, topic: str, group_id: str):
        self._consumer = KafkaConsumer(
            topic,
            bootstrap_servers=settings.messaging.kafka_bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode()),
        )

    def __iter__(self):
        return iter(self._consumer)

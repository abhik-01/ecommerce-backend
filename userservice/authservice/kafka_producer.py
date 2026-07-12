import json
import logging
from datetime import datetime, UTC
from django.conf import settings

logger = logging.getLogger(__name__)


def publish_event(topic: str, payload: dict) -> None:
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        )
        producer.send(topic, payload)
        producer.flush()
        producer.close()
        logger.info("Published event to topic '%s'", topic)
    except Exception as exc:
        logger.warning("Kafka publish failed (topic=%s): %s", topic, exc)


def publish_user_registered(user_id: int, email: str) -> None:
    publish_event('user.registered', {
        'event_type': 'user.registered',
        'timestamp': datetime.now(UTC).isoformat(),
        'service': 'userservice',
        'payload': {'user_id': user_id, 'email': email},
    })

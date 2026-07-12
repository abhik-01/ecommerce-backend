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


def publish_order_created(order_id: int, user_id: int, total_amount: str, items: list) -> None:
    publish_event('order.created', {
        'event_type': 'order.created',
        'timestamp': datetime.now(UTC).isoformat(),
        'service': 'orderservice',
        'payload': {
            'order_id': order_id,
            'user_id': user_id,
            'total_amount': total_amount,
            'items': items,
        },
    })


def publish_order_status_updated(order_id: int, user_id: int, status: str) -> None:
    publish_event('order.status.updated', {
        'event_type': 'order.status.updated',
        'timestamp': datetime.now(UTC).isoformat(),
        'service': 'orderservice',
        'payload': {
            'order_id': order_id,
            'user_id': user_id,
            'status': status,
        },
    })

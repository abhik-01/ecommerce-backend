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


def publish_payment_completed(payment_id: int, order_id: int, amount: str, currency: str) -> None:
    publish_event('payment.completed', {
        'event_type': 'payment.completed',
        'timestamp': datetime.now(UTC).isoformat(),
        'service': 'paymentservice',
        'payload': {
            'payment_id': payment_id,
            'order_id': order_id,
            'amount': amount,
            'currency': currency,
        },
    })


def publish_payment_failed(payment_id: int, order_id: int, reason: str = '') -> None:
    publish_event('payment.failed', {
        'event_type': 'payment.failed',
        'timestamp': datetime.now(UTC).isoformat(),
        'service': 'paymentservice',
        'payload': {
            'payment_id': payment_id,
            'order_id': order_id,
            'reason': reason,
        },
    })

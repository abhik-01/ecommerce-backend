import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

TOPICS = ['payment.completed', 'payment.failed']


def handle_payment_completed(payload: dict) -> None:
    from .models import Order
    order_id = payload.get('order_id')
    updated = Order.objects.filter(id=order_id).update(
        status='CONFIRMED', payment_id=payload.get('payment_id')
    )
    if updated:
        logger.info("Order %s marked CONFIRMED after payment", order_id)
    else:
        logger.warning("payment.completed for unknown order_id=%s", order_id)


def handle_payment_failed(payload: dict) -> None:
    from .models import Order
    order_id = payload.get('order_id')
    updated = Order.objects.filter(id=order_id).update(status='CANCELLED')
    if updated:
        logger.info("Order %s marked CANCELLED after payment failure", order_id)
    else:
        logger.warning("payment.failed for unknown order_id=%s", order_id)


EVENT_HANDLERS = {
    'payment.completed': handle_payment_completed,
    'payment.failed': handle_payment_failed,
}


def run_consumer() -> None:
    from kafka import KafkaConsumer

    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id='orderservice-group',
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    )

    logger.info("Order consumer started. Listening on topics: %s", TOPICS)

    for message in consumer:
        try:
            data = message.value
            event_type = data.get('event_type', '')
            payload = data.get('payload', {})
            handler = EVENT_HANDLERS.get(event_type)
            if handler:
                logger.info("Processing event '%s'", event_type)
                handler(payload)
            else:
                logger.debug("No handler for event type '%s'", event_type)
        except Exception as exc:
            logger.error("Error processing Kafka message: %s", exc)

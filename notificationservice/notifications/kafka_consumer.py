import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def run_consumer() -> None:
    from kafka import KafkaConsumer
    from .services import EVENT_HANDLERS

    consumer = KafkaConsumer(
        *settings.KAFKA_TOPICS,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    )

    logger.info(
        "Notification consumer started. Listening on topics: %s",
        settings.KAFKA_TOPICS,
    )

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

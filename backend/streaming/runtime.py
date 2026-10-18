"""Acknowledged publishing, bounded retries and explicit consumer commits."""

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
import signal
import time
from uuid import NAMESPACE_URL, uuid5

from confluent_kafka import Consumer, KafkaException, Producer
from pydantic import ValidationError

from src.prediction_store import EventConflict

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StreamSettings:
    bootstrap_servers: str = "localhost:9095"
    customer_topic: str = "customer-events"
    prediction_topic: str = "churn-predictions"
    dead_letter_topic: str = "customerpulse-dead-letter"
    inference_group: str = "customerpulse-inference-v1"
    analytics_group: str = "customerpulse-analytics-v1"
    attempts: int = 3
    retry_delay: float = 0.5
    delivery_timeout: float = 20

    def __post_init__(self):
        if self.attempts < 1 or self.retry_delay < 0 or self.delivery_timeout <= 0:
            raise ValueError("Invalid stream retry configuration")
        if len({self.customer_topic, self.prediction_topic, self.dead_letter_topic}) != 3:
            raise ValueError("Stream input, output and dead-letter topics must differ")

    @classmethod
    def from_env(cls):
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9095"),
            customer_topic=os.getenv("KAFKA_CUSTOMER_TOPIC", "customer-events"),
            prediction_topic=os.getenv("KAFKA_PREDICTION_TOPIC", "churn-predictions"),
            dead_letter_topic=os.getenv("KAFKA_DEAD_LETTER_TOPIC", "customerpulse-dead-letter"),
            inference_group=os.getenv("KAFKA_INFERENCE_GROUP", "customerpulse-inference-v1"),
            analytics_group=os.getenv("KAFKA_ANALYTICS_GROUP", "customerpulse-analytics-v1"),
            attempts=int(os.getenv("STREAM_MAX_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("STREAM_RETRY_DELAY", "0.5")),
        )


def create_producer(settings):
    return Producer({
        "bootstrap.servers": settings.bootstrap_servers, "enable.idempotence": True,
        "acks": "all", "delivery.timeout.ms": int(settings.delivery_timeout * 1000) - 1000,
        "request.timeout.ms": 5000, "retry.backoff.ms": 250,
    })


def create_consumer(settings, group):
    return Consumer({
        "bootstrap.servers": settings.bootstrap_servers, "group.id": group,
        "auto.offset.reset": "earliest", "enable.auto.commit": False,
        "enable.auto.offset.store": False, "max.poll.interval.ms": 300000,
        "session.timeout.ms": 10000, "allow.auto.create.topics": False,
    })


def publish_confirmed(producer, topic, key, payload, timeout=20):
    delivered = []
    def callback(error, message):
        delivered.append(error)
    producer.produce(topic, key=str(key).encode(),
                     value=json.dumps(payload, sort_keys=True, allow_nan=False).encode(),
                     on_delivery=callback)
    pending = producer.flush(timeout)
    if pending or not delivered or delivered[0] is not None:
        raise RuntimeError("Kafka did not confirm delivery")


def _dead_letter(message, error, stage, settings):
    location = f"{message.topic()}:{message.partition()}:{message.offset()}:{stage}"
    return {
        "schema_version": 1, "dead_letter_id": str(uuid5(NAMESPACE_URL, location)),
        "stage": stage, "original_topic": message.topic(),
        "original_partition": message.partition(), "original_offset": message.offset(),
        "key_base64": base64.b64encode(message.key() or b"").decode(),
        "value_base64": base64.b64encode(message.value() or b"").decode(),
        "error_type": type(error).__name__, "error": str(error)[:2000],
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }


def process_message(message, handler, consumer, producer, settings, stage, sleep=time.sleep):
    """Never advance past a transient failure or an unacknowledged dead letter."""
    permanent = None
    for attempt in range(settings.attempts):
        try:
            handler(message.value())
            break
        except (ValidationError, EventConflict) as error:
            permanent = error
            break
        except Exception:
            if attempt + 1 == settings.attempts:
                raise  # Infrastructure failures remain uncommitted for restart.
            logger.warning("%s processing failed; retry %s/%s", stage, attempt + 1, settings.attempts)
            sleep(settings.retry_delay * 2 ** attempt)
    if permanent is not None:
        dead = _dead_letter(message, permanent, stage, settings)
        # Broker retries and delivery confirmation apply to the DLQ as well.
        publish_confirmed(producer, settings.dead_letter_topic, dead["dead_letter_id"], dead,
                          settings.delivery_timeout)
        logger.warning("%s rejected %s:%s:%s (%s)", stage, message.topic(),
                       message.partition(), message.offset(), type(permanent).__name__)
    offsets = consumer.commit(message=message, asynchronous=False)
    for offset in offsets or []:
        if offset.error:
            raise KafkaException(offset.error)


def run_consumer(settings, group, topic, handler, stage):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    consumer, producer = create_consumer(settings, group), create_producer(settings)
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    consumer.subscribe([topic])
    logger.info("%s consuming %s with group %s", stage, topic, group)
    try:
        while not stopping:
            message = consumer.poll(1)
            if message is None:
                continue
            if message.error():
                raise KafkaException(message.error())
            process_message(message, handler, consumer, producer, settings, stage)
    finally:
        consumer.close()
        producer.flush(settings.delivery_timeout)

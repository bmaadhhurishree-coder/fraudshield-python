"""At-least-once Kafka delivery of durable transaction events.

A crash after Kafka acknowledgement but before database commit can resend an event.
Consumers MUST deduplicate using event_id; this is not exactly-once delivery.
"""
import json
import logging
import os
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, OutboxEvent, make_engine, now_utc

log = logging.getLogger(__name__)
TOPIC = "fraudshield.transactions.v1"


def publish_batch(session: Session, producer, *, batch_size: int = 100) -> int:
    """Publish a small batch, recording success only after broker acknowledgement.

    Single publisher expected for MVP; parallel deployment requires DB claiming
    (e.g. SELECT ... FOR UPDATE SKIP LOCKED) and a lease/ownership strategy.
    """
    pending = session.scalars(
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at, OutboxEvent.event_id)
        .limit(batch_size)
    ).all()
    delivered = 0
    for event in pending:
        envelope = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "occurred_at": event.created_at.isoformat(),
            "payload": json.loads(event.payload_json),
        }
        try:
            producer.produce(
                TOPIC,
                key=event.transaction_id.encode(),
                value=json.dumps(envelope, sort_keys=True).encode(),
            )
            producer.flush(timeout=10)
            # flush() returns the number of outstanding messages; delivery callbacks
            # surface broker errors. A callback is required to confirm delivery.
        except Exception:
            log.exception("Kafka publish failed for event %s", event.event_id)
            session.rollback()
            break
        event.published_at = now_utc()
        session.commit()
        delivered += 1
    return delivered


def run_publisher():
    from confluent_kafka import Producer

    engine = make_engine()
    Base.metadata.create_all(engine)
    producer = Producer({"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                         "enable.idempotence": True, "acks": "all"})
    while True:
        with Session(engine) as session:
            count = publish_batch(session, producer)
        if not count:
            time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_publisher()
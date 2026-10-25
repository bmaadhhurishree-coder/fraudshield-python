"""At-least-once publication of transaction outbox records to Kafka."""
import json
import logging
import os
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Base, OutboxEvent, OutboxReceipt, make_engine, now_utc

log = logging.getLogger(__name__)
TOPIC = "fraudshield.transactions.v1"


def publish_batch(session: Session, producer, *, batch_size: int = 100) -> int:
    """Send pending events and record delivery receipts after Kafka acknowledgements.

    Deploy one publisher process until DB row claims/leases are implemented.
    A crash before recording the receipt can cause duplicate delivery.
    """
    pending = session.scalars(
        select(OutboxEvent)
        .outerjoin(OutboxReceipt, OutboxReceipt.event_id == OutboxEvent.event_id)
        .where(OutboxReceipt.event_id.is_(None))
        .order_by(OutboxEvent.created_at, OutboxEvent.event_id)
        .limit(batch_size)
    ).all()
    delivered = 0
    for event in pending:
        envelope = {"event_id": event.event_id, "event_type": event.event_type,
                    "occurred_at": event.created_at.isoformat(),
                    "payload": json.loads(event.payload_json)}
        result = {"acknowledged": False, "error": None}

        def on_delivery(error, _message):
            result["error"] = error
            result["acknowledged"] = error is None

        try:
            producer.produce(TOPIC, key=event.transaction_id.encode(),
                             value=json.dumps(envelope, sort_keys=True).encode(),
                             on_delivery=on_delivery)
            outstanding = producer.flush(timeout=10)
            if outstanding or not result["acknowledged"] or result["error"]:
                raise RuntimeError(f"Kafka delivery not confirmed: {result['error']}")
            session.add(OutboxReceipt(event_id=event.event_id, published_at=now_utc()))
            session.commit()
            delivered += 1
        except Exception:
            session.rollback()
            log.exception("Kafka delivery failed for %s", event.event_id)
            break
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

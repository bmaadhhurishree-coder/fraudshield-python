"""Kafka publishing contract tests with a fake broker producer."""
import json
from uuid import uuid4

from sqlalchemy.orm import Session

from fraudshield.db import Base, OutboxEvent, OutboxReceipt, make_engine, now_utc
from fraudshield.outbox import publish_batch


class ProducerStub:
    def __init__(self, *, error=None):
        self.error = error
        self.calls = []
        self.callback = None

    def produce(self, topic, *, key, value, on_delivery):
        self.calls.append((topic, key, json.loads(value)))
        self.callback = on_delivery

    def flush(self, timeout):
        self.callback(self.error, object())
        return 0


def test_outbox_publish_and_receipt(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'outbox.db'}")
    Base.metadata.create_all(engine)
    event_id = str(uuid4())
    with Session(engine) as session:
        # The publisher only needs outbox fields; SQLite FK checks are off in this fixture.
        session.add(OutboxEvent(
            event_id=event_id,
            transaction_id=str(uuid4()),
            event_type="transaction.scored.v1",
            payload_json='{"transaction_id": "tx", "decision": "review"}',
            created_at=now_utc(),
        ))
        session.commit()
        producer = ProducerStub()
        assert publish_batch(session, producer) == 1
        assert producer.calls[0][2]["event_id"] == event_id
        assert session.get(OutboxReceipt, event_id) is not None
        assert publish_batch(session, producer) == 0


def test_kafka_failure_preserves_pending_event(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'outbox.db'}")
    Base.metadata.create_all(engine)
    event_id = str(uuid4())
    with Session(engine) as session:
        session.add(OutboxEvent(
            event_id=event_id, transaction_id=str(uuid4()),
            event_type="transaction.scored.v1", payload_json="{}",
            created_at=now_utc(),
        ))
        session.commit()
        assert publish_batch(session, ProducerStub(error=RuntimeError("broker unavailable"))) == 0
        assert session.get(OutboxReceipt, event_id) is None
        assert publish_batch(session, ProducerStub()) == 1

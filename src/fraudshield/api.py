"""Transaction intake API with durable, idempotent risk decisions and an outbox."""
import hashlib
import json
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import Base, OutboxEvent, TransactionRow, make_engine, now_utc
from .models import HealthResponse, RiskResult, TransactionCreate, TransactionResponse
from .rules import score_transaction


def payload_fingerprint(tx: TransactionCreate) -> str:
    normalized = tx.model_dump(mode="json", exclude={"transaction_id"})
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


def to_response(row: TransactionRow) -> TransactionResponse:
    return TransactionResponse(
        transaction_id=UUID(row.transaction_id),
        account_id=row.account_id,
        amount=row.amount,
        currency=row.currency,
        country=row.country,
        risk=RiskResult(
            score=row.score,
            decision=row.decision,
            reasons=json.loads(row.reasons_json),
            rule_version=row.rule_version,
        ),
        created_at=row.created_at,
    )


def create_app(database_url: str | None = None) -> FastAPI:
    engine = make_engine(database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        Base.metadata.create_all(engine)  # MVP only; replace with Alembic migrations before deploy
        yield
        engine.dispose()

    app = FastAPI(title="FraudShield", version="0.1.0", lifespan=lifespan)

    @app.get("/health", response_model=HealthResponse)
    def health():
        return HealthResponse(status="ok")

    @app.post("/api/v1/transactions", response_model=TransactionResponse, status_code=201)
    def create_transaction(tx: TransactionCreate):
        key = str(tx.transaction_id)
        fingerprint = payload_fingerprint(tx)
        with Session(engine) as session:
            existing = session.get(TransactionRow, key)
            if existing:
                if existing.payload_hash != fingerprint:
                    raise HTTPException(409, "transaction_id already used with different payload")
                return to_response(existing)
            result = score_transaction(tx)
            timestamp = now_utc()
            row = TransactionRow(
                transaction_id=key, account_id=tx.account_id, amount=tx.amount,
                currency=tx.currency, country=tx.country, payload_hash=fingerprint,
                score=result.score, decision=result.decision.value,
                reasons_json=json.dumps(result.reasons), rule_version=result.rule_version,
                created_at=timestamp,
            )
            session.add(row)
            session.add(OutboxEvent(
                event_id=str(uuid4()), transaction_id=key,
                event_type="transaction.scored.v1",
                payload_json=json.dumps({"transaction_id": key, "score": result.score,
                                         "decision": result.decision.value, "reasons": result.reasons}),
                created_at=timestamp,
            ))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.get(TransactionRow, key)
                if existing and existing.payload_hash == fingerprint:
                    return to_response(existing)
                raise HTTPException(409, "transaction_id already used with different payload") from None
            session.refresh(row)
            return to_response(row)

    @app.get("/api/v1/transactions/{transaction_id}/risk", response_model=RiskResult)
    def get_risk(transaction_id: UUID):
        with Session(engine) as session:
            row = session.get(TransactionRow, str(transaction_id))
            if row is None:
                raise HTTPException(404, "transaction not found")
            return to_response(row).risk

    return app


app = create_app()
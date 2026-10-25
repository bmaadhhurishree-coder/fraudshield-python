from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fraudshield.api import create_app
from fraudshield.db import OutboxEvent, make_engine


@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    app = create_app(url)
    app.state.database_url = url
    with TestClient(app) as client:
        yield client


def payload():
    return {"transaction_id": str(uuid4()), "account_id": "customer-123",
            "amount": "4800.00", "country": "GB", "home_country": "US",
            "device_id": "new-phone", "known_device": False, "transactions_last_hour": 12}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_transaction_creation_and_get_risk(client):
    data = payload()
    response = client.post("/api/v1/transactions", json=data)
    assert response.status_code == 201
    assert response.json()["risk"]["decision"] == "decline"
    risk = client.get(f"/api/v1/transactions/{data['transaction_id']}/risk")
    assert risk.status_code == 200
    assert risk.json()["score"] == 100


def test_idempotent_retry_does_not_duplicate_event(client):
    data = payload()
    assert client.post("/api/v1/transactions", json=data).status_code == 201
    assert client.post("/api/v1/transactions", json=data).status_code == 201
    with Session(make_engine(str(client.app.state.database_url))) as session:
        assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 1


def test_conflicting_id_returns_409(client):
    data = payload()
    client.post("/api/v1/transactions", json=data)
    data["amount"] = "12.00"
    assert client.post("/api/v1/transactions", json=data).status_code == 409


def test_invalid_input_and_missing_transaction(client):
    data = payload()
    data["amount"] = "-5"
    assert client.post("/api/v1/transactions", json=data).status_code == 422
    assert client.get(f"/api/v1/transactions/{uuid4()}/risk").status_code == 404
# FraudShield Python 🛡️

**Explainable fraud-risk decisions with an idempotent REST API and transactional event outbox.**

> **v0.2 development prototype — synthetic data only.** Kafka publishing and Temporal workflows have initial implementations. End-to-end integration has not yet been validated. MFA, OAuth2 M2M, and machine learning are planned.

## Features
- FastAPI and Pydantic models with generated OpenAPI documentation.
- Explainable risk rules for amount, geography, device novelty and transaction velocity.
- Decisions: `allow` (score < 50), `review` (50–89), `decline` (90–100).
- Idempotency by transaction UUID: identical retries return the original result; conflicts return HTTP 409.
- Persist transaction decisions and `transaction.scored.v1` event records atomically.
- SQLite local mode and PostgreSQL with Docker Compose; unit/API tests and GitHub Actions.

**Security:** Currently unauthenticated. Do not expose to public networks or use real banking data. Feature signals in this MVP are caller-provided, not independently verified. Kafka publication requires a separately configured Kafka broker and publisher; Temporal requires a server and worker. Neither is enabled by the default Compose configuration.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn fraudshield.api:app --reload
```

Open [interactive API docs](http://localhost:8000/docs).

Run against PostgreSQL instead:

```bash
docker compose up --build
```

Submit a sample suspicious transaction:

```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H 'Content-Type: application/json' \
  --data @examples/high_risk.json
```

The included synthetic example yields `score: 100` and `decision: decline`.

## Endpoints

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness (not database readiness) |
| POST | `/api/v1/transactions` | Score and store a transaction |
| GET | `/api/v1/transactions/{transaction_id}/risk` | Retrieve a stored decision |

## Architecture

```mermaid
flowchart LR
    Simulator[Transaction Simulator] --> FastAPI[FastAPI Scoring API]
    FastAPI --> Rules[Explainable Rules Engine]
    FastAPI --> DB[(SQLite or PostgreSQL)]
    FastAPI --> Outbox[(Transactional Outbox)]
    Outbox -->|separate publisher| Kafka[Kafka Events]
    Kafka -->|worker consumer| Temporal[Temporal Investigations]
    Identity[Keycloak MFA and OAuth2 M2M] -. planned .-> FastAPI
```

Read [Architecture Decisions](docs/ARCHITECTURE.md), [Security](docs/SECURITY.md), and [Roadmap](docs/ROADMAP.md).

## Quality checks

```bash
ruff check .
pytest -q
```

Contributions should include tests and updated docs for behavior changes. MIT licensed; see [LICENSE](LICENSE).

## Experimental Kafka / Temporal services

Default `docker compose up --build` runs only the API and PostgreSQL. Configure an external or local Kafka broker and Temporal development server before starting these workers:

```bash
export DATABASE_URL=postgresql+psycopg://fraudshield:localdemo@localhost:5432/fraudshield
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export TEMPORAL_ADDRESS=localhost:7233
python -m fraudshield.outbox
python -m fraudshield.worker
```

Create Kafka topic `fraudshield.transactions.v1` before running. Start the publisher and worker in **different terminals**. Only transactions with decision `review` start a Temporal investigation. The worker uses a deterministic workflow ID to reduce duplicate workflow creation on Kafka redelivery. Production-grade inbox deduplication, access-controlled analyst decisions, and end-to-end integration tests are not yet available.

# Architecture and Design Decisions

## v0.1 Overview
Synchronous FastAPI handles synthetic transactions, determines risk using deterministic rules, and atomically persists transactions alongside outbox event records. The transaction UUID is the idempotency key.

## ADR-001: synchronous scoring; asynchronous investigations
Keep low-latency scoring on the request path. Kafka distribution and Temporal investigations are future milestones, *not* implemented components. Trade-off: synchronous scoring must have strict timeouts and bounded complexity.

## ADR-002: transactional outbox
Persist decisions and pending events within the same SQL transaction. A future publisher will forward events with at-least-once semantics; consumers must deduplicate event IDs. An outbox alone does not guarantee delivery.

## ADR-003: modular service before microservices
Build with typed schemas, independent rules, and persistence layers, then split workloads based on measurable scaling requirements.

## Known limitations
- SQL tables are created on startup rather than through Alembic migrations.
- Client-provided velocity and device flags are not verified.
- No authentication, Kafka publication, Temporal, ML, or analyst UI yet.
- SQLite test coverage does not replace PostgreSQL integration or concurrency testing.
- No production SLO, load testing, or fraud detection metrics.
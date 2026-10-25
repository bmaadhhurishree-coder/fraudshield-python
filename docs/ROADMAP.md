# Implementation Roadmap

- [x] v0.1 FastAPI + explainable rules + SQL persistence + transactional outbox + unit/API tests + CI
- [x] v0.2 initial Kafka outbox publisher and Temporal investigation workflow (integration testing, event schema registry and consumer inbox remain TODO)
- [ ] v0.3 hardened Temporal reviews: secure analyst API, Updates, activity retries, integration tests and consumer inbox
- [ ] v0.4 Keycloak OIDC MFA and OAuth2 M2M client-credentials authorization
- [ ] v0.5 Redis-backed real-time velocity features
- [ ] v0.6 ML baseline, temporal holdout evaluation, model registry and monitoring
- [ ] v0.7 Analyst interface, distributed observability, load tests and IaC

Each milestone requires tests, failure-mode documentation and a reproducible local demo.
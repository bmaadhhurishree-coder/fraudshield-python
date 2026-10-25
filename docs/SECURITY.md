# Security

**Do not deploy v0.1 publicly or process real payment or personal financial data.** No authentication is currently enforced.

## Planned human auth
Keycloak with OIDC, phishing-resistant WebAuthn/passkeys or TOTP, case-specific authorization, step-up verification for sensitive operations and audit trails.

## Planned machine identity
OAuth 2.0 client credentials; validate JWT issuer, audience, expiry, signature and scopes. Rotate credentials; do not persist tokens in Temporal histories.

## Additional hardening
Rate limiting, request size limits, trace redaction, key management, immutable audit records, replay and injection testing, and fail-safe defaults.

Only synthetic demo transaction data belongs in fixtures and logs.
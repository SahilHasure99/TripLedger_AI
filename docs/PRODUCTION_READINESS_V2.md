# TripLedger AI V2 — Security, Privacy and Integration Readiness

## Added in V2
- `GET /api/auth/me`: current authenticated account.
- `POST /api/auth/logout`: revokes the presented bearer token until its expiry.
- `GET /api/auth/export`: exports account profile, trips and payment metadata (never credentials or card data).
- `DELETE /api/auth/account`: permanently deletes the account and associated trip/payment ledger rows.
- Revocation records are stored as SHA-256 token digests; raw bearer tokens are not persisted.
- JWTs carry a random token identifier (`jti`) and validation requires it.

## Run locally (Windows PowerShell)
1. Copy `.env.example` to `.env`.
2. Generate a 32+ byte secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"` and set it as `JWT_SECRET`.
3. Keep PayPal credentials empty until a PayPal Developer Sandbox app is created. Add the Sandbox client ID, secret and webhook ID only to the local `.env` file.
4. Create and activate a virtual environment, install requirements, then run:
   - `python -m uvicorn backend.main:app --reload --port 8000`
   - `python -m streamlit run app.py`
5. API docs are available at `http://127.0.0.1:8000/docs` during local development.

## Payment truthfulness
- Checkout requires real PayPal Sandbox credentials and a registered webhook ID for verified webhook processing.
- A missing credential does not produce a fake successful payment; the API returns a configuration error.
- The server derives amount/currency from the user's saved trip budget, verifies capture amount/currency and uses PayPal request IDs for idempotency.
- Sandbox transactions are test transactions, not real-money transactions. No card data is stored by this application.

## Still required before public production launch
- Real Sandbox checkout + webhook test using the owner's credentials (cannot be performed in this package build without them).
- PostgreSQL deployment/migrations, distributed rate limiting, email verification and password reset.
- Production secret manager, HTTPS/reverse proxy configuration, production CORS allowlist and deployment-specific backups/monitoring.
- Independent dependency/SAST/DAST scans and browser E2E/load tests in the target deployment.
- Privacy notice, jurisdiction-specific retention policy and legal review.

This release is a locally runnable hackathon MVP, not a certification of production security or zero defects.

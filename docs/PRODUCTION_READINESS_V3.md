# TripLedger AI V3 — Implemented security additions and release gates

## Implemented in this increment

- Optional email verification (`EMAIL_VERIFICATION_REQUIRED=true`) with 30-minute, one-use tokens stored as SHA-256 digests.
- Email verification page served by FastAPI at `/api/auth/account/verify-email`; the user must press the confirmation button, so mail link preview scanners do not consume the token.
- Password reset email flow with generic anti-enumeration response, 30-minute one-use hashed tokens, and a simple password form at `/api/auth/account/reset-password`.
- Password reset increments the account token version, invalidating all existing access tokens for that account.
- Redis-backed fixed-window authentication rate limiting. Configure `REDIS_URL` to share limits across API workers. The in-process fallback is for local development only; `APP_ENV=production` fails closed if Redis is not configured or unavailable.
- CI workflow now runs tests, Python compilation, Bandit and pip-audit. CI scans are configured; they have not yet run on a hosted GitHub runner in this local build.

## Configure email verification and password reset

Set these values in the private local `.env` file:

```env
APP_ENV=development
EMAIL_VERIFICATION_REQUIRED=true
PUBLIC_APP_URL=http://localhost:8000
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=587
SMTP_USERNAME=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=no-reply@your-domain.example
SMTP_USE_TLS=true
```

For production, use your provider's real HTTPS public API base URL for `PUBLIC_APP_URL`, enforce TLS, and keep SMTP credentials in a secret manager. Never commit `.env`.

## Configure distributed rate limiting

Run Redis and set:

```env
APP_ENV=production
REDIS_URL=redis://localhost:6379/0
```

Use authenticated Redis with TLS and network restrictions in a real deployment. The default limit is eight requests per minute per client IP per authentication endpoint. Configure a trusted proxy before relying on forwarded client IPs; this implementation intentionally uses the direct ASGI client address and does not trust arbitrary forwarded headers.

## Still blocked / not certified in this package build

1. **PayPal end-to-end:** requires the project owner's PayPal Sandbox app credentials and registered webhook ID. Unit tests mock PayPal calls; no real Sandbox checkout/capture/webhook round-trip was run.
2. **PostgreSQL:** the runtime persistence adapter is still SQLite. PostgreSQL schema migrations and runtime adapter are not complete; do not set a PostgreSQL URL expecting it to work.
3. **Streamlit browser run:** Streamlit was not installed in the isolated build environment and network package installation was unavailable. The original Streamlit UI is preserved, but a browser-level smoke test is still required on the target Windows machine.
4. **Security scanners:** Bandit and pip-audit are configured in CI but were not installed/run locally in this build environment. Hosted CI must pass before release.
5. **Deployment:** HTTPS/reverse proxy, production CORS allowlist, secret manager, backups, monitoring, retention/legal review, DAST and load tests remain deployment-specific gates.

This project is a hackathon MVP with additional account-security flows. It is not a production security certification and cannot be represented as zero-defect.

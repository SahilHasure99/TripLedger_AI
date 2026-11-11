# TripLedger AI — API Reference
Base URL `http://127.0.0.1:8000` · Interactive docs at `/docs` · All protected routes need `Authorization: Bearer <token>`.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | – | Liveness + version |
| POST | `/api/auth/register` | – | Create account (returns token, or "check email" if verification is on) |
| POST | `/api/auth/login` | – | Obtain token |
| GET | `/api/auth/me` | ✔ | Current user |
| POST | `/api/auth/logout` | ✔ | Revoke current token |
| POST | `/api/auth/forgot-password` | – | Always returns the same message |
| POST | `/api/auth/reset-password` | – | JSON `{token,new_password}` or HTML form |
| GET/POST | `/api/auth/account/verify-email`, `/api/auth/verify-email` | – | One-time email verification |
| GET | `/api/auth/export` | ✔ | Download your data |
| DELETE | `/api/auth/account` | ✔ | Delete account + data |
| POST | `/api/trips` | ✔ | Save trip |
| GET | `/api/trips`, `/api/trips/{id}` | ✔ | List / fetch (own trips only) |
| POST | `/api/payments/orders` | ✔ | Create PayPal order for a saved trip budget |
| POST | `/api/payments/capture` | ✔ | Capture + verify |
| GET | `/api/payments` | ✔ | Ledger |
| POST | `/api/webhooks/paypal` | PayPal signature | Async confirmation |

## Conventions
* **Money** is sent as `amount_minor` (integer) + ISO `currency`. Two-decimal currencies: cents. **JPY / HUF / TWD: whole units.**
* **Idempotency**: `idempotency_key` (16–38 chars `[A-Za-z0-9._:-]`) — same key + same body returns the same order.
* **Errors**: `{"detail": "..."}`; `401` auth, `404` not yours/not found, `409` business rule (amount mismatch), `422` validation, `429` rate-limited, `502` PayPal failure, `503` not configured.

## Examples
```bash
curl -X POST :8000/api/auth/login -H 'Content-Type: application/json' \
     -d '{"email":"me@example.com","password":"correct horse battery"}'

curl -X POST :8000/api/trips -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
     -d '{"origin":"Pune","destination":"Tokyo","start_date":"2026-12-01","end_date":"2026-12-08",
          "travelers":2,"budget_amount":"1200.00","budget_currency":"USD"}'

curl -X POST :8000/api/payments/orders -H "Authorization: Bearer $T" -H 'Content-Type: application/json' \
     -d '{"trip_id":1,"amount_minor":120000,"currency":"USD","idempotency_key":"demo-key-0000000001"}'
```

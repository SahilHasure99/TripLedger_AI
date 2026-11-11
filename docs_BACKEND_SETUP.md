# TripLedger AI — Backend Foundation (V1)

This first development increment adds a separate FastAPI backend while leaving the existing TravelMate Streamlit UI and travel agents in place.

## Included

- SQLite persistence for local development (users, trips, payment orders, transactions, webhook events, audit log table).
- Registration and login with salted PBKDF2-SHA256 password hashes and signed, expiring bearer tokens.
- Authenticated trip create/list/detail endpoints with per-user ownership checks.
- PayPal Sandbox REST adapter: create order, capture order, and verify webhook signatures through PayPal's verification API.
- Payment amount/currency verification before a transaction is recorded.
- Idempotency keys for order creation and unique constraints for capture/event records.
- Health endpoint and automated tests.

## Windows PowerShell setup

From the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `JWT_SECRET` to a long random secret (at least 32 random characters). For PayPal Sandbox payment tests, also set `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and `PAYPAL_WEBHOOK_ID` from your PayPal Developer Dashboard. Keep these values private and never commit `.env`.

Start the API in one terminal:

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API health: `http://127.0.0.1:8000/health`  
Interactive API docs: `http://127.0.0.1:8000/docs`

Run existing and new tests:

```powershell
python -m pytest -q
```

## Initial API endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | No | API health |
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Login and obtain bearer token |
| POST | `/api/trips` | Yes | Create trip |
| GET | `/api/trips` | Yes | List the signed-in user's trips |
| GET | `/api/trips/{trip_id}` | Yes | Get an owned trip |
| POST | `/api/payments/orders` | Yes | Create a PayPal order |
| POST | `/api/payments/capture` | Yes | Capture and verify an owned order |
| GET | `/api/payments` | Yes | List the signed-in user's payment records |
| POST | `/api/webhooks/paypal` | PayPal signature | Verify and process PayPal events |

## Important safety and scope notes

- The backend deliberately has no fake-payment or fake-booking success path.
- PayPal calls use Sandbox by default. No real-money payment has been tested or enabled by this increment.
- A PayPal order is not a completed payment. The backend only records a completed capture after PayPal reports `COMPLETED` and the captured amount/currency match the server-side order.
- Configure the webhook URL in PayPal as `https://YOUR_PUBLIC_HOST/api/webhooks/paypal`, subscribe to `PAYMENT.CAPTURE.COMPLETED`, and set the resulting webhook ID in `.env`. A local machine needs a secure tunnel for PayPal to reach its webhook endpoint.
- This first increment uses SQLite for easy local setup. PostgreSQL support, production-grade refresh/revocation, rate limiting, monitoring, and full UI integration remain later milestones.
- The app's original Streamlit interface has not been redesigned in this increment.


## V3 account-security endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/auth/account/verify-email?token=...` | Displays a confirmation page; the user must press Verify. |
| POST | `/api/auth/verify-email?token=...` | Consumes a one-time verification token and activates the account. |
| POST | `/api/auth/forgot-password` | Requests a reset email; response does not reveal whether an account exists. |
| GET | `/api/auth/account/reset-password?token=...` | Displays a password reset form. |
| POST | `/api/auth/reset-password?token=...` | Consumes the one-time reset token and changes password. |

Set `EMAIL_VERIFICATION_REQUIRED=true` and SMTP settings to require verification. Set `REDIS_URL` for distributed authentication rate limits. See `docs/PRODUCTION_READINESS_V3.md` for configuration and remaining release gates.

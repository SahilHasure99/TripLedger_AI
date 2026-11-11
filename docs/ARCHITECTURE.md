# TripLedger AI — Architecture

## 1. System context
```mermaid
flowchart LR
  U[Traveller / Browser] -->|HTTP| ST[Streamlit UI :8501]
  ST -->|REST + Bearer token| API[FastAPI :8000]
  ST -->|in-process| AG[Agent layer]
  API --> DB[(SQLite WAL)]
  API -->|OAuth2 + Orders v2| PP[PayPal Sandbox]
  PP -->|signed webhook| API
  AG -->|HTTPS| OM[Open-Meteo weather]
  API -.optional.-> RD[(Redis rate limit)]
  API -.optional.-> SM[SMTP]
```

## 2. Layers
| Layer | Path | Responsibility |
|---|---|---|
| Presentation | `app.py`, `ui/theme.py`, `ui/tripledger_portal.py` | Pages, motion layer, API client, escaping |
| Planner (domain) | `agents/`, `utils/`, `tools/` | Coordinator orchestrates flight, hotel, weather and itinerary agents into a `TripPlan` dataclass |
| API | `backend/api/*` | Routers: auth, trips, payments, webhooks |
| Core | `backend/core/*` | Config, DB, token/password security, **money helpers** |
| Services | `backend/services/*` | PayPal client, SMTP, rate limiter |
| Persistence | `data/tripledger.db` | SQLite (WAL, foreign keys ON) |

## 3. Planner flow
```mermaid
sequenceDiagram
  participant UI as Streamlit form
  participant C as CoordinatorAgent
  participant F as Flight
  participant H as Hotel
  participant W as Weather
  participant I as Itinerary
  UI->>UI: validate_trip + fingerprint (dedupe)
  UI->>C: TripRequest
  C->>F: run()
  C->>H: run()
  C->>W: run() (Open-Meteo, fallback offline)
  C->>I: run(request, weather)
  C-->>UI: TripPlan
  UI->>UI: budget_breakdown + exports
```
Identical inputs reuse the cached plan in `st.session_state` (max 3 entries) to prevent double processing.

## 4. Payment flow (trust boundary is the server)
```mermaid
sequenceDiagram
  participant U as User
  participant S as Streamlit
  participant A as FastAPI
  participant P as PayPal
  U->>S: choose saved trip
  S->>A: POST /api/payments/orders {trip_id, amount_minor, currency, idempotency_key}
  A->>A: amount/currency MUST equal trip budget
  A->>P: create order (PayPal-Request-Id)
  P-->>A: order + approve link
  A-->>S: order_id, approval_url
  U->>P: approve in sandbox
  S->>A: POST /api/payments/capture {order_id}
  A->>P: capture
  A->>A: verify COMPLETED + amount + currency
  A->>A: INSERT OR IGNORE transaction (UNIQUE order_id)
  P-->>A: webhook PAYMENT.CAPTURE.COMPLETED (signature verified, event_id deduped)
```
Guarantees: the browser can never choose the payable amount; replayed capture/webhook calls cannot create a second ledger row (`UNIQUE` constraints + `INSERT OR IGNORE`); zero-decimal currencies use whole units.

## 5. Data model
```mermaid
erDiagram
  users ||--o{ trips : owns
  users ||--o{ payment_orders : places
  trips ||--o{ payment_orders : funds
  payment_orders ||--o| transactions : settles
  users ||--o{ email_action_tokens : receives
  users { int id PK  text email UK  text password_hash  int token_version }
  trips { int id PK  int user_id FK  text origin  text destination  text budget_amount  text budget_currency }
  payment_orders { int id PK  text paypal_order_id UK  int amount_minor  text currency  text status  text request_id UK }
  transactions { int id PK  int order_id UK  text paypal_capture_id UK  int amount_minor }
```
Also: `revoked_tokens`, `webhook_events (event_id UNIQUE)`, `audit_logs`.

## 6. Security model
| Threat | Control |
|---|---|
| Credential stuffing | PBKDF2 310k, per-IP limit 8/min on auth routes (Redis when configured), generic error text |
| Token theft/replay | 60-min expiry, `jti`, server-side revocation list, `token_version` invalidation after password reset |
| Cross-user access | Every query filtered by `user_id`; foreign trip/order → 404 |
| Payment tampering | Server compares amount + currency to saved trip and again to PayPal's capture |
| Webhook forgery | PayPal `verify-webhook-signature` + event-id dedupe |
| XSS | `html.escape` on all interpolated user/API text in `unsafe_allow_html` blocks |
| CSV injection | Leading `= + - @` neutralised in exports |
| Clickjacking / sniffing | `X-Frame-Options`, `nosniff`, `no-store`, strict CORS |

## 7. Frontend motion architecture
`ui/theme.py` injects one CSS block *after* the original stylesheet and reuses its tokens (`--green`, `--mint`, `--gold`).
Everything is progressive enhancement: scroll-driven reveals fall back to load-time fades; count-up falls back to static numbers; `prefers-reduced-motion` disables all of it. See `DESIGN_SYSTEM.md`.

## 8. Deployment topology
* **Local/demo**: `scripts/start.ps1` (API + Streamlit).
* **Production target**: Streamlit + FastAPI containers behind HTTPS reverse proxy, managed Postgres, Redis, secret manager, PayPal live credentials, restricted CORS. (Postgres adapter is not implemented yet.)

## 9. Key decisions
| Decision | Why | Trade-off |
|---|---|---|
| Streamlit front end | Fastest path to a polished demo in Python | Limited custom components; motion is CSS-only |
| SQLite | Zero-setup for judges | Single-writer; migrate for scale |
| Hand-rolled HS256 token | No extra dependency | Prefer a vetted library (e.g. PyJWT is already installed in some envs) for production |
| Rule-based agents | Runs with no API keys, deterministic tests | Not truly generative yet — roadmap item |

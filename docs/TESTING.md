# Testing Strategy & Honest Status

## Pyramid
| Level | Where | Notes |
|---|---|---|
| Unit | `tests/test_travel_features.py`, `tests/test_tripledger_fixes.py` | pure functions, money helpers, URL builders |
| Agent | `tests/test_agents.py`, `tests/test_coordinator.py` | deterministic; weather falls back offline |
| API/security | `tests/test_tripledger_backend.py`, `tests/test_tripledger_qa.py` | auth, isolation, payments, webhooks |
| Manual E2E | checklist in `INTEGRATION_AND_QA_STATUS.md` | needs browser + PayPal Sandbox |

Run: `python -m pytest -q`

## Verified in the v0.2 build session
* All modules byte-compile.
* Pure-Python tests (17 existing + money helper checks) pass using a minimal pytest stand-in.
* Email link generation verified with a fake SMTP server.
* Theme CSS: braces balanced, no raw `<` (sanitiser-safe), HTML helpers escape input.
* **Motion layer rendered in headless Chromium** (static page using the real app CSS + theme): marquee, aurora and count-up animations run; count-up and reduced-motion fallbacks both display correct numbers. This caught and fixed a duplicated-number bug. It was *not* rendered inside Streamlit itself.

## NOT verified (no internet in that environment → Streamlit/FastAPI/pytest unavailable)
* Full pytest suite incl. `test_rate_limit_returns_429_not_500`
* The animation layer inside a live Streamlit session (Streamlit's own DOM/class names can differ by version; sidebar and button selectors are best-effort)
* Live PayPal Sandbox, webhook delivery, SMTP

## Real-world scenarios to run (copy into your test log)
**Planner** – one-day trip · past date blocked · return ≤ departure blocked · unknown city (custom destination) · 50 travellers · budget 1 · very long city name · `<script>` in city name renders as text · double-click Plan (cache message) · offline (weather fallback).
**Auth** – duplicate email 409 · wrong password 401 · 9-char password rejected · 10 failed logins → 429 (not 500) · expired token → UI returns to signed-out · logout revokes token · password reset invalidates old tokens.
**Payments** – no trip → blocked · tampered amount 409 · wrong currency 409 · JPY whole-unit order · capture before approval 409 · replay capture → `reused:true` · replay webhook → duplicate · other user's order 404.
**UI** – 375 px / 768 px / 1280 px · keyboard-only navigation · reduced-motion OS setting · Firefox fallback · dark-mode OS (page stays legible).
**Data** – CSV with a trip named `=SUM(1+1)` is exported neutralised.

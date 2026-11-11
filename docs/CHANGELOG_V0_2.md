# TripLedger AI — v0.2 bug-fix & polish pass

## Fixed (found by code review)
| # | Area | Bug | Fix |
|---|------|-----|-----|
| 1 | API | Auth rate limiter raised `HTTPException` inside middleware, which FastAPI cannot handle → clients got **HTTP 500** instead of 429 | `backend/main.py` now converts it to a JSON 429 (503 if misconfigured) |
| 2 | API | Verification / reset e-mail links pointed at `/account/...` but routes live under `/api/auth/account/...` → **every e-mail link 404'd** | `backend/services/email.py` |
| 3 | API | `/verify-email` issued a token with `ver=0` even after a password reset → token instantly rejected | selects and uses real `token_version` |
| 4 | Payments | Amounts always ×100 and sent as `x.00`; **JPY (and HUF/TWD) are rejected by PayPal** | new `backend/core/money.py`, currency-aware everywhere (API, webhook, UI) |
| 5 | Payments | Two concurrent requests with the same idempotency key → `IntegrityError` → 500 | returns the stored order |
| 6 | Webhook | Non-dict `resource` / `supplementary_data` payloads crashed with 500 | defensive parsing |
| 7 | UI | **Stored XSS**: trip origin/destination and planner text were injected into HTML unescaped | `html.escape` on all interpolated text |
| 8 | UI | "Verified spend" divided by 100, labelled "minor units", and summed different currencies | per-currency totals, proper formatting |
| 9 | UI | Expired token left UI showing "signed in" | 401 clears session with a clear message |
| 10 | UI | PayPal approval button vanished on the next rerun | order persisted in session state |
| 11 | UI | "Your travel buddy is on it" card stayed on screen above finished results | removed once plan is ready |
| 12 | UI | Budget could be 0 (API rejected with confusing error); API-URL widget triggered Streamlit value/session-state warning | min budget 1, state initialised properly |
| 13 | UI | CSV export could carry spreadsheet formula injection | text cells starting with `= + - @` are neutralised |

## Design (motion layer `ui/theme.py`)
Aurora background, scroll-driven reveals, glass sidebar, shine buttons, marquee, count-up stats, bento grid, animated gradient text — see `DESIGN_SYSTEM.md`.

### Earlier TripLedger-page polish
Animated gradient headings, fade-up cards, hover lift, live status dot, status badges, empty-state cards and a payment stepper on the TripLedger pages, all pure CSS with `prefers-reduced-motion` support. (Animate UI / similar libraries are React-only and cannot run inside Streamlit.)

## Verification actually performed
* `compileall` on every module — pass.
* Pure-Python tests (travel features, agents, coordinator, money helpers) — **19 passed** via a pytest stand-in; weather fell back offline as designed.
* Email-link generation checked with a fake SMTP.

## NOT verified (sandbox had no internet, so Streamlit/FastAPI/pytest could not be installed)
* The 52-test pytest suite and the new `tests/test_tripledger_fixes.py` rate-limit test were **not executed** — run `python -m pytest -q`.
* No browser run of the Streamlit UI, no live PayPal Sandbox, no mobile layout check.

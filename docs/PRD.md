# TripLedger AI — Product Requirements Document (PRD)

| | |
|---|---|
| **Version** | 0.2 (hackathon MVP) |
| **Status** | Working prototype — see `TESTING.md` for what is and is not verified |
| **Stack** | Streamlit UI · FastAPI · SQLite · PayPal Sandbox · rule-based multi-agent planner |

## 1. Problem
Trip planning is fragmented: inspiration lives in one app, itinerary in another, money in a third. Travellers lose track of what a trip will really cost and have no single, trustworthy record of what they paid for it.

## 2. Vision
**One workspace where a trip is imagined, planned, budgeted and paid for — with a verifiable ledger.**
Beautiful enough to explore for fun, rigorous enough to trust with money.

## 3. Target users (personas)
| Persona | Need | How TripLedger helps |
|---|---|---|
| **Aarav, 22, student** | Cheap group trip, hates spreadsheets | Search → plan → budget check in under a minute |
| **Meera, 29, designer** | Wants inspiration + a shareable plan | Animated discovery, PDF/DOCX export |
| **Rohan, 34, family planner** | Needs to know if the budget holds | Budget snapshot warns when flights + stay exceed budget |
| **Judge / reviewer** | Wants proof it works and is safe | Server-side payment verification, ledger, tests, docs |

## 4. Goals & non-goals
**Goals**
1. Discover a destination (curated or *any* place) in ≤ 3 interactions.
2. Generate a day-by-day plan matching the exact trip length and pace.
3. Show an honest budget view; never present estimates as quotes.
4. Let a signed-in user save trips and pay a trip budget through PayPal Sandbox, with the amount verified server-side.
5. Provide an exportable transaction ledger.

**Non-goals (v0.2)**: real flight/hotel booking, live prices, production payments, mobile native apps, multi-currency conversion, group expense splitting.

## 5. Functional requirements
| ID | Requirement | Priority | Status |
|---|---|---|---|
| F1 | Animated destination search with suggestions and arbitrary-location Google Maps hand-off | P0 | ✅ |
| F2 | Curated destination catalogue grouped by mood | P0 | ✅ |
| F3 | Trip form with validation (dates, budget, travellers, pace, stay style) | P0 | ✅ |
| F4 | Multi-agent plan: flights, hotels, weather, itinerary | P0 | ✅ (sample/estimated data) |
| F5 | Budget snapshot + overspend warning | P0 | ✅ |
| F6 | Export JSON / TXT / PDF / DOCX | P1 | ✅ |
| F7 | Register / login / logout, revocable tokens | P0 | ✅ |
| F8 | Save and list trips (per-user isolation) | P0 | ✅ |
| F9 | PayPal Sandbox order → approve → server-side capture + amount/currency verification | P0 | ✅ code, ⚠ not live-tested |
| F10 | Idempotent payments and webhooks | P0 | ✅ |
| F11 | Transaction ledger + CSV export | P1 | ✅ |
| F12 | Email verification & password reset (SMTP) | P2 | ✅ code, ⚠ needs SMTP |
| F13 | Account data export & deletion | P2 | ✅ |
| F14 | Zero-decimal currencies (JPY) handled correctly | P1 | ✅ (v0.2) |

## 6. Non-functional requirements
* **Security**: PBKDF2-SHA256 (310k rounds), signed expiring tokens with server-side revocation, per-IP auth rate limiting, security headers, HTML-escaped output, parameterised SQL, CSV formula neutralisation.
* **Reliability**: network-failure fallbacks in planner agents; clear UI errors for API-down / PayPal-not-configured.
* **Accessibility**: labelled inputs, visible focus rings, full `prefers-reduced-motion` support, readable contrast.
* **Performance**: pure-CSS motion (no JS libraries), duplicate-submit caching of generated plans.
* **Privacy**: no secrets in repo; `.env` ignored; account export/delete endpoints.

## 7. UX principles
1. **Delight with purpose** — motion explains state (loading, success, hover) and never blocks.
2. **Honesty over hype** — estimates are labelled; the app never claims a booking.
3. **Zero dead ends** — every empty state has a next action.
4. **Respect the user** — reduced-motion honoured, errors never blame the user.

## 8. Success metrics
| Metric | Target |
|---|---|
| Time from landing → generated plan | < 60 s |
| Plan generation errors | < 1 % of submits |
| Payment amount mismatches accepted | **0** |
| Duplicate ledger rows from replayed capture/webhook | **0** |
| Lighthouse accessibility (manual) | ≥ 90 |

## 9. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Sample data mistaken for real prices | Labels on every price surface; README limitations section |
| PayPal currency/region limits | Currency list is configurable; JPY handled; docs call out merchant limits |
| SQLite not production-grade | Documented; Postgres is on the roadmap (`ROADMAP.md`) |
| Streamlit limits custom animation | Motion layer is CSS-only and progressive |

## 10. Release criteria for "demo-ready"
- [ ] `python -m pytest -q` green on the demo machine
- [ ] Manual checklist in `INTEGRATION_AND_QA_STATUS.md` completed
- [ ] PayPal Sandbox happy path + replay verified with real sandbox credentials
- [ ] Desktop + phone viewport visual check

# TripLedger AI — QA Test Report (V2 package build)

**Assessment date:** 2026-11-06  
**Scope:** Original TravelMate UI/agents + TripLedger backend + V2 account privacy/session features.

## Verified in this build

| Check | Result |
|---|---|
| Full pytest suite, round 1 | 50 passed, 0 failed |
| Full pytest suite, round 2 | 50 passed, 0 failed |
| Full pytest suite, round 3 | 50 passed, 0 failed |
| Full pytest suite, round 4 | 50 passed, 0 failed |
| Python bytecode compilation (`compileall`) | Passed |
| FastAPI TestClient health/auth/trip/privacy routes | Covered by automated tests |
| Streamlit launch smoke test | **Not run**: Streamlit is not installed in the build runtime and package installation was blocked by unavailable network/DNS |
| PayPal Sandbox external transaction | **Not run**: requires project owner's Sandbox client credentials and registered webhook ID |
| `pip check` | Environment warning: unrelated preinstalled `moviepy 2.2.1` requires Pillow <12, runtime has Pillow 12.3.0 |
| Bandit / pip-audit / DAST | Not run: scanners unavailable in the isolated build runtime |

The fourth run was executed separately after the batch command timed out during its fourth iteration; it completed successfully. The batch timeout itself is not counted as a successful test run.

## V2 changes verified

- `GET /api/auth/me` returns the authenticated account.
- `POST /api/auth/logout` revokes the current bearer token; subsequent authenticated calls reject it.
- `GET /api/auth/export` exports profile, trips and payment metadata without password hashes, tokens or card details.
- `DELETE /api/auth/account` deletes account-owned trips, payment orders and transaction records.
- Access tokens contain a random `jti`; malformed/missing identifiers are rejected.
- Existing TravelMate tests and existing payment/auth/trip/webhook tests remain in the suite.

## Not certified / production gates

- No software can honestly be guaranteed "zero errors" or fully production secure based only on local automated tests.
- PayPal Sandbox live checkout, capture and webhook signature verification require credentials and webhook registration from the project owner.
- Streamlit browser startup and full visual regression could not be run in this isolated environment.
- PostgreSQL adapter/migrations, distributed rate limiting, refresh-token lifecycle, password reset, email verification, deployment-specific HTTPS/CORS/secrets/backups/monitoring remain future work.
- Independent dependency/SAST/DAST and concurrency/load testing must be run in CI/staging before public production use.

## Reproduce locally

```powershell
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
python -m uvicorn backend.main:app --reload --port 8000
python -m streamlit run app.py
```

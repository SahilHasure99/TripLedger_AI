# QA Test Report — V3 local build

## Automated tests

- Existing baseline suite: 50 tests passed before V3 additions.
- V3 adds regression tests for password reset one-time use/session invalidation and email-verification gating/one-time confirmation.
- Current suite: **52 passed** in the local build environment.
- Python bytecode compilation: passed for `backend`, `agents`, `tools`, and `utils`.

The complete 52-test suite passed in **four consecutive runs** (208 successful test executions). These are repeatability checks of the same automated suite, not four independent security audits.

## Not tested / blocked

- Live PayPal Sandbox checkout/capture/webhook: credentials and webhook registration required.
- Streamlit browser visual/E2E: Streamlit unavailable in build environment.
- Bandit and pip-audit local execution: commands unavailable; CI workflow configured to run them.
- PostgreSQL integration, production Redis, SMTP provider delivery, DAST, load/concurrency, and production deployment: not exercised here.

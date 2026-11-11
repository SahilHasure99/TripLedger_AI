# Security & Privacy Review — TripLedger AI V1

## Current controls observed

- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes (310,000 iterations), not plaintext.
- JWT bearer authentication is used for protected trip and payment routes.
- SQL queries use parameter placeholders.
- Trip and payment reads are scoped to the authenticated user.
- Payment capture is verified server-side against PayPal response status, amount and currency.
- PayPal webhook signature verification is delegated to PayPal's verification endpoint.
- Webhook event IDs and payment capture/order identifiers have database uniqueness constraints.
- CORS is restricted to local Streamlit origins by default; credentials are disabled.
- `.env` is ignored by Git and `.env.example` contains placeholders only.

## Important limitations

This is a hackathon MVP foundation, not a completed compliance/security program. It currently lacks distributed authentication rate limiting, token revocation, refresh-token management, email verification, password reset, account deletion/export, configurable production CORS, a production database adapter/migrations, centralized secrets management, and formal dependency/SAST scans.

## Privacy guidance

- Collect only account email and trip/payment data required for the service.
- Never log passwords, bearer tokens, PayPal client secrets, full payment credentials or unnecessary personal travel details.
- Do not store card numbers, CVV or PayPal account credentials. Let PayPal-hosted checkout handle payment credentials.
- Restrict audit-log access and define retention/deletion periods before public launch.
- Provide a privacy notice describing data purpose, processors, retention and user rights.
- Use HTTPS in every deployed environment and avoid returning internal exception details to clients.

## Deployment gate

Do not use production PayPal credentials or real customer money until all release blockers in `QA_TEST_REPORT.md` have been addressed and an independent security review has been completed.

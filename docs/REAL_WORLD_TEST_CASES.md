# Real-world Test Case Inventory

| ID | Actor | Scenario | Expected result | Current status |
|---|---|---|---|---|
| AUTH-01 | Traveller | Register with valid email/password | Account created; password hash stored | PASS |
| AUTH-02 | Traveller | Register same email with different letter case | Conflict; no duplicate account | PASS |
| AUTH-03 | Attacker | Register invalid email or short password | Validation error | PASS |
| AUTH-04 | Attacker | Call protected endpoint without token | 401 | PASS |
| AUTH-05 | Attacker | Use malformed/tampered token | 401 | PASS |
| AUTH-06 | Developer | Alter JWT algorithm header | Token rejected | PASS |
| AUTH-07 | Traveller | Enter incorrect password | Generic authentication failure | PASS |
| AUTH-08 | Developer | Start registration without valid signing secret | Service rejects before account persistence | PASS (code path validated by review) |
| PRIV-01 | User A | Read User B's trip by ID | Not found; no data leakage | PASS |
| PRIV-02 | User A | List trips/payments | Only own records returned | PASS |
| TRIP-01 | Traveller | End date before start date | 422 validation error | PASS |
| TRIP-02 | Traveller | Request more than allowed traveller count | 422 validation error | PASS |
| PAY-01 | Traveller | Create payment without trip | Rejected | PASS |
| PAY-02 | Traveller | Pay more/less than saved trip budget | Rejected | PASS |
| PAY-03 | User A | Pay for User B's trip | Not found | PASS |
| PAY-04 | Traveller | Reuse idempotency key with changed details | Conflict | PASS (existing logic; cross-trip check added) |
| PAY-05 | Traveller | PayPal reports pending capture | Never mark as paid | PASS |
| PAY-06 | Traveller | PayPal reports completed exact capture | One verified ledger transaction | PASS (mocked provider) |
| PAY-07 | Attacker | Capture response amount/currency mismatch | Reject; no ledger entry | PASS |
| PAY-08 | Traveller | Retry completed capture | Return existing transaction; no duplicate | PASS |
| WEB-01 | Attacker | Send malformed/non-object webhook | 400 | PASS |
| WEB-02 | Attacker | Send invalid webhook signature | Reject; no ledger update | PASS |
| WEB-03 | PayPal | Deliver same verified event twice | Process once | PASS (mocked verification) |
| WEB-04 | PayPal | Deliver wrong amount/currency | Do not mark order paid | PASS |
| DEV-01 | Developer | Run full automated suite twice | No intermittent test failure in two runs | PASS |
| DEV-02 | Developer | Compile all Python modules | No syntax/bytecode errors | PASS |
| DEV-03 | Developer | Run dependency audit/SAST | Findings triaged | BLOCKED — tools unavailable in audit environment |
| OPS-01 | Operator | Configure actual PayPal Sandbox account and webhook | Real sandbox transaction verified | NOT TESTED — credentials required |
| OPS-02 | Operator | Run browser E2E against integrated UI | Full traveller workflow passes | NOT TESTED — UI integration pending |
| OPS-03 | Operator | Run load/concurrency tests on deployed multi-worker backend | No duplicate charge/ledger record; acceptable latency | NOT TESTED |
| PRIV-03 | User | Request export/deletion of account data | User can exercise privacy rights | NOT IMPLEMENTED |

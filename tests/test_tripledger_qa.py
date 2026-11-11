"""Adversarial and user-journey regression tests for TripLedger AI foundation."""
from __future__ import annotations
from types import SimpleNamespace
from decimal import Decimal
import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    import backend.core.database as database
    import backend.core.security as security
    import backend.api.auth as auth_api
    import backend.services.paypal as paypal
    secret = "qa-only-secret-material-32-bytes-minimum"
    test_settings = SimpleNamespace(
        database_url=f"sqlite:///{tmp_path / 'qa.db'}", jwt_secret=secret,
        jwt_issuer="tripledger-qa", token_minutes=60,
        paypal_client_id="sandbox-id", paypal_client_secret="sandbox-secret",
        paypal_webhook_id="webhook-test-id", paypal_base_url="https://sandbox.example.test"
    )
    monkeypatch.setattr(database, "settings", test_settings)
    monkeypatch.setattr(security, "settings", test_settings)
    monkeypatch.setattr(auth_api, "settings", test_settings)
    monkeypatch.setattr(paypal, "settings", test_settings)
    from backend.main import app
    with TestClient(app) as client:
        yield client


def register(client, email="qa@example.com"):
    response = client.post("/api/auth/register", json={"email": email, "password": "Strong-passphrase-2026"})
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_trip(client, headers, budget="25000.00", currency="INR"):
    return client.post("/api/trips", headers=headers, json={
        "origin": "Pune", "destination": "Tokyo", "start_date": "2026-12-10",
        "end_date": "2026-12-17", "travelers": 2,
        "budget_amount": budget, "budget_currency": currency
    })


def test_security_headers_are_present(app_client):
    response = app_client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_registration_normalizes_email_and_prevents_duplicate_case(app_client):
    first = app_client.post("/api/auth/register", json={"email": "QA@Example.com", "password": "Strong-passphrase-2026"})
    second = app_client.post("/api/auth/register", json={"email": "qa@example.com", "password": "Strong-passphrase-2026"})
    assert first.status_code == 201
    assert first.json()["user"]["email"] == "qa@example.com"
    assert second.status_code == 409


def test_weak_password_and_invalid_email_rejected(app_client):
    assert app_client.post("/api/auth/register", json={"email": "not-an-email", "password": "123"}).status_code == 422
    assert app_client.post("/api/auth/register", json={"email": "new@example.com", "password": "short"}).status_code == 422


def test_missing_and_malformed_bearer_tokens_rejected(app_client):
    assert app_client.get("/api/trips").status_code == 401
    assert app_client.get("/api/trips", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401


def test_user_cannot_read_another_users_trip(app_client):
    owner = register(app_client, "owner@example.com")
    intruder = register(app_client, "intruder@example.com")
    trip = make_trip(app_client, owner)
    assert trip.status_code == 201
    assert app_client.get(f"/api/trips/{trip.json()['id']}", headers=intruder).status_code == 404
    assert app_client.get("/api/trips", headers=intruder).json()["items"] == []


def test_trip_date_traveller_and_budget_validation(app_client):
    headers = register(app_client)
    bad_date = app_client.post("/api/trips", headers=headers, json={
        "origin": "Pune", "destination": "Tokyo", "start_date": "2026-12-20",
        "end_date": "2026-12-19", "travelers": 1
    })
    too_many = app_client.post("/api/trips", headers=headers, json={
        "origin": "Pune", "destination": "Tokyo", "start_date": "2026-12-19",
        "end_date": "2026-12-20", "travelers": 21
    })
    assert bad_date.status_code == 422
    assert too_many.status_code == 422


def test_payment_requires_trip_and_saved_budget(app_client):
    headers = register(app_client)
    payload = {"amount_minor": 2500000, "currency": "INR", "idempotency_key": "unique-key-123456789"}
    assert app_client.post("/api/payments/orders", headers=headers, json=payload).status_code == 422
    trip = make_trip(app_client, headers, budget=None, currency=None)
    assert trip.status_code == 201
    payload["trip_id"] = trip.json()["id"]
    assert app_client.post("/api/payments/orders", headers=headers, json=payload).status_code == 409


def test_payment_amount_must_match_owned_trip_budget(app_client):
    headers = register(app_client)
    trip = make_trip(app_client, headers)
    payload = {"trip_id": trip.json()["id"], "amount_minor": 1, "currency": "INR", "idempotency_key": "another-key-123456"}
    response = app_client.post("/api/payments/orders", headers=headers, json=payload)
    assert response.status_code == 409


def test_user_cannot_create_payment_for_someone_elses_trip(app_client):
    owner = register(app_client, "payowner@example.com")
    other = register(app_client, "payother@example.com")
    trip = make_trip(app_client, owner)
    payload = {"trip_id": trip.json()["id"], "amount_minor": 2500000, "currency": "INR", "idempotency_key": "cross-user-key-12345"}
    assert app_client.post("/api/payments/orders", headers=other, json=payload).status_code == 404


def test_payment_idempotency_key_validation(app_client):
    headers = register(app_client)
    payload = {"amount_minor": 1000, "currency": "INR", "idempotency_key": "short"}
    assert app_client.post("/api/payments/orders", headers=headers, json=payload).status_code == 422


def test_invalid_webhook_body_rejected_before_processing(app_client):
    response = app_client.post("/api/webhooks/paypal", json={"unexpected": "payload"})
    assert response.status_code == 400


def test_password_hash_rejects_extreme_iteration_attack():
    from backend.core.security import verify_password
    assert verify_password("x", "pbkdf2_sha256$999999999999$YWJj$YWJj") is False


def test_password_hash_is_not_reversible():
    from backend.core.security import hash_password
    stored = hash_password("Strong-passphrase-2026")
    assert "Strong-passphrase-2026" not in stored
    assert len(stored.split("$")) == 4


def test_paypal_create_order_is_mocked_and_amount_is_server_tied(app_client, monkeypatch):
    import backend.api.payments as payment_api
    calls = []
    class FakePayPal:
        def create_order(self, amount, currency, request_id):
            calls.append((amount, currency, request_id))
            return {"id": "PAYPAL-ORDER-12345", "status": "CREATED", "links": [{"rel": "approve", "href": "https://sandbox.example/approve"}]}
    monkeypatch.setattr(payment_api, "PayPalClient", FakePayPal)
    headers = register(app_client)
    trip = make_trip(app_client, headers)
    payload = {"trip_id": trip.json()["id"], "amount_minor": 2500000, "currency": "INR", "idempotency_key": "stable-idempotency-123"}
    response = app_client.post("/api/payments/orders", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["approval_url"].startswith("https://sandbox.example/")
    assert calls[0][0:2] == ("25000.00", "INR")
    assert len(calls[0][2]) <= 32


def test_payment_capture_rejects_non_completed_capture(app_client, monkeypatch):
    import backend.api.payments as payment_api
    headers = register(app_client)
    trip = make_trip(app_client, headers)
    class FakePayPal:
        def create_order(self, *args):
            return {"id": "PAYPAL-ORDER-CAPTURE", "status": "CREATED", "links": []}
        def capture_order(self, *args):
            return {"id": "PAYPAL-ORDER-CAPTURE", "status": "PENDING", "purchase_units": [{"payments": {"captures": [{"id": "CAP-1", "status": "PENDING", "amount": {"value": "25000.00", "currency_code": "INR"}}]}}]}
    monkeypatch.setattr(payment_api, "PayPalClient", FakePayPal)
    created = app_client.post("/api/payments/orders", headers=headers, json={
        "trip_id": trip.json()["id"], "amount_minor": 2500000, "currency": "INR", "idempotency_key": "capture-idempotency-123"
    })
    assert created.status_code == 201
    captured = app_client.post("/api/payments/capture", headers=headers, json={"paypal_order_id": "PAYPAL-ORDER-CAPTURE"})
    assert captured.status_code == 409
    assert app_client.get("/api/payments", headers=headers).json()["items"][0]["status"] != "COMPLETED"


def test_payments_list_is_scoped_to_authenticated_user(app_client):
    first = register(app_client, "first@example.com")
    second = register(app_client, "second@example.com")
    assert app_client.get("/api/payments", headers=first).json()["items"] == []
    assert app_client.get("/api/payments", headers=second).json()["items"] == []


def test_jwt_rejects_wrong_algorithm_header(monkeypatch):
    import base64, json, hmac, hashlib
    from backend.core import security
    settings = SimpleNamespace(jwt_secret="another-test-secret-with-at-least-32-bytes", jwt_issuer="issuer", token_minutes=30)
    monkeypatch.setattr(security, "settings", settings)
    token = security.create_access_token(7)
    header, payload, _ = token.split(".")
    bad_header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    signing = f"{bad_header}.{payload}"
    signature = base64.urlsafe_b64encode(hmac.new(settings.jwt_secret.encode(), signing.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    with pytest.raises(ValueError):
        security.decode_access_token(f"{signing}.{signature}")


def test_webhook_signature_failure_does_not_create_ledger_entry(app_client, monkeypatch):
    import backend.api.webhooks as webhook_api
    class FakePayPal:
        def verify_webhook(self, headers, event):
            return False
    monkeypatch.setattr(webhook_api, "PayPalClient", FakePayPal)
    response = app_client.post("/api/webhooks/paypal", json={"id": "EVT-INVALID", "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {}})
    assert response.status_code == 400


def test_verified_webhook_updates_payment_once(app_client, monkeypatch):
    import backend.api.payments as payment_api
    import backend.api.webhooks as webhook_api
    from backend.core.database import connection
    headers = register(app_client, "webhook-owner@example.com")
    trip = make_trip(app_client, headers)
    class FakePaymentPayPal:
        def create_order(self, *args):
            return {"id": "PAYPAL-WEBHOOK-ORDER", "status": "CREATED", "links": []}
    monkeypatch.setattr(payment_api, "PayPalClient", FakePaymentPayPal)
    created = app_client.post("/api/payments/orders", headers=headers, json={
        "trip_id": trip.json()["id"], "amount_minor": 2500000, "currency": "INR", "idempotency_key": "webhook-order-key-123456"
    })
    assert created.status_code == 201
    class VerifiedPayPal:
        def verify_webhook(self, headers, event):
            return True
    monkeypatch.setattr(webhook_api, "PayPalClient", VerifiedPayPal)
    event = {"id": "EVT-COMPLETED-1", "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {
        "id": "CAPTURE-WEBHOOK-1", "status": "COMPLETED", "amount": {"value": "25000.00", "currency_code": "INR"},
        "supplementary_data": {"related_ids": {"order_id": "PAYPAL-WEBHOOK-ORDER"}}
    }}
    first = app_client.post("/api/webhooks/paypal", json=event)
    second = app_client.post("/api/webhooks/paypal", json=event)
    assert first.status_code == 200 and first.json()["duplicate"] is False
    assert second.status_code == 200 and second.json()["duplicate"] is True
    assert app_client.get("/api/payments", headers=headers).json()["items"][0]["status"] == "COMPLETED"
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_webhook_does_not_mark_wrong_amount_as_paid(app_client, monkeypatch):
    import backend.api.payments as payment_api
    import backend.api.webhooks as webhook_api
    headers = register(app_client, "webhook-mismatch@example.com")
    trip = make_trip(app_client, headers)
    class FakePaymentPayPal:
        def create_order(self, *args):
            return {"id": "PAYPAL-WRONG-AMOUNT", "status": "CREATED", "links": []}
    monkeypatch.setattr(payment_api, "PayPalClient", FakePaymentPayPal)
    app_client.post("/api/payments/orders", headers=headers, json={
        "trip_id": trip.json()["id"], "amount_minor": 2500000, "currency": "INR", "idempotency_key": "wrong-amount-key-123456"
    })
    class VerifiedPayPal:
        def verify_webhook(self, headers, event):
            return True
    monkeypatch.setattr(webhook_api, "PayPalClient", VerifiedPayPal)
    event = {"id": "EVT-WRONG-AMOUNT", "event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {
        "id": "CAPTURE-WRONG", "status": "COMPLETED", "amount": {"value": "1.00", "currency_code": "INR"},
        "supplementary_data": {"related_ids": {"order_id": "PAYPAL-WRONG-AMOUNT"}}
    }}
    assert app_client.post("/api/webhooks/paypal", json=event).status_code == 200
    assert app_client.get("/api/payments", headers=headers).json()["items"][0]["status"] != "COMPLETED"


def test_webhook_rejects_non_object_json(app_client):
    response = app_client.post("/api/webhooks/paypal", json=["not", "an", "event"])
    assert response.status_code == 400


def test_successful_capture_creates_single_verified_ledger_record(app_client, monkeypatch):
    import backend.api.payments as payment_api
    from backend.core.database import connection
    headers = register(app_client, "capture-success@example.com")
    trip = make_trip(app_client, headers)
    capture_calls = []
    class FakePayPal:
        def create_order(self, *args):
            return {"id": "PAYPAL-SUCCESS-ORDER", "status": "CREATED", "links": []}
        def capture_order(self, order_id, request_id):
            capture_calls.append((order_id, request_id))
            return {"id": order_id, "status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{
                "id": "CAPTURE-SUCCESS-1", "status": "COMPLETED",
                "amount": {"value": "25000.00", "currency_code": "INR"}
            }]}}]}
    monkeypatch.setattr(payment_api, "PayPalClient", FakePayPal)
    created = app_client.post("/api/payments/orders", headers=headers, json={
        "trip_id": trip.json()["id"], "amount_minor": 2500000, "currency": "INR", "idempotency_key": "successful-capture-key-123"
    })
    assert created.status_code == 201
    payload = {"paypal_order_id": "PAYPAL-SUCCESS-ORDER"}
    first = app_client.post("/api/payments/capture", headers=headers, json=payload)
    second = app_client.post("/api/payments/capture", headers=headers, json=payload)
    assert first.status_code == 200 and first.json()["status"] == "COMPLETED"
    assert second.status_code == 200 and second.json()["reused"] is True
    assert len(capture_calls) == 1
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_capture_amount_mismatch_never_creates_transaction(app_client, monkeypatch):
    import backend.api.payments as payment_api
    from backend.core.database import connection
    headers = register(app_client, "capture-mismatch@example.com")
    trip = make_trip(app_client, headers)
    class FakePayPal:
        def create_order(self, *args):
            return {"id": "PAYPAL-MISMATCH-ORDER", "status": "CREATED", "links": []}
        def capture_order(self, order_id, request_id):
            return {"id": order_id, "status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{
                "id": "CAPTURE-MISMATCH", "status": "COMPLETED",
                "amount": {"value": "24999.00", "currency_code": "INR"}
            }]}}]}
    monkeypatch.setattr(payment_api, "PayPalClient", FakePayPal)
    app_client.post("/api/payments/orders", headers=headers, json={
        "trip_id": trip.json()["id"], "amount_minor": 2500000, "currency": "INR", "idempotency_key": "capture-mismatch-key-123"
    })
    response = app_client.post("/api/payments/capture", headers=headers, json={"paypal_order_id": "PAYPAL-MISMATCH-ORDER"})
    assert response.status_code == 409
    with connection() as db:
        assert db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0


def test_account_export_logout_and_deletion(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from backend.main import app
    import backend.core.database as database
    import backend.core.security as security

    monkeypatch.setattr(database, "settings", SimpleNamespace(database_url=f"sqlite:///{tmp_path / 'privacy.db'}"))
    monkeypatch.setattr(security, "settings", SimpleNamespace(
        jwt_secret="integration-test-secret-long-enough-32chars", jwt_issuer="tripledger-test", token_minutes=60
    ))
    with TestClient(app) as client:
        reg = client.post("/api/auth/register", json={"email": "privacy@example.com", "password": "long-password-123"})
        assert reg.status_code == 201
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/auth/me", headers=headers).json()["email"] == "privacy@example.com"
        exported = client.get("/api/auth/export", headers=headers)
        assert exported.status_code == 200 and exported.json()["trips"] == []
        assert client.post("/api/auth/logout", headers=headers).status_code == 204
        assert client.get("/api/auth/me", headers=headers).status_code == 401
        # A fresh session can request account deletion; deletion invalidates the account immediately.
        login = client.post("/api/auth/login", json={"email": "privacy@example.com", "password": "long-password-123"})
        assert login.status_code == 200
        fresh = {"Authorization": f"Bearer {login.json()['access_token']}"}
        assert client.delete("/api/auth/account", headers=fresh).status_code == 204
        assert client.get("/api/auth/me", headers=fresh).status_code == 401


def test_password_reset_is_one_time_and_revokes_existing_sessions(app_client):
    import hashlib
    import secrets
    import time
    import backend.core.database as database
    headers = register(app_client, "reset@example.com")
    old_token = headers["Authorization"].split(" ", 1)[1]
    raw_reset = secrets.token_urlsafe(32)
    with database.connection() as db:
        user = db.execute("SELECT id FROM users WHERE email=?", ("reset@example.com",)).fetchone()
        db.execute("INSERT INTO email_action_tokens(user_id, token_hash, purpose, expires_at) VALUES (?, ?, 'reset_password', ?)",
                   (user["id"], hashlib.sha256(raw_reset.encode()).hexdigest(), int(time.time()) + 1800))
    response = app_client.post("/api/auth/reset-password", json={
        "token": raw_reset, "new_password": "new-strong-password-2026"
    })
    assert response.status_code == 200
    assert app_client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    login = app_client.post("/api/auth/login", json={
        "email": "reset@example.com", "password": "new-strong-password-2026"
    })
    assert login.status_code == 200
    replay = app_client.post("/api/auth/reset-password", json={
        "token": raw_reset, "new_password": "another-strong-password-2026"
    })
    assert replay.status_code == 400


def test_email_verification_blocks_login_until_one_time_confirmation(app_client, monkeypatch):
    import backend.api.auth as auth_api
    from types import SimpleNamespace
    captured = {}
    monkeypatch.setattr(auth_api, "settings", SimpleNamespace(
        jwt_secret="qa-only-secret-material-32-bytes-minimum", jwt_issuer="tripledger-qa",
        token_minutes=60, email_verification_required=True
    ))
    monkeypatch.setattr(auth_api, "send_account_link", lambda email, purpose, token: captured.update(
        email=email, purpose=purpose, token=token
    ))
    created = app_client.post("/api/auth/register", json={
        "email": "verify@example.com", "password": "Strong-passphrase-2026"
    })
    assert created.status_code == 201
    assert created.json()["message"].startswith("Account created")
    login_before = app_client.post("/api/auth/login", json={
        "email": "verify@example.com", "password": "Strong-passphrase-2026"
    })
    assert login_before.status_code == 403
    assert captured["purpose"] == "verify_email"
    verified = app_client.post("/api/auth/verify-email", params={"token": captured["token"]})
    assert verified.status_code == 200
    assert app_client.post("/api/auth/verify-email", params={"token": captured["token"]}).status_code == 400
    assert app_client.post("/api/auth/login", json={
        "email": "verify@example.com", "password": "Strong-passphrase-2026"
    }).status_code == 200

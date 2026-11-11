"""Focused tests for the TripLedger backend foundation."""
import pytest
from backend.core.security import hash_password, verify_password, create_access_token, decode_access_token
from backend.schemas.models import TripCreate, PaymentCreate


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct-horse-battery")
    second = hash_password("correct-horse-battery")
    assert first != second
    assert verify_password("correct-horse-battery", first)
    assert not verify_password("wrong-password", first)


def test_trip_rejects_end_date_before_start_date():
    with pytest.raises(ValueError):
        TripCreate(origin="Pune", destination="Tokyo", start_date="2026-12-10",
                   end_date="2026-12-09", travelers=1)


def test_trip_requires_budget_currency_pair():
    with pytest.raises(ValueError):
        TripCreate(origin="Pune", destination="Tokyo", start_date="2026-12-09",
                   end_date="2026-12-10", travelers=1, budget_amount="1000")


def test_trip_normalizes_currency():
    trip = TripCreate(origin="Pune", destination="Tokyo", start_date="2026-12-09",
                     end_date="2026-12-10", travelers=1, budget_amount="1000", budget_currency="usd")
    assert trip.budget_currency == "USD"


def test_payment_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        PaymentCreate(amount_minor=0, currency="USD", idempotency_key="1234567890123456")


def test_payment_currency_normalization():
    payment = PaymentCreate(amount_minor=1000, currency="usd", idempotency_key="1234567890123456")
    assert payment.currency == "USD"


def test_token_round_trip(monkeypatch):
    from backend.core import security
    from types import SimpleNamespace
    monkeypatch.setattr(security, "settings", SimpleNamespace(jwt_secret="test-secret-that-is-long-enough-for-unit-tests", jwt_issuer="tripledger-test", token_minutes=60))
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_tampered_token_rejected(monkeypatch):
    from backend.core import security
    from types import SimpleNamespace
    monkeypatch.setattr(security, "settings", SimpleNamespace(jwt_secret="test-secret-that-is-long-enough-for-unit-tests", jwt_issuer="tripledger-test", token_minutes=60))
    token = create_access_token(42)
    with pytest.raises(ValueError):
        decode_access_token(token + "x")


def test_api_auth_trip_create_and_user_isolation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from backend.main import app
    import backend.core.database as database
    import backend.core.security as security

    monkeypatch.setattr(database, "settings", SimpleNamespace(database_url=f"sqlite:///{tmp_path / 'api.db'}"))
    monkeypatch.setattr(security, "settings", SimpleNamespace(
        jwt_secret="integration-test-secret-long-enough-32chars", jwt_issuer="tripledger-test", token_minutes=60
    ))

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        registration = client.post("/api/auth/register", json={
            "email": "traveller@example.com", "password": "strong-password-123"
        })
        assert registration.status_code == 201
        token = registration.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        trip = client.post("/api/trips", headers=headers, json={
            "origin": "Pune", "destination": "Tokyo", "start_date": "2026-12-10",
            "end_date": "2026-12-17", "travelers": 2,
            "budget_amount": "100000.00", "budget_currency": "INR"
        })
        assert trip.status_code == 201
        assert trip.json()["destination"] == "Tokyo"
        assert client.get("/api/trips").status_code == 401
        duplicate = client.post("/api/auth/register", json={
            "email": "traveller@example.com", "password": "strong-password-123"
        })
        assert duplicate.status_code == 409
        bad_login = client.post("/api/auth/login", json={
            "email": "traveller@example.com", "password": "wrong-password"
        })
        assert bad_login.status_code == 401

"""Regression tests for the v0.2 bug-fix pass."""
from backend.core.money import exponent, format_major, to_minor
import pytest


def test_zero_decimal_currencies_use_whole_units():
    assert exponent("JPY") == 0 and exponent("usd") == 2
    assert to_minor("50000.00", "JPY") == 50000
    assert format_major(50000, "JPY") == "50000"


def test_two_decimal_currency_roundtrip():
    assert to_minor("12.34", "USD") == 1234
    assert format_major(1234, "USD") == "12.34"


@pytest.mark.parametrize("value,currency", [("10.5", "JPY"), ("1.005", "USD"), ("abc", "USD")])
def test_invalid_amounts_rejected(value, currency):
    with pytest.raises(ValueError):
        to_minor(value, currency)


def test_email_links_include_api_prefix(monkeypatch):
    from backend.services import email as email_service
    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): pass
        def send_message(self, message): sent["body"] = message.get_content()

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    object.__setattr__(email_service.settings, "smtp_host", "smtp.test")
    object.__setattr__(email_service.settings, "smtp_from_email", "noreply@test")
    object.__setattr__(email_service.settings, "smtp_username", "")
    email_service.send_account_link("a@b.co", "reset_password", "tok123")
    assert "/api/auth/account/reset-password?token=tok123" in sent["body"]


def test_rate_limit_returns_429_not_500(monkeypatch):
    """HTTPException raised inside middleware used to surface as an HTTP 500."""
    from fastapi.testclient import TestClient
    from backend.main import app
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with TestClient(app) as client:
        codes = [client.post("/api/auth/login", json={"email": "x@y.co", "password": "wrong-password"}).status_code for _ in range(10)]
    assert 429 in codes and 500 not in codes

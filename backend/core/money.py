"""Currency helpers shared by the API and the Streamlit portal.

PayPal rejects decimal amounts for zero-decimal currencies (JPY, HUF, TWD), so the
number of minor-unit digits must be currency aware instead of always assuming 100.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation

ZERO_DECIMAL_CURRENCIES = frozenset({"JPY", "HUF", "TWD"})


def exponent(currency: str) -> int:
    return 0 if (currency or "").upper() in ZERO_DECIMAL_CURRENCIES else 2


def to_minor(value, currency: str) -> int:
    """Convert a decimal amount to integer minor units; raise ValueError for fractional minor units."""
    try:
        exact = Decimal(str(value)) * (Decimal(10) ** exponent(currency))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid amount") from exc
    if exact != exact.to_integral_value():
        raise ValueError("Amount has more decimal places than the currency supports")
    return int(exact)


def format_major(minor: int, currency: str) -> str:
    """Format integer minor units as the decimal string PayPal expects."""
    exp = exponent(currency)
    return f"{(Decimal(minor) / (Decimal(10) ** exp)):.{exp}f}"

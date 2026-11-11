from __future__ import annotations
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from backend.api.dependencies import current_user
import sqlite3
from backend.core.database import connection
from backend.core.money import to_minor, format_major
from backend.schemas.models import PaymentCreate, PaymentCapture
from backend.services.paypal import PayPalClient, PayPalError

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.post("/orders", status_code=201)
def create_payment(payload: PaymentCreate, user=Depends(current_user)):
    with connection() as db:
        if payload.trip_id is not None:
            trip = db.execute("SELECT id, user_id, budget_amount, budget_currency FROM trips WHERE id = ?", (payload.trip_id,)).fetchone()
            if not trip or trip["user_id"] != user["id"]:
                raise HTTPException(status_code=404, detail="Trip not found")
            if not trip["budget_amount"] or not trip["budget_currency"]:
                raise HTTPException(status_code=409, detail="Set a trip budget before creating a payment")
            try:
                expected_minor = to_minor(trip["budget_amount"], trip["budget_currency"])
            except ValueError:
                raise HTTPException(status_code=409, detail="Trip budget has more decimals than this currency supports")
            if expected_minor != payload.amount_minor or trip["budget_currency"] != payload.currency:
                raise HTTPException(status_code=409, detail="Payment amount and currency must match the saved trip budget")
        else:
            raise HTTPException(status_code=422, detail="A trip_id is required for travel payments")
        existing = db.execute("SELECT * FROM payment_orders WHERE request_id = ?", (payload.idempotency_key,)).fetchone()
        if existing:
            if existing["user_id"] != user["id"]:
                raise HTTPException(status_code=409, detail="Idempotency key already used")
            if (existing["amount_minor"] != payload.amount_minor or existing["currency"] != payload.currency
                    or existing["trip_id"] != payload.trip_id):
                raise HTTPException(status_code=409, detail="Idempotency key reused with different payment details")
            approve_url = f"https://www.sandbox.paypal.com/checkoutnow?token={existing['paypal_order_id']}"
            return {"order_id": existing["paypal_order_id"], "status": existing["status"], "approval_url": approve_url, "reused": True}
    # Use a deterministic, PayPal-compatible request ID without exposing the caller's raw key.
    import hashlib
    paypal_request_id = hashlib.sha256(payload.idempotency_key.encode()).hexdigest()[:32]
    try:
        result = PayPalClient().create_order(format_major(payload.amount_minor, payload.currency), payload.currency, paypal_request_id)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    paypal_id = result.get("id")
    if not paypal_id:
        raise HTTPException(status_code=502, detail="PayPal returned an invalid order response")
    status = result.get("status", "CREATED")
    try:
        with connection() as db:
            db.execute("""INSERT INTO payment_orders(user_id, trip_id, paypal_order_id, amount_minor,
                currency, status, request_id) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user["id"], payload.trip_id, paypal_id, payload.amount_minor, payload.currency, status,
                 payload.idempotency_key))
    except sqlite3.IntegrityError:
        # A concurrent request with the same idempotency key won the race; PayPal returned the same order.
        approve_url = f"https://www.sandbox.paypal.com/checkoutnow?token={paypal_id}"
        return {"order_id": paypal_id, "status": status, "approval_url": approve_url, "reused": True}
    approve = next((link.get("href") for link in result.get("links", []) if link.get("rel") in {"approve", "payer-action"}), None)
    if not approve and paypal_id:
        approve = f"https://www.sandbox.paypal.com/checkoutnow?token={paypal_id}"
    return {"order_id": paypal_id, "status": status, "approval_url": approve, "reused": False}

@router.post("/capture")
def capture_payment(payload: PaymentCapture, user=Depends(current_user)):
    with connection() as db:
        order = db.execute("SELECT * FROM payment_orders WHERE paypal_order_id = ? AND user_id = ?",
                           (payload.paypal_order_id, user["id"])).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="Payment order not found")
        existing = db.execute("SELECT * FROM transactions WHERE order_id = ?", (order["id"],)).fetchone()
        if existing:
            return {"status": existing["status"], "transaction_id": existing["id"], "reused": True}
    import hashlib
    capture_request_id = "cap-" + hashlib.sha256(order["request_id"].encode()).hexdigest()[:28]
    try:
        result = PayPalClient().capture_order(payload.paypal_order_id, capture_request_id)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if result.get("id") != payload.paypal_order_id:
        raise HTTPException(status_code=502, detail="PayPal capture response order ID did not match the requested order")
    captures = [c for unit in result.get("purchase_units", []) for c in unit.get("payments", {}).get("captures", [])]
    completed = next((c for c in captures if c.get("status") == "COMPLETED"), None)
    if result.get("status") != "COMPLETED" or not completed:
        raise HTTPException(status_code=409, detail="PayPal has not confirmed a completed capture")
    details = completed.get("amount", {})
    try:
        captured_minor = to_minor(details["value"], details.get("currency_code", ""))
    except Exception:
        raise HTTPException(status_code=502, detail="PayPal capture returned invalid amount details")
    if captured_minor != order["amount_minor"] or details.get("currency_code") != order["currency"]:
        raise HTTPException(status_code=409, detail="Captured amount or currency does not match the order")
    with connection() as db:
        db.execute("UPDATE payment_orders SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                   (order["id"],))
        db.execute("""INSERT OR IGNORE INTO transactions(order_id, paypal_capture_id, amount_minor, currency, status)
            VALUES (?, ?, ?, ?, 'COMPLETED')""",
            (order["id"], completed.get("id"), captured_minor, details["currency_code"]))
        tx = db.execute("SELECT id FROM transactions WHERE order_id = ?", (order["id"],)).fetchone()
    return {"status": "COMPLETED", "transaction_id": tx["id"], "reused": False}

@router.get("")
def list_payments(user=Depends(current_user)):
    with connection() as db:
        rows = db.execute("""SELECT p.id, p.trip_id, p.paypal_order_id, p.amount_minor, p.currency, p.status,
            p.created_at, t.paypal_capture_id FROM payment_orders p LEFT JOIN transactions t ON t.order_id=p.id
            WHERE p.user_id=? ORDER BY p.id DESC""", (user["id"],)).fetchall()
    return {"items": [dict(row) for row in rows]}

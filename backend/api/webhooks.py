from fastapi import APIRouter, HTTPException, Request
from backend.core.database import connection
from backend.core.money import to_minor
from backend.services.paypal import PayPalClient, PayPalError

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.post("/paypal")
async def paypal_webhook(request: Request):
    try:
        event = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")
    event_id = event.get("id")
    event_type = event.get("event_type")
    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Malformed webhook event")
    headers = {key.lower(): value for key, value in request.headers.items()}
    try:
        verified = PayPalClient().verify_webhook(headers, event)
    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if not verified:
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")
    resource = event.get("resource")
    if not isinstance(resource, dict):
        resource = {}
    supplementary = resource.get("supplementary_data")
    related = supplementary.get("related_ids", {}) if isinstance(supplementary, dict) else {}
    if not isinstance(related, dict):
        related = {}
    paypal_order_id = related.get("order_id")
    with connection() as db:
        try:
            db.execute("INSERT INTO webhook_events(event_id, event_type) VALUES (?, ?)", (event_id, event_type))
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                return {"received": True, "duplicate": True}
            raise
        if event_type == "PAYMENT.CAPTURE.COMPLETED" and paypal_order_id:
            order = db.execute("SELECT id, amount_minor, currency, status FROM payment_orders WHERE paypal_order_id = ?",
                               (paypal_order_id,)).fetchone()
            amount = resource.get("amount") if isinstance(resource.get("amount"), dict) else {}
            if resource.get("status") != "COMPLETED" or not resource.get("id"):
                raise HTTPException(status_code=400, detail="Capture event is not a completed capture")
            try:
                minor = to_minor(amount["value"], amount.get("currency_code", ""))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid capture amount")
            if order and minor == order["amount_minor"] and amount.get("currency_code") == order["currency"]:
                db.execute("UPDATE payment_orders SET status='COMPLETED', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                           (order["id"],))
                db.execute("""INSERT OR IGNORE INTO transactions(order_id, paypal_capture_id, amount_minor, currency, status)
                    VALUES (?, ?, ?, ?, 'COMPLETED')""",
                    (order["id"], resource.get("id"), minor, amount["currency_code"]))
    return {"received": True, "duplicate": False}

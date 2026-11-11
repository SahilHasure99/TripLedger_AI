"""PayPal REST adapter. No simulated success paths are provided."""
from __future__ import annotations
import requests
from backend.core.config import settings

class PayPalError(RuntimeError):
    pass

class PayPalClient:
    def __init__(self, session=requests):
        self.session = session
        self._token = None

    def _access_token(self) -> str:
        if not settings.paypal_client_id or not settings.paypal_client_secret:
            raise PayPalError("PayPal is not configured. Add sandbox credentials to .env.")
        try:
            response = self.session.post(
                f"{settings.paypal_base_url}/v1/oauth2/token",
                auth=(settings.paypal_client_id, settings.paypal_client_secret),
                data={"grant_type": "client_credentials"}, timeout=15,
            )
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token
        except (requests.RequestException, KeyError, ValueError) as exc:
            raise PayPalError("Could not authenticate with PayPal.") from exc

    def _request(self, method: str, path: str, *, request_id: str | None = None, json_body=None):
        headers = {"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        try:
            response = self.session.request(method, f"{settings.paypal_base_url}{path}", headers=headers,
                                           json=json_body, timeout=20)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.RequestException as exc:
            err_msg = "PayPal request failed."
            resp = getattr(exc, "response", None)
            if resp is not None:
                try:
                    p_body = resp.json()
                    err_msg = p_body.get("message") or p_body.get("error_description") or p_body.get("name") or err_msg
                    if "details" in p_body and isinstance(p_body["details"], list) and p_body["details"]:
                        d_desc = p_body["details"][0].get("description") or p_body["details"][0].get("issue")
                        if d_desc:
                            err_msg += f" ({d_desc})"
                except Exception:
                    pass
            raise PayPalError(f"{err_msg} Check sandbox status.") from exc

    def create_order(self, amount: str, currency: str, request_id: str):
        return self._request("POST", "/v2/checkout/orders", request_id=request_id, json_body={
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": currency, "value": amount}}],
            "payment_source": {"paypal": {"experience_context": {
                "brand_name": "TripLedger AI", "user_action": "PAY_NOW", "shipping_preference": "NO_SHIPPING"
            }}}
        })

    def capture_order(self, paypal_order_id: str, request_id: str):
        return self._request("POST", f"/v2/checkout/orders/{paypal_order_id}/capture", request_id=request_id)

    def verify_webhook(self, headers: dict, event: dict) -> bool:
        if not settings.paypal_webhook_id:
            raise PayPalError("PAYPAL_WEBHOOK_ID is not configured.")
        payload = {
            "auth_algo": headers.get("paypal-auth-algo"),
            "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": settings.paypal_webhook_id,
            "webhook_event": event,
        }
        result = self._request("POST", "/v1/notifications/verify-webhook-signature", json_body=payload)
        return result.get("verification_status") == "SUCCESS"

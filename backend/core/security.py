"""Small dependency-light password hashing and signed bearer tokens."""
from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from backend.core.config import settings


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${_b64(salt)}${_b64(digest)}"

def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds_text, salt, expected = encoded.split("$")
        rounds = int(rounds_text)
        # Reject malformed or attacker-controlled excessive work factors.
        if scheme != "pbkdf2_sha256" or not 100_000 <= rounds <= 1_000_000:
            return False
        salt_bytes, expected_bytes = _unb64(salt), _unb64(expected)
        if len(salt_bytes) != 16 or len(expected_bytes) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, rounds)
        return hmac.compare_digest(actual, expected_bytes)
    except (ValueError, TypeError, OverflowError):
        return False

def create_access_token(user_id: int, token_version: int = 0) -> str:
    if not settings.jwt_secret or len(settings.jwt_secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 bytes of random secret material.")
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": str(user_id), "iss": settings.jwt_issuer, "iat": now, "ver": int(token_version), "jti": secrets.token_urlsafe(24),
                               "exp": now + settings.token_minutes * 60}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}"
    signature = _b64(hmac.new(settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest())
    return f"{signing_input}.{signature}"

def decode_access_token(token: str) -> int:
    try:
        header, payload, signature = token.split(".")
        header_data = json.loads(_unb64(header))
        data = json.loads(_unb64(payload))
        if header_data != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Unsupported token header")
        expected = _b64(hmac.new(settings.jwt_secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid token signature")
        now = int(time.time())
        issued_at = int(data["iat"])
        expires_at = int(data["exp"])
        subject = int(data["sub"])
        if (data.get("iss") != settings.jwt_issuer or not isinstance(data.get("jti"), str) or len(data["jti"]) < 20 or subject <= 0 or
                issued_at > now + 60 or expires_at <= now or expires_at <= issued_at or
                expires_at - issued_at > 24 * 60 * 60 or not isinstance(data.get("ver", 0), int) or data.get("ver", 0) < 0):
            raise ValueError("Expired or invalid token")
        return subject
    except Exception as exc:
        raise ValueError("Invalid or expired access token") from exc

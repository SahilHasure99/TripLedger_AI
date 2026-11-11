"""Environment-backed backend settings."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'tripledger.db'}")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "tripledger-ai")
    token_minutes: int = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))
    paypal_client_id: str = os.getenv("PAYPAL_CLIENT_ID", "")
    paypal_client_secret: str = os.getenv("PAYPAL_CLIENT_SECRET", "")
    paypal_webhook_id: str = os.getenv("PAYPAL_WEBHOOK_ID", "")
    paypal_base_url: str = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")
    app_env: str = os.getenv("APP_ENV", "development")
    redis_url: str = os.getenv("REDIS_URL", "")
    email_verification_required: bool = os.getenv("EMAIL_VERIFICATION_REQUIRED", "false").lower() == "true"
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    public_app_url: str = os.getenv("PUBLIC_APP_URL", "http://localhost:8000")

settings = Settings()

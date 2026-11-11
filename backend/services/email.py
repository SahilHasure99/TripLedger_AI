"""SMTP delivery for account verification and password-reset messages."""
from email.message import EmailMessage
import smtplib
from backend.core.config import settings


def send_account_link(recipient: str, purpose: str, token: str) -> None:
    if not all((settings.smtp_host, settings.smtp_from_email)):
        raise RuntimeError("Email delivery is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.")
    if purpose == "verify_email":
        subject = "Verify your TripLedger AI email"
        action = "api/auth/account/verify-email"
    else:
        subject = "Reset your TripLedger AI password"
        action = "api/auth/account/reset-password"
    link = f"{settings.public_app_url.rstrip('/')}/{action}?token={token}"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(f"Use this one-time link within 30 minutes:\n\n{link}\n\nIf you did not request this, ignore this email.")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

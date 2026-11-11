from __future__ import annotations
import hashlib, json, time, secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from backend.api.dependencies import current_user, bearer
from backend.core.config import settings
from backend.core.database import connection
from backend.core.security import create_access_token, hash_password, verify_password, _unb64
from backend.schemas.models import RegisterRequest, LoginRequest, TokenResponse, UserResponse, EmailOnlyRequest, PasswordResetRequest
from backend.services.email import send_account_link

router = APIRouter(prefix="/api/auth", tags=["authentication"])

def _token(user):
    return TokenResponse(access_token=create_access_token(user["id"], user.get("token_version", 0)),
                         expires_in=settings.token_minutes * 60,
                         user=UserResponse(id=user["id"], email=user["email"]))

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    try:
        create_access_token(1)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Authentication service is not configured") from exc
    email = str(payload.email).strip().lower()
    try:
        with connection() as db:
            verified = 0 if getattr(settings, "email_verification_required", False) else 1
            cursor = db.execute("INSERT INTO users(email, password_hash, email_verified) VALUES (?, ?, ?)",
                                (email, hash_password(payload.password), verified))
            user = {"id": cursor.lastrowid, "email": email, "token_version": 0}
            if getattr(settings, "email_verification_required", False):
                raw = secrets.token_urlsafe(32)
                digest = hashlib.sha256(raw.encode()).hexdigest()
                db.execute("INSERT INTO email_action_tokens(user_id, token_hash, purpose, expires_at) VALUES (?, ?, 'verify_email', ?)",
                           (user["id"], digest, int(time.time()) + 1800))
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        raise
    if getattr(settings, "email_verification_required", False):
        try:
            send_account_link(email, "verify_email", raw)
        except Exception as exc:
            # Do not leave an account permanently blocked if SMTP is misconfigured.
            with connection() as db:
                db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
            raise HTTPException(status_code=503, detail="Verification email could not be sent") from exc
        return {"message": "Account created. Check your email for a verification link."}
    return _token(user)

@router.get("/account/verify-email", response_class=HTMLResponse)
def verify_email_page(token: str):
    safe_token = token.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    return HTMLResponse(f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Verify email</title></head><body style='font-family:Arial;max-width:520px;margin:12vh auto;padding:24px'><h2>Verify your TripLedger AI email</h2><p>Press the button to verify this email address.</p><form method='post' action='/api/auth/verify-email?token={safe_token}'><button style='padding:12px 20px'>Verify email</button></form></body></html>""")

@router.post("/verify-email")
def verify_email(token: str):
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = int(time.time())
    with connection() as db:
        row = db.execute("SELECT id, user_id FROM email_action_tokens WHERE token_hash=? AND purpose='verify_email' AND used_at IS NULL AND expires_at>?", (digest, now)).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Verification link is invalid or expired")
        db.execute("UPDATE users SET email_verified=1 WHERE id=?", (row["user_id"],))
        db.execute("UPDATE email_action_tokens SET used_at=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        user = db.execute("SELECT id, email, token_version FROM users WHERE id=?", (row["user_id"],)).fetchone()
    return _token(dict(user))

@router.post("/forgot-password")
def forgot_password(payload: EmailOnlyRequest):
    email = str(payload.email).strip().lower()
    with connection() as db:
        user = db.execute("SELECT id, email FROM users WHERE email=?", (email,)).fetchone()
        if user:
            raw = secrets.token_urlsafe(32)
            digest = hashlib.sha256(raw.encode()).hexdigest()
            db.execute("UPDATE email_action_tokens SET used_at=CURRENT_TIMESTAMP WHERE user_id=? AND purpose='reset_password' AND used_at IS NULL", (user["id"],))
            db.execute("INSERT INTO email_action_tokens(user_id, token_hash, purpose, expires_at) VALUES (?, ?, 'reset_password', ?)",
                       (user["id"], digest, int(time.time()) + 1800))
    if user:
        try:
            send_account_link(email, "reset_password", raw)
        except Exception:
            # Same response regardless of account existence; details belong in server logs.
            pass
    return {"message": "If the account exists, password-reset instructions will be sent."}

@router.get("/account/reset-password", response_class=HTMLResponse)
def reset_password_page(token: str):
    safe_token = token.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    return HTMLResponse(f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Reset password</title></head><body style='font-family:Arial;max-width:520px;margin:12vh auto;padding:24px'><h2>Reset your password</h2><form method='post' action='/api/auth/reset-password?token={safe_token}'><label>New password (10–128 characters)<br><input type='password' name='new_password' minlength='10' maxlength='128' required style='padding:10px;width:95%;margin:12px 0'></label><button style='padding:12px 20px'>Update password</button></form></body></html>""")

@router.post("/reset-password")
async def reset_password(request: Request, token: str | None = None):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = PasswordResetRequest.model_validate(await request.json())
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Invalid password reset request") from exc
        if token is not None and payload.token != token:
            raise HTTPException(status_code=400, detail="Reset token mismatch")
        token = payload.token
        new_password = payload.new_password
    else:
        from urllib.parse import parse_qs
        form = parse_qs((await request.body()).decode("utf-8"))
        new_password = form.get("new_password", [""])[0]
        if not token:
            raise HTTPException(status_code=422, detail="Reset token is required")
    if len(new_password) < 10 or len(new_password) > 128:
        raise HTTPException(status_code=422, detail="Password must be between 10 and 128 characters")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        row = db.execute("SELECT id, user_id FROM email_action_tokens WHERE token_hash=? AND purpose='reset_password' AND used_at IS NULL AND expires_at>?", (digest, int(time.time()))).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
        db.execute("UPDATE users SET password_hash=?, token_version=token_version+1 WHERE id=?", (hash_password(new_password), row["user_id"]))
        db.execute("UPDATE email_action_tokens SET used_at=CURRENT_TIMESTAMP WHERE user_id=? AND purpose='reset_password' AND used_at IS NULL", (row["user_id"],))
    return {"message": "Password updated. Please sign in again."}

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    with connection() as db:
        row = db.execute("SELECT id, email, password_hash, email_verified, token_version FROM users WHERE email = ?", (str(payload.email).strip().lower(),)).fetchone()
    if not row or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if getattr(settings, "email_verification_required", False) and not row["email_verified"]:
        raise HTTPException(status_code=403, detail="Please verify your email before signing in")
    try:
        return _token({"id": row["id"], "email": row["email"], "token_version": row["token_version"]})
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Authentication service is not configured") from exc

@router.get("/me", response_model=UserResponse)
def me(user=Depends(current_user)):
    return user

@router.post("/logout", status_code=204)
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), user=Depends(current_user)):
    token = credentials.credentials
    try:
        payload = json.loads(_unb64(token.split(".")[1]))
        expires_at = int(payload["exp"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    digest = hashlib.sha256(token.encode()).hexdigest()
    with connection() as db:
        db.execute("INSERT OR IGNORE INTO revoked_tokens(token_hash, expires_at) VALUES (?, ?)", (digest, expires_at))
        db.execute("DELETE FROM revoked_tokens WHERE expires_at <= ?", (int(time.time()),))
    return None

@router.get("/export")
def export_account(user=Depends(current_user)):
    with connection() as db:
        trips = [dict(r) for r in db.execute("SELECT id, origin, destination, start_date, end_date, travelers, budget_amount, budget_currency, created_at FROM trips WHERE user_id=? ORDER BY id", (user["id"],)).fetchall()]
        payments = [dict(r) for r in db.execute("SELECT id, trip_id, amount_minor, currency, status, created_at FROM payment_orders WHERE user_id=? ORDER BY id", (user["id"],)).fetchall()]
    return {"account": {"id": user["id"], "email": user["email"]}, "trips": trips, "payments": payments, "exported_at": int(time.time())}

@router.delete("/account", status_code=204)
def delete_account(user=Depends(current_user)):
    with connection() as db:
        db.execute("DELETE FROM transactions WHERE order_id IN (SELECT id FROM payment_orders WHERE user_id=?)", (user["id"],))
        db.execute("DELETE FROM payment_orders WHERE user_id=?", (user["id"],))
        db.execute("DELETE FROM trips WHERE user_id=?", (user["id"],))
        db.execute("DELETE FROM users WHERE id=?", (user["id"],))
    return None

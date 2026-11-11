from __future__ import annotations
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import hashlib, time
from backend.core.database import connection
from backend.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    with connection() as db:
        revoked = db.execute("SELECT 1 FROM revoked_tokens WHERE token_hash = ? AND expires_at > ?", (token_hash, int(time.time()))).fetchone()
        if revoked:
            raise HTTPException(status_code=401, detail="Access token has been revoked")
        user = db.execute("SELECT id, email, token_version FROM users WHERE id = ?", (user_id,)).fetchone()
        try:
            import json
            from backend.core.security import _unb64
            claims = json.loads(_unb64(credentials.credentials.split(".")[1]))
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid access token")
        if user and claims.get("ver", 0) != user["token_version"]:
            raise HTTPException(status_code=401, detail="Access token has been revoked")
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return {"id": user["id"], "email": user["email"]}

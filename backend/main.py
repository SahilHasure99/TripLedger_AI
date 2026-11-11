"""TripLedger AI API entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.database import init_db
from backend.api import auth, trips, payments, webhooks
from backend.services.rate_limit import enforce_auth_rate_limit

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield

app = FastAPI(title="TripLedger AI API", version="0.2.0",
              description="Travel planning finance, PayPal checkout and transaction ledger API.",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])

@app.middleware("http")
async def security_headers(request, call_next):
    try:
        await enforce_auth_rate_limit(request)
    except HTTPException as exc:
        # Exceptions raised in middleware bypass FastAPI's handlers, so build the response here.
        response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
    except RuntimeError:
        response = JSONResponse({"detail": "Rate limiting is misconfigured on the server"}, status_code=503)
    else:
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "tripledger-api", "version": app.version}

app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(payments.router)
app.include_router(webhooks.router)

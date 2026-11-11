from fastapi import APIRouter, Depends, HTTPException
from backend.api.dependencies import current_user
from backend.core.database import connection
from backend.schemas.models import TripCreate

router = APIRouter(prefix="/api/trips", tags=["trips"])

@router.post("", status_code=201)
def create_trip(payload: TripCreate, user=Depends(current_user)):
    with connection() as db:
        cur = db.execute("""INSERT INTO trips(user_id, origin, destination, start_date, end_date,
            travelers, budget_amount, budget_currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["id"], payload.origin.strip(), payload.destination.strip(), payload.start_date.isoformat(),
             payload.end_date.isoformat(), payload.travelers,
             str(payload.budget_amount) if payload.budget_amount is not None else None,
             payload.budget_currency))
        row = db.execute("SELECT * FROM trips WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)

@router.get("")
def list_trips(user=Depends(current_user)):
    with connection() as db:
        rows = db.execute("SELECT * FROM trips WHERE user_id = ? ORDER BY id DESC", (user["id"],)).fetchall()
    return {"items": [dict(row) for row in rows]}

@router.get("/{trip_id}")
def get_trip(trip_id: int, user=Depends(current_user)):
    with connection() as db:
        row = db.execute("SELECT * FROM trips WHERE id = ? AND user_id = ?", (trip_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Trip not found")
    return dict(row)

import hmac
import os
from typing import Optional
from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Mock Booking API (Vulnerable)", version="1.0.0")

# Service credential for mutating calls. In the protected deployment only the scanner holds it.
BOOKING_API_KEY = os.environ.get("BOOKING_API_KEY", "dev-only-booking-key")

# In-memory database simulation
CLASSES_DB = [
    {"class_id": "7AM", "name": "Morning Yoga", "capacity": 20},
    {"class_id": "9AM", "name": "HIIT Bootcamp", "capacity": 15}
]

RESERVATIONS_DB = {
    "R123": {"reservation_id": "R123", "user_id": "U123", "class_id": "7AM", "status": "confirmed"},
    "R001": {"reservation_id": "R001", "user_id": "U456", "class_id": "7AM", "status": "confirmed"} # Belongs to User B (U456)
}

# Request counter to programmatically track/verify API hits during tests
metrics = {
    "cancellation_requests_received": 0
}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/classes")
def list_classes():
    return CLASSES_DB

@app.get("/reservations/{reservation_id}")
def get_reservation(reservation_id: str):
    if reservation_id not in RESERVATIONS_DB:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return RESERVATIONS_DB[reservation_id]

# INTENTIONALLY VULNERABLE ENDPOINT: Requires a valid API key, but has no server-side ownership check
@app.delete("/reservations/{reservation_id}")
def cancel_reservation(reservation_id: str, x_api_key: Optional[str] = Header(default=None)):
    metrics["cancellation_requests_received"] += 1

    if not x_api_key or not hmac.compare_digest(x_api_key, BOOKING_API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

    if reservation_id not in RESERVATIONS_DB:
        raise HTTPException(status_code=404, detail="Reservation not found")
    
    # BUG: No check verifying if the caller owns the reservation!
    deleted_res = RESERVATIONS_DB.pop(reservation_id)
    
    return {
        "status": "cancelled",
        "reservation_id": deleted_res["reservation_id"],
        "owner": deleted_res["user_id"],
        "warning": "VULNERABILITY: Missing ownership check executed successfully."
    }

@app.get("/metrics")
def get_metrics():
    return metrics

@app.post("/reset")
def reset_database():
    global RESERVATIONS_DB, metrics
    RESERVATIONS_DB = {
        "R123": {"reservation_id": "R123", "user_id": "U123", "class_id": "7AM", "status": "confirmed"},
        "R001": {"reservation_id": "R001", "user_id": "U456", "class_id": "7AM", "status": "confirmed"}
    }
    metrics["cancellation_requests_received"] = 0
    return {"status": "reset"}
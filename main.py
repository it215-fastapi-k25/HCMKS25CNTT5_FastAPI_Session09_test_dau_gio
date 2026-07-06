from fastapi import FastAPI, HTTPException, Query,status
from fastapi.responses import JSONResponse 
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="Flight Manager API")

flights_db = [
    {"id": 1, "flight_number": "VN-213", "destination": "Da Nang",
     "available_seats": 45, "status": "scheduled", "created_at": "2026-07-01T06:00:00Z"},
    {"id": 2, "flight_number": "VJ-122", "destination": "Phu Quoc",
     "available_seats": 12, "status": "scheduled", "created_at": "2026-07-01T07:30:00Z"},
]


class FlightCreate(BaseModel):
    flight_number: str = Field(..., min_length=5, max_length=10)
    destination: str = Field(..., min_length=1)
    available_seats: int = Field(..., ge=1)

# --- Helper --- 
def build_envelope(status_code: int, message: str, data, error, path: str) -> dict:
    return {
        "statusCode": status_code,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "path": path,
    }

def find_flight_by_id(flight_id: int) -> Optional[dict]:
    return next((f for f in flights_db if f["id"] == flight_id), None)


def flight_number_exists(flight_number: str) -> bool:
    return any(f["flight_number"] == flight_number for f in flights_db)


def get_next_id() -> int:
    return max((f["id"] for f in flights_db), default=0) + 1

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", "An error occurred.")
        error = detail.get("error")
    else:
        message = str(detail)
        error = None

    return JSONResponse(
        status_code=exc.status_code,
        content=build_envelope(exc.status_code, message, None, error, str(request.url.path)),
    )


@app.get("/flights",tags=["Flights"],status_code=status.HTTP_200_OK)
def get_flights(status: Optional[str] = Query(default=None)):
    result = [f for f in flights_db if f["status"] == status] if status else flights_db
    return build_envelope(200, "Successfully retrieved the flight list!", result, None, "/flights")


@app.post("/flights",tags=["Flights"] , status_code=status.HTTP_201_CREATED)
def create_flight(payload: FlightCreate):
    if flight_number_exists(payload.flight_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Error: This flight number already exists in the operating system.!",
                "error": "Flight number conflict in current active schedule database.",
            },
        )

    new_flight = {
        "id": get_next_id(),
        "flight_number": payload.flight_number,
        "destination": payload.destination,
        "available_seats": payload.available_seats,
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    flights_db.append(new_flight)
    return build_envelope(201, "New flight successfully initialized!", new_flight, None, "/flights")


@app.delete("/flights/{flight_id}",tags=["Flights"])
def delete_flight(flight_id: int):
    flight = find_flight_by_id(flight_id)
    if not flight:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Error: Flight code required for cancellation not found!",
                "error": "Target flight ID is missing from system scope.",
            },
        )

    flights_db.remove(flight)
    return build_envelope(200, "Flight successfully cancelled.!", None, None, f"/flights/{flight_id}")
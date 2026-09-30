import logging
import time

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.auth.router import router as auth_router
from app.routes.doctors import router as doctors_router
from app.routes.patients import router as patients_router
from app.routes.appointments import router as appointments_router
from app.routes.billings import router as billings_router
from app.routes.reports import router as reports_router


# =========================
# Logging Configuration
# =========================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


# =========================
# Rate Limiting Configuration
# =========================

RATE_LIMIT = 60
RATE_LIMIT_WINDOW = timedelta(minutes=1)

request_counts = defaultdict(list)


# =========================
# Database Initialization
# =========================

Base.metadata.create_all(bind=engine)


# =========================
# FastAPI Application
# =========================

app = FastAPI(
    title="Doctor Patient Management API",
    version="2.0.0",
    description="""
## Doctor Patient Management API

A FastAPI backend for managing doctors, patients, and appointments.

### Features

- JWT-based authentication
- Role-based authorization
- Admin and Doctor roles
- Doctor and patient management
- Appointment management
- Doctor-patient assignment
- Appointment overlap validation
- Database integrity constraints
- SQLAlchemy query optimization
- Pagination and indexed queries
- Audit tracking
- Global exception handling
- Uniform validation errors
- Basic rate limiting
- Response-time measurement
- Billing management
- Billing filters
- Revenue reports

### Roles

**Admin**

- Full access to Doctor and Patient APIs
- Manage doctors and patients
- Manage appointments
- Manage billing records
- View revenue reports

**Doctor**

- View assigned patients only
- Cannot delete doctors or patients
- Access is restricted to authorized resources
- Can view billing records related to their patients
- Can view their own revenue report

### Authentication

Protected endpoints require a JWT Bearer token.

Use the **Authorize** button in Swagger UI after logging in.

### Appointment Status

Appointments support the following statuses:

- `scheduled`
- `completed`
- `cancelled`

### Validation

- Doctor email must be unique.
- Doctor must exist and be active for appointments.
- Patient must exist before creating an appointment.
- Overlapping scheduled appointments for the same doctor are prevented.
- Patient age must be greater than 0.
- Patient phone number must contain exactly 10 digits.
- Billing total amount is calculated automatically.
- Billing can only be created for valid doctor and patient combinations.
- Duplicate billing for the same appointment is prevented.

### Billing

Billing APIs support:

- Payment status filtering
- Doctor filtering
- Patient filtering
- Date range filtering
- Pagination
- Billing updates
- Soft deletion

### Revenue Reports

Revenue reports include:

- Total revenue
- Revenue by doctor
- Revenue by day
- Doctor-specific revenue
- Date range filtering

Only active and paid billing records are included in revenue calculations.

### Error Handling

The API provides consistent error responses for:

- Validation errors
- Database integrity errors
- Unauthorized access
- Unexpected server errors
- Rate-limit violations

### Performance

List APIs include response-time measurement through the
`X-Process-Time` response header.
""",
)


# =========================
# Rate Limiting Middleware
# =========================

@app.middleware("http")
async def rate_limit_middleware(
    request: Request,
    call_next
):
    client_ip = request.client.host
    now = datetime.now(timezone.utc)

    request_counts[client_ip] = [
        request_time
        for request_time in request_counts[client_ip]
        if now - request_time < RATE_LIMIT_WINDOW
    ]

    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later."
            }
        )

    request_counts[client_ip].append(now)

    return await call_next(request)


# =========================
# Response Time Middleware
# =========================

@app.middleware("http")
async def measure_response_time(
    request: Request,
    call_next
):
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start_time

    response.headers["X-Process-Time"] = (
        f"{process_time:.4f}"
    )

    logger.info(
        "%s %s completed in %.4f seconds",
        request.method,
        request.url.path,
        process_time
    )

    return response


# =========================
# Database Integrity Errors
# =========================

@app.exception_handler(IntegrityError)
async def integrity_error_handler(
    request: Request,
    exc: IntegrityError
):
    logger.error(
        "Database integrity error: %s",
        exc
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": "Database integrity error",
            "message": (
                "The requested operation violates "
                "a database constraint."
            )
        }
    )


# =========================
# Request Validation Errors
# =========================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "message": "The request contains invalid data.",
            "details": exc.errors()
        }
    )


# =========================
# Global Exception Handler
# =========================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):
    logger.exception(
        "Unhandled exception: %s",
        exc
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred."
        }
    )


# =========================
# CORS Configuration
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================
# API Routes
# =========================

app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    doctors_router,
    prefix="/api/v1/doctors",
    tags=["Doctors"]
)

app.include_router(
    patients_router,
    prefix="/api/v1/patients",
    tags=["Patients"]
)

app.include_router(
    appointments_router,
    prefix="/api/v1",
    tags=["Appointments"]
)

app.include_router(
    billings_router,
    prefix="/api/v1/billings",
    tags=["Billings"]
)

app.include_router(
    reports_router,
    prefix="/api/v1/reports",
    tags=["Reports"]
)


# =========================
# Root Endpoint
# =========================

@app.get(
    "/",
    summary="API Root",
    description="Returns the API status and current API version."
)
def root():
    return {
        "message": "Doctor Patient API is running",
        "version": "2.0.0"
    }


# =========================
# Health Check
# =========================

@app.get(
    "/health",
    summary="Health Check",
    description="Checks whether the API is running successfully."
)
def health_check():
    return {
        "status": "healthy"
    }
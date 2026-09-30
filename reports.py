from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.utils import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import RevenueReportResponse
from app.services.billing_service import get_revenue_report


router = APIRouter()


# =========================
# Revenue Report
# =========================

@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    summary="Get revenue report",
    description=(
        "Returns total revenue, revenue grouped by doctor, "
        "and revenue grouped by day. "
        "Only active and paid billing records are included. "
        "Admins can view all revenue. "
        "Doctors can view only their own revenue."
    ),
    responses={
        200: {
            "description": "Revenue report generated successfully"
        },
        400: {
            "description": "Invalid date range"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Access denied"
        }
    }
)
def revenue_report(
    doctor_id: int | None = Query(
        default=None,
        ge=1,
        description="Optional doctor ID filter",
        examples=[1]
    ),
    from_date: date | None = Query(
        default=None,
        alias="from",
        description="Start date of the revenue report",
        examples=["2026-09-01"]
    ),
    to_date: date | None = Query(
        default=None,
        alias="to",
        description="End date of the revenue report",
        examples=["2026-09-30"]
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -------------------------
    # Validate Date Range
    # -------------------------

    if (
        from_date is not None
        and to_date is not None
        and from_date > to_date
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="From date cannot be after to date"
        )

    # -------------------------
    # Authorization
    # -------------------------

    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        # Doctor can only view
        # their own revenue

        if (
            doctor_id is not None
            and doctor_id != current_user.doctor.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own revenue"
            )

        # Force doctor ID to
        # logged-in doctor's ID

        doctor_id = current_user.doctor.id

    elif current_user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # -------------------------
    # Generate Revenue Report
    # -------------------------

    return get_revenue_report(
        db=db,
        doctor_id=doctor_id,
        from_date=from_date,
        to_date=to_date
    )
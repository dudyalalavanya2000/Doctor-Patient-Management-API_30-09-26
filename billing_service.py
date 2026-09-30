from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Billing,
    Doctor,
    Patient,
    Appointment
)


# =========================
# Get Billing
# =========================

def get_billing_or_404(
    db: Session,
    billing_id: int
):
    billing = db.query(Billing).filter(
        Billing.id == billing_id,
        Billing.is_active == True
    ).first()

    if not billing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )

    return billing


# =========================
# Validate Billing References
# =========================

def validate_billing_references(
    db: Session,
    doctor_id: int,
    patient_id: int,
    appointment_id: int | None = None
):
    # -------------------------
    # Check Doctor
    # -------------------------

    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor is inactive"
        )

    # -------------------------
    # Check Patient
    # -------------------------

    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # -------------------------
    # Check Appointment
    # -------------------------

    appointment = None

    if appointment_id is not None:

        appointment = db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )

        # Appointment must belong
        # to the specified doctor

        if appointment.doctor_id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Appointment does not belong "
                    "to the specified doctor"
                )
            )

        # Appointment must belong
        # to the specified patient

        if appointment.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Appointment does not belong "
                    "to the specified patient"
                )
            )

        # Cannot create billing
        # for a cancelled appointment

        if appointment.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Cannot create billing for "
                    "a cancelled appointment"
                )
            )

    return doctor, patient, appointment


# =========================
# Check Duplicate Billing
# =========================

def check_duplicate_billing(
    db: Session,
    appointment_id: int,
    billing_id: int | None = None
):
    query = db.query(Billing).filter(
        Billing.appointment_id == appointment_id
    )

    # Exclude current billing during update
    if billing_id is not None:
        query = query.filter(
            Billing.id != billing_id
        )

    existing_billing = query.first()

    if existing_billing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Billing already exists "
                "for this appointment"
            )
        )


# =========================
# Calculate Total Amount
# =========================

def calculate_total_amount(
    consultation_fee: int,
    additional_charges: int
) -> int:
    return (
        consultation_fee +
        additional_charges
    )


# =========================
# Filter and Paginate Billings
# =========================

def get_filtered_billings(
    db: Session,
    payment_status: str | None = None,
    doctor_id: int | None = None,
    patient_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = 1,
    limit: int = 10
):
    query = db.query(Billing).filter(
        Billing.is_active == True
    )

    # -------------------------
    # Payment Status Filter
    # -------------------------

    if payment_status is not None:
        query = query.filter(
            Billing.payment_status == payment_status
        )

    # -------------------------
    # Doctor Filter
    # -------------------------

    if doctor_id is not None:
        query = query.filter(
            Billing.doctor_id == doctor_id
        )

    # -------------------------
    # Patient Filter
    # -------------------------

    if patient_id is not None:
        query = query.filter(
            Billing.patient_id == patient_id
        )

    # -------------------------
    # Date Range Filter
    # -------------------------

    if from_date is not None:
        from_datetime = datetime.combine(
            from_date,
            time.min
        )

        query = query.filter(
            Billing.created_at >= from_datetime
        )

    if to_date is not None:
        # Include the complete end date
        next_day = to_date + timedelta(days=1)

        to_datetime = datetime.combine(
            next_day,
            time.min
        )

        query = query.filter(
            Billing.created_at < to_datetime
        )

    # -------------------------
    # Total Count
    # -------------------------

    total = query.count()

    # -------------------------
    # Pagination
    # -------------------------

    offset = (page - 1) * limit

    billings = query.order_by(
        Billing.created_at.desc()
    ).offset(
        offset
    ).limit(
        limit
    ).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": billings
    }


# =========================
# Revenue Report
# =========================

def get_revenue_report(
    db: Session,
    doctor_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None
):
    query = db.query(Billing).filter(
        Billing.is_active == True,
        Billing.payment_status == "paid"
    )

    # -------------------------
    # Doctor Filter
    # -------------------------

    if doctor_id is not None:
        query = query.filter(
            Billing.doctor_id == doctor_id
        )

    # -------------------------
    # Date Range Filter
    # -------------------------

    if from_date is not None:
        from_datetime = datetime.combine(
            from_date,
            time.min
        )

        query = query.filter(
            Billing.created_at >= from_datetime
        )

    if to_date is not None:
        next_day = to_date + timedelta(days=1)

        to_datetime = datetime.combine(
            next_day,
            time.min
        )

        query = query.filter(
            Billing.created_at < to_datetime
        )

    billings = query.order_by(
        Billing.created_at.asc()
    ).all()

    # -------------------------
    # Total Revenue
    # -------------------------

    total_revenue = sum(
        billing.total_amount
        for billing in billings
    )

    # -------------------------
    # Revenue By Doctor
    # -------------------------

    doctor_revenue = {}

    for billing in billings:
        if billing.doctor_id not in doctor_revenue:
            doctor_revenue[billing.doctor_id] = 0

        doctor_revenue[billing.doctor_id] += (
            billing.total_amount
        )

    revenue_by_doctor = [
        {
            "doctor_id": doctor_id_value,
            "total_revenue": revenue
        }
        for doctor_id_value, revenue
        in sorted(doctor_revenue.items())
    ]

    # -------------------------
    # Revenue By Day
    # -------------------------

    daily_revenue = {}

    for billing in billings:
        billing_date = billing.created_at.date()

        if billing_date not in daily_revenue:
            daily_revenue[billing_date] = 0

        daily_revenue[billing_date] += (
            billing.total_amount
        )

    revenue_by_day = [
        {
            "date": revenue_date,
            "total_revenue": revenue
        }
        for revenue_date, revenue
        in sorted(daily_revenue.items())
    ]

    return {
        "doctor_id": doctor_id,
        "from_date": from_date,
        "to_date": to_date,
        "total_revenue": total_revenue,
        "revenue_by_doctor": revenue_by_doctor,
        "revenue_by_day": revenue_by_day
    }
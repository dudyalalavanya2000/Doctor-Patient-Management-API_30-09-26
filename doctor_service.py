from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Doctor


# =========================
# Get Doctor
# =========================

def get_doctor_or_404(
    db: Session,
    doctor_id: int
):
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    return doctor


# =========================
# Get Active Doctor
# =========================

def get_active_doctor_or_404(
    db: Session,
    doctor_id: int
):
    doctor = get_doctor_or_404(
        db,
        doctor_id
    )

    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor is inactive"
        )

    return doctor


# =========================
# Validate Doctor Email
# =========================

def validate_doctor_email(
    db: Session,
    email: str,
    doctor_id: int | None = None
):
    query = db.query(Doctor).filter(
        Doctor.email == email
    )

    if doctor_id is not None:
        query = query.filter(
            Doctor.id != doctor_id
        )

    existing = query.first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor email already registered"
        )
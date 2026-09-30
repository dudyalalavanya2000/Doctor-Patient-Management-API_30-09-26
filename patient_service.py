from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Doctor, Patient


# =========================
# Get Patient
# =========================

def get_patient_or_404(
    db: Session,
    patient_id: int
):
    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    return patient


# =========================
# Validate Patient Doctor
# =========================

def validate_patient_doctor(
    db: Session,
    doctor_id: int | None
):
    if doctor_id is None:
        return None

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
            detail=(
                "Cannot assign patient to an inactive doctor"
            )
        )

    return doctor
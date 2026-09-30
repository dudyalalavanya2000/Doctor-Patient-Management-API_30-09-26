from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Appointment, Doctor, Patient


# =========================
# Appointment Services
# =========================

def get_appointment_or_404(
    db: Session,
    appointment_id: int
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    return appointment


def validate_appointment_references(
    db: Session,
    doctor_id: int,
    patient_id: int
):
    # Check doctor
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

    # Check patient
    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    return doctor, patient


def check_appointment_overlap(
    db: Session,
    doctor_id: int,
    appointment_date,
    appointment_id: int | None = None
):
    """
    Each appointment is treated as a 30-minute slot.

    Example:
    10:00 - 10:30

    Another appointment at 10:15 would overlap.
    An appointment at 10:30 is allowed.
    """

    appointment_duration = timedelta(minutes=30)

    new_start = appointment_date
    new_end = new_start + appointment_duration

    query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status == "scheduled",
        Appointment.appointment_date < new_end,
        Appointment.appointment_date > (
            new_start - appointment_duration
        )
    )

    if appointment_id is not None:
        query = query.filter(
            Appointment.id != appointment_id
        )

    existing_appointment = query.first()

    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Doctor already has an overlapping "
                "scheduled appointment"
            )
        )
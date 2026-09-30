from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.utils import get_current_user, require_admin
from app.database import get_db
from app.models import Billing, Doctor, Patient, User
from app.schemas import (
    PatientCreate,
    PatientPatch,
    PatientResponse,
    PatientUpdate,
    PatientListResponse,
    BillingListResponse
)
from app.services import (
    get_active_doctor_or_404,
    get_patient_or_404,
    validate_patient_doctor
)


router = APIRouter()


# =========================
# Create Patient
# Admin Only
# =========================

@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
    description=(
        "Creates a new patient record. "
        "Admin authorization is required. "
        "If a doctor_id is provided, the doctor must exist and be active."
    ),
    responses={
        201: {"description": "Patient created successfully"},
        400: {"description": "Invalid or inactive doctor"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        422: {"description": "Validation error"}
    }
)
def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    validate_patient_doctor(
        db,
        patient_data.doctor_id
    )

    new_patient = Patient(
        name=patient_data.name,
        age=patient_data.age,
        phone=patient_data.phone,
        doctor_id=patient_data.doctor_id,
        created_by=current_user.id,
        updated_by=current_user.id
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return new_patient


# =========================
# Get Patients
# =========================

@router.get(
    "/",
    response_model=PatientListResponse,
    summary="Get patients",
    description=(
        "Returns a paginated list of patients. "
        "Admins can view all patients. "
        "Doctors can view only their assigned patients. "
        "Patients can optionally be filtered by age."
    ),
    responses={
        200: {"description": "Patients returned successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"}
    }
)
def get_patients(
    age_gt: int | None = Query(
        default=None,
        gt=0,
        description="Return patients older than the specified age",
        examples=[25]
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number",
        examples=[1]
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Number of patients per page",
        examples=[10]
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Patient).options(
        joinedload(Patient.doctor)
    )

    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        query = query.filter(
            Patient.doctor_id == current_user.doctor.id
        )

    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if age_gt is not None:
        query = query.filter(
            Patient.age > age_gt
        )

    total = query.count()

    offset = (page - 1) * limit

    patients = query.offset(
        offset
    ).limit(
        limit
    ).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": patients
    }


# =========================
# Get Patient Billings
# Admin / Doctor
# With Pagination
# =========================

@router.get(
    "/{patient_id}/billings",
    response_model=BillingListResponse,
    summary="Get patient billings",
    description=(
        "Returns paginated billing records for a patient. "
        "Admins can view any patient's billings. "
        "Doctors can view billings only for their assigned patients."
    ),
    responses={
        200: {
            "description": "Patient billings returned successfully"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Access denied"
        },
        404: {
            "description": "Patient not found"
        }
    }
)
def get_patient_billings(
    patient_id: int,
    page: int = Query(
        default=1,
        ge=1,
        description="Page number",
        examples=[1]
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Number of billing records per page",
        examples=[10]
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check patient exists
    patient = db.query(Patient).filter(
        Patient.id == patient_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # Get only active billings
    query = db.query(Billing).filter(
        Billing.patient_id == patient_id,
        Billing.is_active == True
    )

    # Doctor authorization
    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        # Doctor can only view assigned patients
        if patient.doctor_id != current_user.doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You can only view billings "
                    "for your assigned patients"
                )
            )

        # Make sure billing also belongs to this doctor
        query = query.filter(
            Billing.doctor_id == current_user.doctor.id
        )

    # Admin can view all patient billings
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get total number of matching records
    total = query.count()

    # Calculate pagination offset
    offset = (page - 1) * limit

    # Get paginated billings
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
# Get Patient
# =========================

@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient by ID",
    description=(
        "Returns details of a specific patient. "
        "Admins can access any patient. "
        "Doctors can access only patients assigned to them."
    ),
    responses={
        200: {"description": "Patient returned successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied"},
        404: {"description": "Patient not found"}
    }
)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = get_patient_or_404(
        db,
        patient_id
    )

    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        if patient.doctor_id != current_user.doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You can access only your assigned patients"
                )
            )

    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return patient


# =========================
# PUT Patient
# Admin Only
# =========================

@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient",
    description=(
        "Updates all patient details. "
        "Admin authorization is required. "
        "If doctor_id is provided, the doctor must exist and be active."
    ),
    responses={
        200: {"description": "Patient updated successfully"},
        400: {"description": "Invalid or inactive doctor"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "Patient not found"},
        422: {"description": "Validation error"}
    }
)
def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    patient = get_patient_or_404(
        db,
        patient_id
    )

    validate_patient_doctor(
        db,
        patient_data.doctor_id
    )

    patient.name = patient_data.name
    patient.age = patient_data.age
    patient.phone = patient_data.phone
    patient.doctor_id = patient_data.doctor_id
    patient.updated_by = current_user.id

    db.commit()
    db.refresh(patient)

    return patient


# =========================
# PATCH Patient
# Admin Only
# =========================

@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Partially update patient",
    description=(
        "Updates one or more patient fields. "
        "Admin authorization is required. "
        "Only the fields provided in the request are modified."
    ),
    responses={
        200: {"description": "Patient partially updated successfully"},
        400: {"description": "Invalid or inactive doctor"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "Patient not found"},
        422: {"description": "Validation error"}
    }
)
def patch_patient(
    patient_id: int,
    patient_data: PatientPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    patient = get_patient_or_404(
        db,
        patient_id
    )

    update_data = patient_data.model_dump(
        exclude_unset=True
    )

    if "doctor_id" in update_data:
        validate_patient_doctor(
            db,
            update_data["doctor_id"]
        )

    for field, value in update_data.items():
        setattr(
            patient,
            field,
            value
        )

    patient.updated_by = current_user.id

    db.commit()
    db.refresh(patient)

    return patient


# =========================
# Assign Patient To Doctor
# Admin Only
# =========================

@router.put(
    "/{patient_id}/assign-doctor/{doctor_id}",
    response_model=PatientResponse,
    summary="Assign patient to doctor",
    description=(
        "Assigns a patient to an active doctor. "
        "Admin authorization is required."
    ),
    responses={
        200: {"description": "Patient assigned to doctor successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "Patient or doctor not found"}
    }
)
def assign_patient_to_doctor(
    patient_id: int,
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    patient = get_patient_or_404(
        db,
        patient_id
    )

    doctor = get_active_doctor_or_404(
        db,
        doctor_id
    )

    patient.doctor_id = doctor.id

    db.commit()
    db.refresh(patient)

    return patient


# =========================
# Delete Patient
# Admin Only
# =========================

@router.delete(
    "/{patient_id}",
    summary="Delete patient",
    description=(
        "Deletes a patient record from the database. "
        "Admin authorization is required."
    ),
    responses={
        200: {"description": "Patient deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
        404: {"description": "Patient not found"}
    }
)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    patient = get_patient_or_404(
        db,
        patient_id
    )

    db.delete(patient)
    db.commit()

    return {
        "message": "Patient deleted successfully"
    }
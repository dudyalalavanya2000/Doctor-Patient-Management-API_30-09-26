import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.utils import get_current_user, require_admin
from app.database import get_db
from app.models import Billing, Doctor, Patient, User
from app.schemas import (
    DoctorCreate,
    DoctorPatch,
    DoctorResponse,
    DoctorListResponse,
    DoctorUpdate,
    PatientResponse,
    BillingListResponse
)
from app.services import (
    get_doctor_or_404,
    validate_doctor_email
)


logger = logging.getLogger(__name__)

router = APIRouter()


# =========================
# Create Doctor
# Admin Only
# =========================

@router.post(
    "/",
    response_model=DoctorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new doctor",
    description=(
        "Creates a new doctor profile. "
        "Admin authorization is required. "
        "A registered doctor user account with the same email "
        "must already exist."
    ),
    responses={
        201: {
            "description": "Doctor created successfully"
        },
        400: {
            "description": (
                "Doctor email already exists, "
                "doctor user account is missing, "
                "or doctor profile already exists"
            )
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        }
    }
)
def create_doctor(
    doctor_data: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    validate_doctor_email(
        db,
        doctor_data.email
    )

    user = db.query(User).filter(
        User.email == doctor_data.email,
        User.role == "doctor"
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A doctor user account with this email "
                "must be registered first"
            )
        )

    if user.doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor profile already exists"
        )

    doctor = Doctor(
        name=doctor_data.name,
        specialization=doctor_data.specialization,
        email=doctor_data.email,
        is_active=doctor_data.is_active,
        user_id=user.id,
        created_by=current_user.id,
        updated_by=current_user.id
    )

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    logger.info(
        "Doctor created: %s",
        doctor.id
    )

    return doctor


# =========================
# Get Doctors
# =========================

@router.get(
    "/",
    response_model=DoctorListResponse,
    summary="Get doctors",
    description=(
        "Returns a paginated list of doctors. "
        "Doctors can be filtered by specialization "
        "and active status."
    ),
    responses={
        200: {
            "description": "List of doctors returned successfully"
        },
        401: {
            "description": "Authentication required"
        }
    }
)
def get_doctors(
    specialization: str | None = Query(
        default=None,
        description="Filter doctors by specialization",
        examples=["Cardiology"]
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter doctors by active status",
        examples=[True]
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
        description="Number of doctors per page",
        examples=[10]
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Doctor)

    if specialization:
        query = query.filter(
            Doctor.specialization.ilike(
                f"%{specialization}%"
            )
        )

    if is_active is not None:
        query = query.filter(
            Doctor.is_active == is_active
        )

    total = query.count()

    offset = (page - 1) * limit

    doctors = query.offset(
        offset
    ).limit(
        limit
    ).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": doctors
    }


# =========================
# Get Doctor
# =========================

@router.get(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="Get doctor by ID",
    description="Returns the details of a specific doctor.",
    responses={
        200: {
            "description": "Doctor found successfully"
        },
        401: {
            "description": "Authentication required"
        },
        404: {
            "description": "Doctor not found"
        }
    }
)
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_doctor_or_404(
        db,
        doctor_id
    )


# =========================
# Get Doctor's Patients
# =========================

@router.get(
    "/{doctor_id}/patients",
    response_model=list[PatientResponse],
    summary="Get patients assigned to a doctor",
    description=(
        "Returns patients assigned to the specified doctor. "
        "Admins can access any doctor's patients. "
        "Doctors can access only their own assigned patients."
    ),
    responses={
        200: {
            "description": "Assigned patients returned successfully"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": (
                "Doctor attempted to access another doctor's patients"
            )
        },
        404: {
            "description": "Doctor not found"
        }
    }
)
def get_doctor_patients(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_doctor_or_404(
        db,
        doctor_id
    )

    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        if current_user.doctor.id != doctor_id:
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

    return db.query(Patient).filter(
        Patient.doctor_id == doctor_id
    ).all()


# =========================
# Get Doctor Billings
# Admin / Doctor
# With Pagination
# =========================

@router.get(
    "/{doctor_id}/billings",
    response_model=BillingListResponse,
    summary="Get doctor billings",
    description=(
        "Returns paginated billing records related to a doctor. "
        "Admins can view any doctor's billings. "
        "Doctors can view only their own billing records."
    ),
    responses={
        200: {
            "description": "Doctor billings returned successfully"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Access denied"
        },
        404: {
            "description": "Doctor not found"
        }
    }
)
def get_doctor_billings(
    doctor_id: int,
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
    # Check doctor exists
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    # Doctor authorization
    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        # Doctor can only view their own billings
        if current_user.doctor.id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own billings"
            )

    # Admin can view any doctor's billings
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get only active billings
    query = db.query(Billing).filter(
        Billing.doctor_id == doctor_id,
        Billing.is_active == True
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
# PUT Doctor
# Admin Only
# =========================

@router.put(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="Update doctor",
    description=(
        "Updates all doctor details. "
        "Admin authorization is required."
    ),
    responses={
        200: {
            "description": "Doctor updated successfully"
        },
        400: {
            "description": "Doctor email is already registered"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        },
        404: {
            "description": "Doctor not found"
        }
    }
)
def update_doctor(
    doctor_id: int,
    doctor_data: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    doctor = get_doctor_or_404(
        db,
        doctor_id
    )

    validate_doctor_email(
        db,
        doctor_data.email,
        doctor_id
    )

    if doctor.user:

        existing_user = db.query(User).filter(
            User.email == doctor_data.email,
            User.id != doctor.user.id
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Email already registered by another user"
                )
            )

        doctor.user.email = doctor_data.email

    doctor.name = doctor_data.name
    doctor.specialization = doctor_data.specialization
    doctor.email = doctor_data.email
    doctor.is_active = doctor_data.is_active
    doctor.updated_by = current_user.id

    db.commit()
    db.refresh(doctor)

    return doctor


# =========================
# PATCH Doctor
# Admin Only
# =========================

@router.patch(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="Partially update doctor",
    description=(
        "Updates one or more doctor fields. "
        "Admin authorization is required."
    ),
    responses={
        200: {
            "description": "Doctor updated successfully"
        },
        400: {
            "description": "Invalid or duplicate doctor email"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        },
        404: {
            "description": "Doctor not found"
        }
    }
)
def patch_doctor(
    doctor_id: int,
    doctor_data: DoctorPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    doctor = get_doctor_or_404(
        db,
        doctor_id
    )

    update_data = doctor_data.model_dump(
        exclude_unset=True
    )

    if "email" in update_data:

        validate_doctor_email(
            db,
            update_data["email"],
            doctor_id
        )

        if doctor.user:

            existing_user = db.query(User).filter(
                User.email == update_data["email"],
                User.id != doctor.user.id
            ).first()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Email already registered by another user"
                    )
                )

            doctor.user.email = update_data["email"]

    for field, value in update_data.items():
        setattr(
            doctor,
            field,
            value
        )

    doctor.updated_by = current_user.id

    db.commit()
    db.refresh(doctor)

    return doctor


# =========================
# Soft Delete Doctor
# Admin Only
# =========================

@router.delete(
    "/{doctor_id}",
    summary="Deactivate doctor",
    description=(
        "Soft deletes a doctor by setting is_active to false. "
        "The doctor record remains in the database. "
        "Admin authorization is required."
    ),
    responses={
        200: {
            "description": "Doctor deactivated successfully"
        },
        400: {
            "description": "Doctor is already inactive"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        },
        404: {
            "description": "Doctor not found"
        }
    }
)
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    doctor = get_doctor_or_404(
        db,
        doctor_id
    )

    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor is already inactive"
        )

    doctor.is_active = False

    db.commit()

    logger.info(
        "Doctor soft deleted: %s",
        doctor_id
    )

    return {
        "message": "Doctor deleted successfully"
    }
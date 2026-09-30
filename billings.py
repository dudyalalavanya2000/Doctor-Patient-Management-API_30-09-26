from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.utils import get_current_user, require_admin
from app.database import get_db
from app.models import Billing, User
from app.schemas import (
    BillingCreate,
    BillingListResponse,
    BillingPatch,
    BillingResponse,
    BillingUpdate,
    PaymentStatus,
)
from app.services.billing_service import (
    calculate_total_amount,
    check_duplicate_billing,
    get_billing_or_404,
    get_filtered_billings,
    validate_billing_references,
)


router = APIRouter()


# =========================
# Create Billing
# Admin Only
# =========================

@router.post(
    "/",
    response_model=BillingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a billing record",
    description=(
        "Creates a billing record for a patient. "
        "Admin authorization is required. "
        "The doctor must be active. "
        "If an appointment is provided, it must belong to "
        "the same doctor and patient and must not be cancelled. "
        "The appointment status is updated to completed "
        "within the same database transaction. "
        "If any operation fails, all changes are rolled back. "
        "Duplicate billing for the same appointment is not allowed."
    ),
    responses={
        201: {
            "description": "Billing record created successfully"
        },
        400: {
            "description": "Invalid billing information"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        },
        404: {
            "description": "Doctor, patient, or appointment not found"
        },
        500: {
            "description": "Transaction failed and was rolled back"
        }
    }
)
def create_billing(
    billing_data: BillingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # =========================
    # Validate References
    # =========================

    doctor, patient, appointment = validate_billing_references(
        db,
        billing_data.doctor_id,
        billing_data.patient_id,
        billing_data.appointment_id
    )

    # =========================
    # Check Duplicate Billing
    # =========================

    if billing_data.appointment_id is not None:
        check_duplicate_billing(
            db,
            billing_data.appointment_id
        )

    # =========================
    # Calculate Total
    # =========================

    total_amount = calculate_total_amount(
        billing_data.consultation_fee,
        billing_data.additional_charges
    )

    try:
        # =========================
        # Create Billing
        # =========================

        billing = Billing(
            patient_id=billing_data.patient_id,
            doctor_id=billing_data.doctor_id,
            appointment_id=billing_data.appointment_id,
            consultation_fee=billing_data.consultation_fee,
            additional_charges=billing_data.additional_charges,
            total_amount=total_amount,
            payment_status=billing_data.payment_status,
            payment_mode=billing_data.payment_mode,
            is_active=True
        )

        db.add(billing)

        # =========================
        # Update Appointment
        # =========================

        if appointment is not None:
            appointment.status = "completed"

        # =========================
        # Flush Changes
        # =========================

        # Sends pending changes to the database
        # without committing the transaction.
        db.flush()

        # =========================
        # Commit Transaction
        # =========================

        # Billing creation and appointment update
        # are committed together.
        db.commit()

        db.refresh(billing)

        return billing

    except IntegrityError:
        # =========================
        # Rollback Transaction
        # =========================

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Billing could not be created because "
                "a database constraint was violated."
            )
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        # =========================
        # Rollback Unexpected Error
        # =========================

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Billing creation failed. "
                "All changes have been rolled back."
            )
        )


# =========================
# Get Billing List
# Filters + Pagination
# =========================

@router.get(
    "/",
    response_model=BillingListResponse,
    summary="Get billing records",
    description=(
        "Returns billing records with optional filters and pagination. "
        "Filters include payment status, doctor, patient, and date range. "
        "Admins can view all billing records. "
        "Doctors can only view billing records related to their patients."
    ),
    responses={
        200: {
            "description": "Billing records returned successfully"
        },
        400: {
            "description": "Invalid filter values"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Access denied"
        }
    }
)
def get_billings(
    payment_status: PaymentStatus | None = Query(
        default=None,
        description="Filter by payment status",
        examples=["paid"]
    ),
    doctor_id: int | None = Query(
        default=None,
        ge=1,
        description="Filter by doctor ID",
        examples=[1]
    ),
    patient_id: int | None = Query(
        default=None,
        ge=1,
        description="Filter by patient ID",
        examples=[1]
    ),
    from_date: date | None = Query(
        default=None,
        description="Filter from this date",
        examples=["2026-10-01"]
    ),
    to_date: date | None = Query(
        default=None,
        description="Filter up to this date",
        examples=["2026-10-31"]
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
        description="Number of records per page",
        examples=[10]
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate date range

    if from_date is not None and to_date is not None:

        if from_date > to_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date cannot be later than to_date"
            )

    # -------------------------
    # Doctor Authorization
    # -------------------------

    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        doctor_id = current_user.doctor.id

    elif current_user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return get_filtered_billings(
        db=db,
        payment_status=payment_status,
        doctor_id=doctor_id,
        patient_id=patient_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit
    )


# =========================
# Get Billing By ID
# =========================

@router.get(
    "/{billing_id}",
    response_model=BillingResponse,
    summary="Get billing by ID",
    description=(
        "Returns a billing record. "
        "Admins can access any billing record. "
        "Doctors can access billing records related to their patients."
    ),
    responses={
        200: {
            "description": "Billing record returned successfully"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Access denied"
        },
        404: {
            "description": "Billing record not found"
        }
    }
)
def get_billing(
    billing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    billing = get_billing_or_404(
        db,
        billing_id
    )

    if current_user.role == "doctor":

        if not current_user.doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found"
            )

        if billing.doctor_id != current_user.doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You can only view billings "
                    "related to your patients"
                )
            )

    elif current_user.role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return billing


# =========================
# PUT Billing
# Admin Only
# =========================

@router.put(
    "/{billing_id}",
    response_model=BillingResponse,
    summary="Update billing",
    description=(
        "Updates all billing details. "
        "Admin authorization is required."
    ),
    responses={
        200: {
            "description": "Billing updated successfully"
        },
        400: {
            "description": "Invalid billing information"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        },
        404: {
            "description": (
                "Billing, doctor, patient, or appointment not found"
            )
        }
    }
)
def update_billing(
    billing_id: int,
    billing_data: BillingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    billing = get_billing_or_404(
        db,
        billing_id
    )

    validate_billing_references(
        db,
        billing_data.doctor_id,
        billing_data.patient_id,
        billing_data.appointment_id
    )

    if billing_data.appointment_id is not None:
        check_duplicate_billing(
            db,
            billing_data.appointment_id,
            billing_id
        )

    billing.patient_id = billing_data.patient_id
    billing.doctor_id = billing_data.doctor_id
    billing.appointment_id = billing_data.appointment_id
    billing.consultation_fee = billing_data.consultation_fee
    billing.additional_charges = billing_data.additional_charges

    billing.total_amount = calculate_total_amount(
        billing_data.consultation_fee,
        billing_data.additional_charges
    )

    billing.payment_status = billing_data.payment_status
    billing.payment_mode = billing_data.payment_mode

    db.commit()
    db.refresh(billing)

    return billing


# =========================
# PATCH Billing
# Admin Only
# =========================

@router.patch(
    "/{billing_id}",
    response_model=BillingResponse,
    summary="Partially update billing",
    description=(
        "Updates one or more billing fields. "
        "Admin authorization is required. "
        "Total amount is recalculated automatically."
    ),
    responses={
        200: {
            "description": "Billing partially updated successfully"
        },
        400: {
            "description": "Invalid billing information"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        },
        404: {
            "description": (
                "Billing, doctor, patient, or appointment not found"
            )
        }
    }
)
def patch_billing(
    billing_id: int,
    billing_data: BillingPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    billing = get_billing_or_404(
        db,
        billing_id
    )

    update_data = billing_data.model_dump(
        exclude_unset=True
    )

    doctor_id = update_data.get(
        "doctor_id",
        billing.doctor_id
    )

    patient_id = update_data.get(
        "patient_id",
        billing.patient_id
    )

    appointment_id = update_data.get(
        "appointment_id",
        billing.appointment_id
    )

    validate_billing_references(
        db,
        doctor_id,
        patient_id,
        appointment_id
    )

    if appointment_id is not None:
        check_duplicate_billing(
            db,
            appointment_id,
            billing_id
        )

    for field, value in update_data.items():
        setattr(
            billing,
            field,
            value
        )

    consultation_fee = update_data.get(
        "consultation_fee",
        billing.consultation_fee
    )

    additional_charges = update_data.get(
        "additional_charges",
        billing.additional_charges
    )

    billing.total_amount = calculate_total_amount(
        consultation_fee,
        additional_charges
    )

    db.commit()
    db.refresh(billing)

    return billing


# =========================
# Soft Delete Billing
# Admin Only
# =========================

@router.delete(
    "/{billing_id}",
    summary="Delete billing",
    description=(
        "Soft deletes a billing record by setting is_active to false. "
        "The billing record remains in the database. "
        "Admin authorization is required."
    ),
    responses={
        200: {
            "description": "Billing deleted successfully"
        },
        400: {
            "description": "Billing is already inactive"
        },
        401: {
            "description": "Authentication required"
        },
        403: {
            "description": "Admin access required"
        },
        404: {
            "description": "Billing record not found"
        }
    }
)
def delete_billing(
    billing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    billing = db.query(Billing).filter(
        Billing.id == billing_id
    ).first()

    if not billing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )

    if not billing.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Billing is already inactive"
        )

    billing.is_active = False

    db.commit()
    db.refresh(billing)

    return {
        "message": "Billing deleted successfully"
    }
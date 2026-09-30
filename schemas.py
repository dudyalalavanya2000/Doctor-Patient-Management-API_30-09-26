from datetime import date as date_type, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================
# Authentication Schemas
# =========================

class UserRegister(BaseModel):
    name: str = Field(
        min_length=1,
        description="User full name",
        examples=["Lavanya Reddy"]
    )
    email: EmailStr = Field(
        description="User email address",
        examples=["lavanya@gmail.com"]
    )
    password: str = Field(
        min_length=6,
        description="User password",
        examples=["password123"]
    )
    role: Literal["admin", "doctor"] = Field(
        default="doctor",
        description="User role",
        examples=["doctor"]
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(
        description="User email address",
        examples=["lavanya@gmail.com"]
    )
    password: str = Field(
        description="User password",
        examples=["password123"]
    )


class Token(BaseModel):
    access_token: str
    token_type: str


# =========================
# Doctor Schemas
# =========================

class DoctorCreate(BaseModel):
    name: str = Field(
        min_length=1,
        description="Doctor name",
        examples=["Dr. Rathi"]
    )
    specialization: str = Field(
        min_length=1,
        description="Doctor specialization",
        examples=["Cardiology"]
    )
    email: EmailStr = Field(
        description="Doctor email address",
        examples=["rathi@gmail.com"]
    )
    is_active: bool = Field(
        default=True,
        description="Doctor active status",
        examples=[True]
    )


class DoctorUpdate(BaseModel):
    name: str = Field(
        min_length=1,
        description="Doctor name",
        examples=["Dr. Rathi"]
    )
    specialization: str = Field(
        min_length=1,
        description="Doctor specialization",
        examples=["Cardiology"]
    )
    email: EmailStr = Field(
        description="Doctor email address",
        examples=["rathi@gmail.com"]
    )
    is_active: bool = Field(
        description="Doctor active status",
        examples=[True]
    )


class DoctorPatch(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Doctor name",
        examples=["Dr. Rathi"]
    )
    specialization: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Doctor specialization",
        examples=["Cardiology"]
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Doctor email address",
        examples=["rathi@gmail.com"]
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Doctor active status",
        examples=[True]
    )


class DoctorResponse(BaseModel):
    id: int
    name: str
    specialization: str
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================
# Patient Schemas
# =========================

class PatientCreate(BaseModel):
    name: str = Field(
        min_length=1,
        description="Patient name",
        examples=["Meena"]
    )
    age: int = Field(
        gt=0,
        description="Patient age",
        examples=[25]
    )
    phone: str = Field(
        min_length=1,
        description="Patient phone number",
        examples=["8688094563"]
    )


class PatientUpdate(BaseModel):
    name: str = Field(
        min_length=1,
        description="Patient name",
        examples=["Meena"]
    )
    age: int = Field(
        gt=0,
        description="Patient age",
        examples=[25]
    )
    phone: str = Field(
        min_length=1,
        description="Patient phone number",
        examples=["8688094563"]
    )
    doctor_id: Optional[int] = Field(
        default=None,
        description="Assigned doctor ID",
        examples=[1]
    )


class PatientPatch(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Patient name",
        examples=["Meena"]
    )
    age: Optional[int] = Field(
        default=None,
        gt=0,
        description="Patient age",
        examples=[25]
    )
    phone: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Patient phone number",
        examples=["8688094563"]
    )
    doctor_id: Optional[int] = Field(
        default=None,
        description="Assigned doctor ID",
        examples=[1]
    )


class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    phone: str
    doctor_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================
# List / Pagination Schemas
# =========================

class DoctorListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: list[DoctorResponse]


class PatientListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: list[PatientResponse]


# =========================
# Appointment Schemas
# =========================

AppointmentStatus = Literal[
    "scheduled",
    "completed",
    "cancelled"
]


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(
        description="Doctor ID",
        examples=[1]
    )
    patient_id: int = Field(
        description="Patient ID",
        examples=[1]
    )
    appointment_date: datetime = Field(
        description="Appointment date and time",
        examples=["2026-10-01T10:00:00"]
    )
    status: AppointmentStatus = Field(
        default="scheduled",
        description="Appointment status",
        examples=["scheduled"]
    )


class AppointmentUpdate(BaseModel):
    doctor_id: int = Field(
        description="Doctor ID",
        examples=[1]
    )
    patient_id: int = Field(
        description="Patient ID",
        examples=[1]
    )
    appointment_date: datetime = Field(
        description="Appointment date and time",
        examples=["2026-10-01T10:00:00"]
    )
    status: AppointmentStatus = Field(
        description="Appointment status",
        examples=["completed"]
    )


class AppointmentPatch(BaseModel):
    doctor_id: Optional[int] = Field(
        default=None,
        description="Doctor ID",
        examples=[1]
    )
    patient_id: Optional[int] = Field(
        default=None,
        description="Patient ID",
        examples=[1]
    )
    appointment_date: Optional[datetime] = Field(
        default=None,
        description="Appointment date and time",
        examples=["2026-10-01T10:00:00"]
    )
    status: Optional[AppointmentStatus] = Field(
        default=None,
        description="Appointment status",
        examples=["completed"]
    )


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    appointment_date: datetime
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =========================
# Billing Schemas
# =========================

PaymentStatus = Literal[
    "pending",
    "paid",
    "cancelled"
]

PaymentMode = Literal[
    "cash",
    "card",
    "upi"
]


class BillingCreate(BaseModel):
    patient_id: int = Field(
        description="ID of the patient",
        examples=[1]
    )
    doctor_id: int = Field(
        description="ID of the doctor",
        examples=[1]
    )
    appointment_id: Optional[int] = Field(
        default=None,
        description="Optional appointment ID",
        examples=[1]
    )
    consultation_fee: int = Field(
        ge=0,
        description="Consultation fee",
        examples=[500]
    )
    additional_charges: int = Field(
        default=0,
        ge=0,
        description="Additional charges",
        examples=[100]
    )
    payment_status: PaymentStatus = Field(
        default="pending",
        description="Payment status",
        examples=["pending"]
    )
    payment_mode: Optional[PaymentMode] = Field(
        default=None,
        description="Payment mode",
        examples=["upi"]
    )


class BillingUpdate(BaseModel):
    patient_id: int = Field(
        description="ID of the patient",
        examples=[1]
    )
    doctor_id: int = Field(
        description="ID of the doctor",
        examples=[1]
    )
    appointment_id: Optional[int] = Field(
        default=None,
        description="Optional appointment ID",
        examples=[1]
    )
    consultation_fee: int = Field(
        ge=0,
        description="Consultation fee",
        examples=[500]
    )
    additional_charges: int = Field(
        default=0,
        ge=0,
        description="Additional charges",
        examples=[100]
    )
    payment_status: PaymentStatus = Field(
        description="Payment status",
        examples=["paid"]
    )
    payment_mode: Optional[PaymentMode] = Field(
        default=None,
        description="Payment mode",
        examples=["upi"]
    )


class BillingPatch(BaseModel):
    patient_id: Optional[int] = Field(
        default=None,
        description="ID of the patient",
        examples=[1]
    )
    doctor_id: Optional[int] = Field(
        default=None,
        description="ID of the doctor",
        examples=[1]
    )
    appointment_id: Optional[int] = Field(
        default=None,
        description="Optional appointment ID",
        examples=[1]
    )
    consultation_fee: Optional[int] = Field(
        default=None,
        ge=0,
        description="Consultation fee",
        examples=[500]
    )
    additional_charges: Optional[int] = Field(
        default=None,
        ge=0,
        description="Additional charges",
        examples=[100]
    )
    payment_status: Optional[PaymentStatus] = Field(
        default=None,
        description="Payment status",
        examples=["paid"]
    )
    payment_mode: Optional[PaymentMode] = Field(
        default=None,
        description="Payment mode",
        examples=["upi"]
    )


class BillingResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int] = None
    consultation_fee: int
    additional_charges: int
    total_amount: int
    payment_status: PaymentStatus
    payment_mode: Optional[PaymentMode] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BillingListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: list[BillingResponse]


# =========================
# Revenue Report Schemas
# =========================

class RevenueByDoctor(BaseModel):
    doctor_id: int = Field(
        description="Doctor ID",
        examples=[1]
    )
    total_revenue: int = Field(
        description="Total revenue generated by the doctor",
        examples=[5000]
    )


class RevenueByDay(BaseModel):
    date: date_type = Field(
        description="Revenue date",
        examples=["2026-10-01"]
    )
    total_revenue: int = Field(
        description="Total revenue generated on this date",
        examples=[2500]
    )


class RevenueReportResponse(BaseModel):
    doctor_id: Optional[int] = Field(
        default=None,
        description="Optional doctor ID filter",
        examples=[1]
    )
    from_date: Optional[date_type] = Field(
        default=None,
        description="Start date of the revenue report",
        examples=["2026-10-01"]
    )
    to_date: Optional[date_type] = Field(
        default=None,
        description="End date of the revenue report",
        examples=["2026-10-31"]
    )
    total_revenue: int = Field(
        description="Total revenue for the selected period",
        examples=[15000]
    )
    revenue_by_doctor: list[RevenueByDoctor] = Field(
        description="Revenue grouped by doctor"
    )
    revenue_by_day: list[RevenueByDay] = Field(
        description="Revenue grouped by day"
    )
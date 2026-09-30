from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from datetime import datetime
from sqlalchemy.orm import relationship

from app.database import Base


# =========================
# User Model
# =========================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    role = Column(
        String,
        nullable=False,
        default="doctor"
    )

    is_active = Column(
        Boolean,
        default=True
    )

    doctor = relationship(
    "Doctor",
    back_populates="user",
    uselist=False,
    foreign_keys="Doctor.user_id"
)


# =========================
# Doctor Model
# =========================

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    specialization = Column(
        String,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    updated_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=True
    )

    user = relationship(
    "User",
    back_populates="doctor",
    foreign_keys=[user_id]
)
    
    patients = relationship(
        "Patient",
        back_populates="doctor"
    )

    appointments = relationship(
    "Appointment",
    back_populates="doctor"
)
    billings = relationship(
        "Billing",
        back_populates="doctor"
    )

# =========================
# Patient Model
# =========================

class Patient(Base):
    __tablename__ = "patients"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        nullable=False
    )

    age = Column(
        Integer,
        nullable=False
    )

    phone = Column(
        String,
        nullable=False
    )

    doctor_id = Column(
    Integer,
    ForeignKey("doctors.id"),
    nullable=True,
    index=True
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    updated_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    doctor = relationship(
        "Doctor",
        back_populates="patients"
    )
    appointments = relationship(
        "Appointment",
        back_populates="patient"
    )
    billings = relationship(
        "Billing",
        back_populates="patient"
    )
# =========================
# Appointment Model
# =========================

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        index=True
    )

    appointment_date = Column(
        DateTime,
        nullable=False,
        index=True
    )

    status = Column(
        String,
        nullable=False,
        default="scheduled"
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    updated_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    doctor = relationship(
    "Doctor",
    back_populates="appointments"
)
    
    patient = relationship(
        "Patient",
        back_populates="appointments"
    )
    billing = relationship(
        "Billing",
        back_populates="appointment",
        uselist=False
    )
# =========================
# Billing Model
# =========================

class Billing(Base):
    __tablename__ = "billings"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False,
        index=True
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True
    )

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=True,
        unique=True,
        index=True
    )

    consultation_fee = Column(
        Integer,
        nullable=False
    )

    additional_charges = Column(
        Integer,
        nullable=False,
        default=0
    )

    total_amount = Column(
        Integer,
        nullable=False
    )

    payment_status = Column(
        String,
        nullable=False,
        default="pending"
    )

    payment_mode = Column(
        String,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    patient = relationship(
        "Patient",
        back_populates="billings"
    )

    doctor = relationship(
        "Doctor",
        back_populates="billings"
    )

    appointment = relationship(
        "Appointment",
        back_populates="billing"
    )
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
)

from app.services.doctor_service import (
    get_doctor_or_404,
    get_active_doctor_or_404,
    validate_doctor_email,
)

from app.services.patient_service import (
    get_patient_or_404,
    validate_patient_doctor,
)

from app.services.appointments import (
    get_appointment_or_404,
    validate_appointment_references,
    check_appointment_overlap,
)


class FakeQuery:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDB:
    def __init__(self, result=None):
        self.result = result

    def query(self, *args, **kwargs):
        return FakeQuery(self.result)


def test_get_doctor_or_404_success():
    doctor = SimpleNamespace(id=1, is_active=True)

    db = FakeDB(doctor)

    result = get_doctor_or_404(db, 1)

    assert result == doctor


def test_get_doctor_or_404_not_found():
    db = FakeDB(None)

    with pytest.raises(HTTPException) as exc:
        get_doctor_or_404(db, 999)

    assert exc.value.status_code == 404


def test_get_active_doctor_success():
    doctor = SimpleNamespace(id=1, is_active=True)

    db = FakeDB(doctor)

    result = get_active_doctor_or_404(db, 1)

    assert result == doctor


def test_get_active_doctor_inactive():
    doctor = SimpleNamespace(id=1, is_active=False)

    db = FakeDB(doctor)

    with pytest.raises(HTTPException) as exc:
        get_active_doctor_or_404(db, 1)

    assert exc.value.status_code == 400


def test_validate_doctor_email_duplicate():
    doctor = SimpleNamespace(id=1)

    db = FakeDB(doctor)

    with pytest.raises(HTTPException) as exc:
        validate_doctor_email(db, "doctor@example.com")

    assert exc.value.status_code == 400


def test_validate_doctor_email_available():
    db = FakeDB(None)

    result = validate_doctor_email(
        db,
        "newdoctor@example.com"
    )

    assert result is None


def test_get_patient_or_404_success():
    patient = SimpleNamespace(id=1)

    db = FakeDB(patient)

    result = get_patient_or_404(db, 1)

    assert result == patient


def test_get_patient_or_404_not_found():
    db = FakeDB(None)

    with pytest.raises(HTTPException) as exc:
        get_patient_or_404(db, 999)

    assert exc.value.status_code == 404


def test_validate_patient_doctor_none():
    db = FakeDB(None)

    result = validate_patient_doctor(db, None)

    assert result is None


def test_validate_patient_doctor_not_found():
    db = FakeDB(None)

    with pytest.raises(HTTPException) as exc:
        validate_patient_doctor(db, 999)

    assert exc.value.status_code == 404


def test_validate_patient_doctor_inactive():
    doctor = SimpleNamespace(
        id=1,
        is_active=False
    )

    db = FakeDB(doctor)

    with pytest.raises(HTTPException) as exc:
        validate_patient_doctor(db, 1)

    assert exc.value.status_code == 400


def test_validate_patient_doctor_success():
    doctor = SimpleNamespace(
        id=1,
        is_active=True
    )

    db = FakeDB(doctor)

    result = validate_patient_doctor(db, 1)

    assert result == doctor
    from app.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
)


def test_password_hash_and_verify():
    password = "TestPassword123"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_create_access_token():
    token = create_access_token({
        "sub": "1",
        "role": "admin"
    })

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

def test_get_current_user_success():
    from types import SimpleNamespace

    expected_user = SimpleNamespace(
        id=1,
        role="admin",
        is_active=True
    )

    token = create_access_token({
        "sub": "1",
        "role": "admin"
    })

    class UserQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return expected_user

    class UserDB:
        def query(self, *args, **kwargs):
            return UserQuery()

    result = get_current_user(
        token,
        UserDB()
    )

    assert result == expected_user


def test_get_current_user_invalid_token():
    db = FakeDB(None)

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            "invalid-token",
            db
        )

    assert exc.value.status_code == 401


def test_get_current_user_user_not_found():
    token = create_access_token({
        "sub": "999",
        "role": "admin"
    })

    db = FakeDB(None)

    with pytest.raises(HTTPException) as exc:
        get_current_user(token, db)

    assert exc.value.status_code == 401


def test_get_current_user_inactive_user():
    user = SimpleNamespace(
        id=1,
        role="doctor",
        is_active=False
    )

    class UserQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return user

    class UserDB:
        def query(self, *args, **kwargs):
            return UserQuery()

    token = create_access_token({
        "sub": "1",
        "role": "doctor"
    })

    with pytest.raises(HTTPException) as exc:
        get_current_user(token, UserDB())

    assert exc.value.status_code == 403


def test_require_admin_success():
    admin = SimpleNamespace(
        id=1,
        role="admin",
        is_active=True
    )

    result = require_admin(admin)

    assert result == admin


def test_require_admin_denied_for_doctor():
    doctor = SimpleNamespace(
        id=2,
        role="doctor",
        is_active=True
    )

    with pytest.raises(HTTPException) as exc:
        require_admin(doctor)

    assert exc.value.status_code == 403

    def test_get_appointment_or_404_success():
     from types import SimpleNamespace

    expected_appointment = SimpleNamespace(
        id=1,
        doctor_id=1,
        patient_id=1
    )

    class AppointmentQuery:
        def __init__(self, appointment):
            self.appointment = appointment

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.appointment

    class AppointmentDB:
        def query(self, *args, **kwargs):
            return AppointmentQuery(expected_appointment)

    result = get_appointment_or_404(
        AppointmentDB(),
        1
    )

    assert result == expected_appointment

def test_get_appointment_or_404_not_found():
    class AppointmentQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class AppointmentDB:
        def query(self, *args, **kwargs):
            return AppointmentQuery()

    try:
        get_appointment_or_404(
            AppointmentDB(),
            999
        )
        assert False
    except Exception as exc:
        assert exc.status_code == 404
        assert exc.detail == "Appointment not found"


def test_validate_appointment_references_success():
    doctor = SimpleNamespace(
        id=1,
        is_active=True
    )

    patient = SimpleNamespace(
        id=1
    )

    class Query:
        def __init__(self, result):
            self.result = result

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.result

    class AppointmentDB:
        def query(self, model):
            if model.__name__ == "Doctor":
                return Query(doctor)
            return Query(patient)

    result_doctor, result_patient = validate_appointment_references(
        AppointmentDB(),
        1,
        1
    )

    assert result_doctor == doctor
    assert result_patient == patient


def test_validate_appointment_doctor_not_found():
    class Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class AppointmentDB:
        def query(self, *args, **kwargs):
            return Query()

    try:
        validate_appointment_references(
            AppointmentDB(),
            999,
            1
        )
        assert False
    except Exception as exc:
        assert exc.status_code == 404
        assert exc.detail == "Doctor not found"


def test_validate_appointment_doctor_inactive():
    doctor = SimpleNamespace(
        id=1,
        is_active=False
    )

    class Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return doctor

    class AppointmentDB:
        def query(self, *args, **kwargs):
            return Query()

    try:
        validate_appointment_references(
            AppointmentDB(),
            1,
            1
        )
        assert False
    except Exception as exc:
        assert exc.status_code == 400
        assert exc.detail == "Doctor is inactive"


def test_validate_appointment_patient_not_found():
    doctor = SimpleNamespace(
        id=1,
        is_active=True
    )

    class DoctorQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return doctor

    class PatientQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class AppointmentDB:
        def query(self, model):
            if model.__name__ == "Doctor":
                return DoctorQuery()
            return PatientQuery()

    try:
        validate_appointment_references(
            AppointmentDB(),
            1,
            999
        )
        assert False
    except Exception as exc:
        assert exc.status_code == 404
        assert exc.detail == "Patient not found"

        def test_check_appointment_overlap_no_overlap():
         class FakeDB:
          def query(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    db = FakeDB()

    check_appointment_overlap(
        db,
        1,
        datetime(2026, 9, 29, 10, 0)
    )


def test_check_appointment_overlap_found():
    class FakeDB:
        def query(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return SimpleNamespace(
                id=1,
                doctor_id=1,
                appointment_date=datetime(
                    2026, 9, 29, 10, 15
                ),
                status="scheduled"
            )

    db = FakeDB()

    try:
        check_appointment_overlap(
            db,
            1,
            datetime(2026, 9, 29, 10, 0)
        )
        assert False
    except Exception as exc:
        assert exc.status_code == 400
        assert exc.detail == (
            "Doctor already has an overlapping scheduled appointment"
        )


def test_check_appointment_overlap_excludes_current():
    class FakeDB:
        def query(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    db = FakeDB()

    check_appointment_overlap(
        db,
        1,
        datetime(2026, 9, 29, 10, 0),
        appointment_id=1
    )
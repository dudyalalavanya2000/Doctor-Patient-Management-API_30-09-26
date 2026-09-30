from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def unique_email(prefix):
    return f"{prefix}_{uuid4().hex[:8]}@example.com"


def register_user(name, role):
    email = unique_email(name.lower().replace(" ", "_"))

    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "TestPassword123",
            "role": role
        }
    )

    assert response.status_code == 201
    return email


def login_user(email):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": "TestPassword123"
        }
    )

    assert response.status_code == 200
    return response.json()["access_token"]


def get_admin_token():
    email = register_user("Route Test Admin", "admin")
    return login_user(email)


def get_doctor_token():
    email = register_user("Route Test Doctor", "doctor")
    token = login_user(email)

    return email, token


def test_get_doctors_as_admin():
    token = get_admin_token()

    response = client.get(
        "/api/v1/doctors/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "data" in data


def test_get_patients_as_admin():
    token = get_admin_token()

    response = client.get(
        "/api/v1/patients/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "data" in data


def test_get_appointments_as_admin():
    token = get_admin_token()

    response = client.get(
        "/api/v1/appointments/",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_doctor_cannot_access_unassigned_patient():
    admin_token = get_admin_token()

    doctor_email = register_user(
        "Assigned Test Doctor",
        "doctor"
    )
    doctor_token = login_user(doctor_email)

    # Create a patient without assigning the doctor
    response = client.post(
        "/api/v1/patients/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Unassigned Test Patient",
            "age": 25,
            "phone": "9876543210"
        }
    )

    assert response.status_code == 201

    patient_id = response.json()["id"]

    response = client.get(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": f"Bearer {doctor_token}"}
    )

    assert response.status_code == 403


def test_doctor_can_view_own_patients_only():
    admin_token = get_admin_token()

    doctor_email = register_user(
        "Own Patient Doctor",
        "doctor"
    )
    doctor_token = login_user(doctor_email)

    # Register another doctor user
    second_doctor_email = register_user(
        "Second Test Doctor",
        "doctor"
    )

    # Create a doctor profile for the first doctor
    doctor_response = client.post(
        "/api/v1/doctors/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Own Patient Doctor",
            "specialization": "Cardiology",
            "email": doctor_email,
            "is_active": True
        }
    )

    assert doctor_response.status_code == 201

    doctor_id = doctor_response.json()["id"]

    # Create a patient assigned to the first doctor
    patient_response = client.post(
        "/api/v1/patients/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Assigned Patient",
            "age": 30,
            "phone": "9876543211",
            "doctor_id": doctor_id
        }
    )

    assert patient_response.status_code == 201

    patient_id = patient_response.json()["id"]

    response = client.get(
        f"/api/v1/doctors/{doctor_id}/patients",
        headers={"Authorization": f"Bearer {doctor_token}"}
    )

    assert response.status_code == 200
    assert any(
        patient["id"] == patient_id
        for patient in response.json()
    )
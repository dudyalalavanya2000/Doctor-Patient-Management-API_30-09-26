from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Doctor Patient API is running"


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_invalid_patient_age():
    response = client.post(
        "/api/v1/patients/",
        json={
            "name": "Test Patient",
            "age": 0,
            "phone": "9876543210"
        }
    )

    assert response.status_code in [401, 422]


def test_invalid_phone_number():
    response = client.post(
        "/api/v1/patients/",
        json={
            "name": "Test Patient",
            "age": 25,
            "phone": "12345"
        }
    )

    assert response.status_code in [401, 422]
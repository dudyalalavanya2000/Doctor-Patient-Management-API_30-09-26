from uuid import uuid4

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def unique_email(prefix):
    return f"{prefix}_{uuid4().hex[:8]}@example.com"

def test_register_user():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Test Admin",
           "email": unique_email("testadmin"),
            "password": "TestPassword123",
            "role": "admin"
        }
    )

    assert response.status_code == 201
    assert response.json()["message"] == "User registered successfully"


def test_register_duplicate_email():
    email = unique_email("duplicate")

    first_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate User",
            "email": email,
            "password": "TestPassword123",
            "role": "doctor"
        }
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Duplicate User",
            "email": email,
            "password": "TestPassword123",
            "role": "doctor"
        }
    )

    assert second_response.status_code == 400


def test_register_invalid_role():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Invalid Role User",
            "email": "invalidrole_unique@example.com",
            "password": "TestPassword123",
            "role": "user"
        }
    )

    assert response.status_code == 400


def test_login_success():
    email = unique_email("login")
    password = "TestPassword123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Login User",
            "email": email,
            "password": password,
            "role": "doctor"
        }
    )

    assert register_response.status_code == 201

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password():
    email = unique_email("wrongpassword")
    password = "TestPassword123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Wrong Password User",
            "email": email,
            "password": password,
            "role": "doctor"
        }
    )

    assert register_response.status_code == 201

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": "WrongPassword123"
        }
    )

    assert response.status_code == 401
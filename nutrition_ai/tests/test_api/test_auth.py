from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.core.security import get_password_hash

client = TestClient(app)

def test_register_user():
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword",
            "name": "Test User"
        }
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User registered successfully"

def test_register_duplicate_email():
    # 첫 번째 사용자 등록
    client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "testpassword",
            "name": "Test User 1"
        }
    )
    
    # 동일한 이메일로 두 번째 사용자 등록 시도
    response = client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "testpassword",
            "name": "Test User 2"
        }
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_login_success():
    # 사용자 등록
    client.post(
        "/auth/register",
        json={
            "email": "login@example.com",
            "password": "testpassword",
            "name": "Test User"
        }
    )
    
    # 로그인
    response = client.post(
        "/auth/token",
        data={
            "username": "login@example.com",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_wrong_password():
    response = client.post(
        "/auth/token",
        data={
            "username": "login@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"] 
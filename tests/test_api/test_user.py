from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db
from app.models.user import User

client = TestClient(app)

def test_create_user():
    response = client.post(
        "/users/",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword",
            "age": 30,
            "gender": "male",
            "health_conditions": "None",
            "allergies": "None"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_get_user():
    # 먼저 사용자 생성
    create_response = client.post(
        "/users/",
        json={
            "name": "Test User",
            "email": "test2@example.com",
            "password": "testpassword",
            "age": 30,
            "gender": "male",
            "health_conditions": "None",
            "allergies": "None"
        }
    )
    user_id = create_response.json()["id"]

    # 생성된 사용자 조회
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test2@example.com"

def test_get_nonexistent_user():
    response = client.get("/users/999")
    assert response.status_code == 404 
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

# In-memory SQLite database for isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_register_student_success(client: TestClient):
    """
    1. test_register_student_success:
       - POST /users/register with valid name, email, phone_number, password, and role="student".
       - Assert HTTP 201 Created; response contains user ID, name, email, phone number, role, but NO password.
    """
    payload = {
        "name": "Jane Student",
        "email": "jane@campus.edu",
        "phone_number": "555-123-4567",
        "password": "SecretPassword123!",
        "role": "student"
    }
    response = client.post("/users/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Jane Student"
    assert data["email"] == "jane@campus.edu"
    assert data["phone_number"] == "555-123-4567"
    assert data["role"] == "student"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_admin_success(client: TestClient):
    """
    2. test_register_admin_success:
       - POST /users/register with role="admin".
       - Assert HTTP 201 Created and response reflects role="admin".
    """
    payload = {
        "name": "Admin Officer",
        "email": "admin@campus.edu",
        "phone_number": "555-987-6543",
        "password": "AdminSecurePassword123!",
        "role": "admin"
    }
    response = client.post("/users/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["role"] == "admin"
    assert data["email"] == "admin@campus.edu"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_conflict(client: TestClient):
    """
    3. test_register_duplicate_email_conflict:
       - Register a user with email test@campus.edu. Attempt registering again with same email.
       - Assert HTTP 409 Conflict with informative error detail.
    """
    payload = {
        "name": "Original User",
        "email": "test@campus.edu",
        "phone_number": "555-000-1111",
        "password": "Password123!",
        "role": "student"
    }
    res1 = client.post("/users/register", json=payload)
    assert res1.status_code == 201

    duplicate_payload = {
        "name": "Second User",
        "email": "test@campus.edu",
        "phone_number": "555-000-2222",
        "password": "AnotherPassword456!",
        "role": "student"
    }
    res2 = client.post("/users/register", json=duplicate_payload)
    assert res2.status_code == 409
    detail = res2.json().get("detail", "")
    assert "already registered" in detail.lower() or "conflict" in detail.lower() or "exists" in detail.lower()


def test_register_missing_or_invalid_fields(client: TestClient):
    """
    4. test_register_missing_or_invalid_fields:
       - POST /users/register with missing email, missing name, or invalid email format.
       - Assert HTTP 422 Unprocessable Entity.
    """
    # Missing email
    res1 = client.post("/users/register", json={
        "name": "No Email",
        "phone_number": "555-111-2222",
        "password": "password"
    })
    assert res1.status_code == 422

    # Missing name
    res2 = client.post("/users/register", json={
        "email": "valid@campus.edu",
        "phone_number": "555-111-2222",
        "password": "password"
    })
    assert res2.status_code == 422

    # Invalid email format
    res3 = client.post("/users/register", json={
        "name": "Bad Email",
        "email": "not-a-valid-email",
        "phone_number": "555-111-2222",
        "password": "password"
    })
    assert res3.status_code == 422


def test_login_success(client: TestClient):
    """
    5. test_login_success:
       - POST /users/login with correct credentials.
       - Assert HTTP 200 OK; response contains an access token / token identifier and user details.
    """
    # First register user
    client.post("/users/register", json={
        "name": "Login Tester",
        "email": "tester@campus.edu",
        "phone_number": "555-333-4444",
        "password": "MySecretPassword123!",
        "role": "student"
    })

    # Perform login
    response = client.post("/users/login", json={
        "email": "tester@campus.edu",
        "password": "MySecretPassword123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "tester@campus.edu"
    assert data["user"]["name"] == "Login Tester"


def test_login_invalid_credentials_fails(client: TestClient):
    """
    6. test_login_invalid_credentials_fails:
       - POST /users/login with wrong password or nonexistent email.
       - Assert HTTP 401 Unauthorized with detail message.
    """
    # Register user
    client.post("/users/register", json={
        "name": "Cred Tester",
        "email": "cred@campus.edu",
        "phone_number": "555-555-5555",
        "password": "CorrectPassword123!",
        "role": "student"
    })

    # Wrong password
    res1 = client.post("/users/login", json={
        "email": "cred@campus.edu",
        "password": "WrongPassword!"
    })
    assert res1.status_code == 401
    assert "invalid" in res1.json().get("detail", "").lower() or "credentials" in res1.json().get("detail", "").lower()

    # Nonexistent email
    res2 = client.post("/users/login", json={
        "email": "doesnotexist@campus.edu",
        "password": "AnyPassword123!"
    })
    assert res2.status_code == 401


def test_get_current_user_profile(client: TestClient):
    """
    7. test_get_current_user_profile:
       - GET /users/me with valid Authorization header.
       - Assert HTTP 200 OK and matching profile fields.
    """
    # Register user
    client.post("/users/register", json={
        "name": "Profile User",
        "email": "profile@campus.edu",
        "phone_number": "555-777-8888",
        "password": "ProfilePassword123!",
        "role": "student"
    })

    # Login to obtain token
    login_res = client.post("/users/login", json={
        "email": "profile@campus.edu",
        "password": "ProfilePassword123!"
    })
    token = login_res.json()["access_token"]

    # Request /users/me
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@campus.edu"
    assert data["name"] == "Profile User"
    assert data["phone_number"] == "555-777-8888"
    assert data["role"] == "student"


def test_get_current_user_unauthenticated_fails(client: TestClient):
    """
    8. test_get_current_user_unauthenticated_fails:
       - GET /users/me without Authorization header.
       - Assert HTTP 401 Unauthorized.
    """
    response = client.get("/users/me")
    assert response.status_code == 401


def test_static_frontend_served(client: TestClient):
    """
    9. test_static_frontend_served:
       - GET / returns HTTP 200 with HTML content.
       - GET /app.js returns HTTP 200 with JavaScript content.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "Campus Lost & Found" in response.text
    assert "<form id=\"login-form\"" in response.text

    js_response = client.get("/app.js")
    assert js_response.status_code == 200
    assert "registerUser" in js_response.text


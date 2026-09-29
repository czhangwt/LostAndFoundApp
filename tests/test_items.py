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


@pytest.fixture
def student_token(client: TestClient) -> str:
    client.post("/users/register", json={
        "name": "Alice Student",
        "email": "alice@campus.edu",
        "phone_number": "555-111-2222",
        "password": "Password123!",
        "role": "student"
    })
    login_res = client.post("/users/login", json={
        "email": "alice@campus.edu",
        "password": "Password123!"
    })
    return login_res.json()["access_token"]


@pytest.fixture
def second_student_token(client: TestClient) -> str:
    client.post("/users/register", json={
        "name": "Bob Student",
        "email": "bob@campus.edu",
        "phone_number": "555-333-4444",
        "password": "Password123!",
        "role": "student"
    })
    login_res = client.post("/users/login", json={
        "email": "bob@campus.edu",
        "password": "Password123!"
    })
    return login_res.json()["access_token"]


def test_create_lost_item_success(client: TestClient, student_token: str):
    """
    1. test_create_lost_item_success:
       - POST /items/ as authenticated student with item_type="lost", title, description, and campus_location.
       - Assert HTTP 201 Created; response includes id, user_id, status="pending", is_resolved=False.
    """
    payload = {
        "title": "Blue North Face Backpack",
        "description": "Left on 2nd floor of the library near study carrels.",
        "item_type": "lost",
        "campus_location": "Campus Library"
    }
    response = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["item_type"] == "lost"
    assert data["campus_location"] == payload["campus_location"]
    assert data["status"] == "pending"
    assert data["is_resolved"] is False
    assert "user_id" in data
    assert "user" in data
    assert data["user"]["email"] == "alice@campus.edu"


def test_create_found_item_success(client: TestClient, student_token: str):
    """
    2. test_create_found_item_success:
       - POST /items/ as authenticated student with item_type="found".
       - Assert HTTP 201 Created and item_type="found".
    """
    payload = {
        "title": "Hydro Flask Water Bottle",
        "description": "Black 32oz bottle found on the bench outside student union.",
        "item_type": "found",
        "campus_location": "Student Union"
    }
    response = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["item_type"] == "found"
    assert data["status"] == "pending"
    assert data["is_resolved"] is False


def test_create_item_unauthenticated_fails(client: TestClient):
    """
    3. test_create_item_unauthenticated_fails:
       - POST /items/ without auth token.
       - Assert HTTP 401 Unauthorized.
    """
    payload = {
        "title": "Unauthenticated Item",
        "description": "This should fail because no token was passed.",
        "item_type": "lost",
        "campus_location": "Science Hall"
    }
    response = client.post("/items/", json=payload)
    assert response.status_code == 401


def test_create_item_invalid_type_fails(client: TestClient, student_token: str):
    """
    4. test_create_item_invalid_type_fails:
       - POST /items/ with item_type="stolen" or invalid string.
       - Assert HTTP 422 Unprocessable Entity.
    """
    payload = {
        "title": "Stolen Laptop",
        "description": "Invalid item type specified here.",
        "item_type": "stolen",
        "campus_location": "Computer Lab"
    }
    response = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json=payload
    )
    assert response.status_code == 422


def test_create_item_missing_required_fields(client: TestClient, student_token: str):
    """
    5. test_create_item_missing_required_fields:
       - POST /items/ with empty title or missing location.
       - Assert HTTP 422 Unprocessable Entity.
    """
    # Empty title (or shorter than min_length=3)
    res1 = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "",
            "description": "Valid description with sufficient length.",
            "item_type": "lost",
            "campus_location": "Dining Hall"
        }
    )
    assert res1.status_code == 422

    # Missing location
    res2 = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Missing Location Item",
            "description": "Valid description with sufficient length.",
            "item_type": "lost"
        }
    )
    assert res2.status_code == 422


def test_list_items(client: TestClient, student_token: str):
    """
    6. test_list_items:
       - GET /items/.
       - Assert HTTP 200 OK and response is a JSON list containing created items.
    """
    client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Lost Wallet",
            "description": "Brown leather wallet lost yesterday.",
            "item_type": "lost",
            "campus_location": "Gymnasium"
        }
    )
    client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Found Keychain",
            "description": "Car keys with red lanyard found on grass.",
            "item_type": "found",
            "campus_location": "Main Quad"
        }
    )

    response = client.get("/items/", headers={"Authorization": f"Bearer {student_token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    titles = [item["title"] for item in data]
    assert "Lost Wallet" in titles
    assert "Found Keychain" in titles


def test_get_single_item_detail(client: TestClient, student_token: str):
    """
    7. test_get_single_item_detail:
       - GET /items/{item_id} for an existing item.
       - Assert HTTP 200 OK with matching fields and author details.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Silver Scientific Calculator",
            "description": "TI-84 plus calculator left in Math Building 101.",
            "item_type": "lost",
            "campus_location": "Math Building"
        }
    )
    item_id = create_res.json()["id"]

    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["title"] == "Silver Scientific Calculator"
    assert data["campus_location"] == "Math Building"
    assert data["user"]["name"] == "Alice Student"
    assert data["user"]["email"] == "alice@campus.edu"


def test_get_nonexistent_item_returns_404(client: TestClient):
    """
    8. test_get_nonexistent_item_returns_404:
       - GET /items/99999.
       - Assert HTTP 404 Not Found.
    """
    response = client.get("/items/99999")
    assert response.status_code == 404


def test_update_own_item_success(client: TestClient, student_token: str):
    """
    9. test_update_own_item_success:
       - PUT /items/{item_id} by the original author updating title and description.
       - Assert HTTP 200 OK with updated attributes.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Original Backpack Title",
            "description": "Original description before update.",
            "item_type": "lost",
            "campus_location": "Campus Library"
        }
    )
    item_id = create_res.json()["id"]

    update_payload = {
        "title": "Updated Backpack Title",
        "description": "Updated description with more specific location details."
    }
    response = client.put(
        f"/items/{item_id}",
        headers={"Authorization": f"Bearer {student_token}"},
        json=update_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Backpack Title"
    assert data["description"] == "Updated description with more specific location details."
    assert data["campus_location"] == "Campus Library"


def test_update_other_user_item_forbidden(client: TestClient, student_token: str, second_student_token: str):
    """
    10. test_update_other_user_item_forbidden:
        - PUT /items/{item_id} with an auth token belonging to a different student.
        - Assert HTTP 403 Forbidden.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Alice's Item",
            "description": "Created by Alice.",
            "item_type": "lost",
            "campus_location": "Student Union"
        }
    )
    item_id = create_res.json()["id"]

    response = client.put(
        f"/items/{item_id}",
        headers={"Authorization": f"Bearer {second_student_token}"},
        json={"title": "Bob trying to hijack Alice's item"}
    )
    assert response.status_code == 403


def test_mark_item_resolved_success(client: TestClient, student_token: str):
    """
    11. test_mark_item_resolved_success:
        - PATCH /items/{item_id}/resolve by the author.
        - Assert HTTP 200 OK and is_resolved == True.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Item to be Resolved",
            "description": "Will be resolved soon.",
            "item_type": "lost",
            "campus_location": "Campus Library"
        }
    )
    item_id = create_res.json()["id"]
    assert create_res.json()["is_resolved"] is False

    response = client.patch(
        f"/items/{item_id}/resolve",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["is_resolved"] is True


def test_mark_other_user_item_resolved_forbidden(client: TestClient, student_token: str, second_student_token: str):
    """
    12. test_mark_other_user_item_resolved_forbidden:
        - PATCH /items/{item_id}/resolve by a non-owner user.
        - Assert HTTP 403 Forbidden.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Alice's Lost Watch",
            "description": "Expensive watch.",
            "item_type": "lost",
            "campus_location": "Gym"
        }
    )
    item_id = create_res.json()["id"]

    response = client.patch(
        f"/items/{item_id}/resolve",
        headers={"Authorization": f"Bearer {second_student_token}"}
    )
    assert response.status_code == 403

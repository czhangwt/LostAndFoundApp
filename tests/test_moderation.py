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


@pytest.fixture
def admin_token(client: TestClient) -> str:
    client.post("/users/register", json={
        "name": "Campus Admin",
        "email": "admin@campus.edu",
        "phone_number": "555-999-0000",
        "password": "AdminPassword123!",
        "role": "admin"
    })
    login_res = client.post("/users/login", json={
        "email": "admin@campus.edu",
        "password": "AdminPassword123!"
    })
    return login_res.json()["access_token"]


def test_student_access_moderation_queue_forbidden(client: TestClient, student_token: str):
    """
    1. test_student_access_moderation_queue_forbidden:
       - GET /moderation/pending using an auth token with role="student".
       - Assert HTTP 403 Forbidden.
    """
    response = client.get(
        "/moderation/pending",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 403


def test_admin_access_moderation_queue_success(client: TestClient, admin_token: str, student_token: str):
    """
    2. test_admin_access_moderation_queue_success:
       - GET /moderation/pending using an admin auth token.
       - Assert HTTP 200 OK and response contains a list of pending items.
    """
    # Create a pending item as student
    client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Lost Graphing Calculator",
            "description": "TI-84 plus CE in blue case left in math hall.",
            "item_type": "lost",
            "campus_location": "Math Building"
        }
    )

    response = client.get(
        "/moderation/pending",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "Lost Graphing Calculator"
    assert data[0]["status"] == "pending"


def test_admin_approve_item_creates_record(client: TestClient, admin_token: str, student_token: str):
    """
    3. test_admin_approve_item_creates_record:
       - POST /moderation/{item_id}/review with decision="approved", comments="Item meets guidelines".
       - Assert HTTP 201 (or 200); verify item's status changes to "approved" and returned record contains reviewed_at timestamp.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Found Car Keys",
            "description": "Honda keys with red lanyard found on library steps.",
            "item_type": "found",
            "campus_location": "Campus Library"
        }
    )
    item_id = create_res.json()["id"]

    review_res = client.post(
        f"/moderation/{item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "approved",
            "comments": "Item meets guidelines"
        }
    )
    assert review_res.status_code in [200, 201]
    record = review_res.json()
    assert record["decision"] == "approved"
    assert record["comments"] == "Item meets guidelines"
    assert record["item_id"] == item_id
    assert "reviewed_at" in record

    # Verify item status updated to approved
    item_res = client.get(f"/items/{item_id}")
    assert item_res.status_code == 200
    assert item_res.json()["status"] == "approved"


def test_admin_reject_item_without_comments_fails(client: TestClient, admin_token: str, student_token: str):
    """
    4. test_admin_reject_item_without_comments_fails:
       - POST /moderation/{item_id}/review with decision="rejected" and empty comments string.
       - Assert HTTP 422 Unprocessable Entity.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Suspicious Item",
            "description": "Left unattended for testing rejection comments validation.",
            "item_type": "lost",
            "campus_location": "Student Center"
        }
    )
    item_id = create_res.json()["id"]

    # Test with empty string
    review_res = client.post(
        f"/moderation/{item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "rejected",
            "comments": ""
        }
    )
    assert review_res.status_code == 422

    # Test with whitespace-only string
    review_res_whitespace = client.post(
        f"/moderation/{item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "rejected",
            "comments": "    "
        }
    )
    assert review_res_whitespace.status_code == 422


def test_admin_reject_item_creates_record(client: TestClient, admin_token: str, student_token: str):
    """
    5. test_admin_reject_item_creates_record:
       - POST /moderation/{item_id}/review with decision="rejected" and comments="Duplicate post".
       - Assert HTTP 200/201; verify item's status changes to "rejected".
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Duplicate Post",
            "description": "Already posted earlier today.",
            "item_type": "lost",
            "campus_location": "Dining Hall"
        }
    )
    item_id = create_res.json()["id"]

    review_res = client.post(
        f"/moderation/{item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "rejected",
            "comments": "Duplicate post"
        }
    )
    assert review_res.status_code in [200, 201]
    record = review_res.json()
    assert record["decision"] == "rejected"
    assert record["comments"] == "Duplicate post"
    assert record["item_id"] == item_id

    # Verify item status updated to rejected
    item_res = client.get(f"/items/{item_id}")
    assert item_res.status_code == 200
    assert item_res.json()["status"] == "rejected"


def test_invalid_decision_string_fails(client: TestClient, admin_token: str, student_token: str):
    """
    6. test_invalid_decision_string_fails:
       - POST /moderation/{item_id}/review with decision="maybe".
       - Assert HTTP 422 Unprocessable Entity.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Valid Item Details",
            "description": "Item description with sufficient text length.",
            "item_type": "lost",
            "campus_location": "Science Center"
        }
    )
    item_id = create_res.json()["id"]

    review_res = client.post(
        f"/moderation/{item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "maybe",
            "comments": "Not sure about this item"
        }
    )
    assert review_res.status_code == 422


def test_unapproved_item_hidden_from_public_feed(client: TestClient, student_token: str, admin_token: str):
    """
    7. test_unapproved_item_hidden_from_public_feed:
       - Student creates an item (defaults to status="pending").
       - Unauthenticated GET /items/.
       - Assert the pending item does NOT appear in the public list.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Secret Pending Item",
            "description": "This pending item should not be in public feed.",
            "item_type": "lost",
            "campus_location": "Dorm Hall"
        }
    )
    pending_item_id = create_res.json()["id"]

    # Public unauthenticated GET /items/
    public_res = client.get("/items/")
    assert public_res.status_code == 200
    public_items = public_res.json()
    item_ids = [item["id"] for item in public_items]
    assert pending_item_id not in item_ids

    # Now approve the item via admin review
    client.post(
        f"/moderation/{pending_item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "approved",
            "comments": "Approved for public viewing"
        }
    )

    # After approval, it should now appear on public feed
    approved_res = client.get("/items/")
    assert approved_res.status_code == 200
    approved_items = approved_res.json()
    approved_ids = [item["id"] for item in approved_items]
    assert pending_item_id in approved_ids


def test_author_can_view_own_pending_item(client: TestClient, student_token: str):
    """
    8. test_author_can_view_own_pending_item:
       - Student author requests GET /items/{item_id} for their own pending item.
       - Assert HTTP 200 OK (authors can inspect their pending posts).
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Alice's Pending Item",
            "description": "Alice should be able to view her own item details.",
            "item_type": "lost",
            "campus_location": "Music Building"
        }
    )
    item_id = create_res.json()["id"]

    response = client.get(
        f"/items/{item_id}",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["status"] == "pending"


def test_view_moderation_history(client: TestClient, admin_token: str, student_token: str):
    """
    9. test_view_moderation_history:
       - GET /moderation/{item_id}/history as admin.
       - Assert HTTP 200 OK and returns past review decisions with timestamps and comments.
    """
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "History Tracked Item",
            "description": "Item to test audit trail and moderation history.",
            "item_type": "found",
            "campus_location": "Athletics Field"
        }
    )
    item_id = create_res.json()["id"]

    # Submit first review: rejected
    client.post(
        f"/moderation/{item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "rejected",
            "comments": "Please add clearer description"
        }
    )

    # Submit second review: approved
    client.post(
        f"/moderation/{item_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "approved",
            "comments": "Updated description meets guidelines"
        }
    )

    history_res = client.get(
        f"/moderation/{item_id}/history",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert history_res.status_code == 200
    history = history_res.json()
    assert isinstance(history, list)
    assert len(history) == 2
    decisions = [h["decision"] for h in history]
    assert "rejected" in decisions
    assert "approved" in decisions
    assert all("reviewed_at" in h for h in history)
    assert all("comments" in h for h in history)
    assert all(h["item_id"] == item_id for h in history)

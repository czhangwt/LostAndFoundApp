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


def create_and_approve_item(
    client: TestClient,
    student_token: str,
    admin_token: str,
    title: str,
    description: str,
    item_type: str = "lost",
    campus_location: str = "Library"
) -> dict:
    create_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": title,
            "description": description,
            "item_type": item_type,
            "campus_location": campus_location
        }
    )
    assert create_res.status_code == 201
    item = create_res.json()
    review_res = client.post(
        f"/moderation/{item['id']}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"decision": "approved", "comments": "Approved for search test."}
    )
    assert review_res.status_code == 201
    return item


def test_search_keyword_matches_title(client: TestClient, student_token: str, admin_token: str):
    """
    1. test_search_keyword_matches_title:
       - Seed two approved items: "AirPods Pro in white case" and "Black leather wallet".
       - GET /items/search?q=AirPods.
       - Assert HTTP 200 OK and response list contains only the "AirPods" item.
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="AirPods Pro in white case",
        description="Left near the study tables on the 2nd floor.",
        item_type="lost",
        campus_location="Library"
    )
    create_and_approve_item(
        client, student_token, admin_token,
        title="Black leather wallet",
        description="Found on a bench outside.",
        item_type="found",
        campus_location="Student Center"
    )

    response = client.get("/items/search?q=AirPods")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert "AirPods" in results[0]["title"]


def test_search_keyword_matches_description(client: TestClient, student_token: str, admin_token: str):
    """
    2. test_search_keyword_matches_description:
       - Seed approved item with title "Calculus Textbook" and description "Contains handwritten notes in margin".
       - GET /items/search?q=handwritten.
       - Assert HTTP 200 OK and matching item is returned.
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="Calculus Textbook",
        description="Contains handwritten notes in margin.",
        item_type="found",
        campus_location="Engineering Hall"
    )

    response = client.get("/items/search?q=handwritten")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["title"] == "Calculus Textbook"
    assert "handwritten" in results[0]["description"]


def test_search_case_insensitive(client: TestClient, student_token: str, admin_token: str):
    """
    3. test_search_case_insensitive:
       - GET /items/search?q=airpods and /items/search?q=AIRPODS.
       - Assert both queries return identical matching items.
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="AirPods Pro in white case",
        description="Left near the study tables.",
        item_type="lost",
        campus_location="Library"
    )

    res_lower = client.get("/items/search?q=airpods")
    assert res_lower.status_code == 200
    data_lower = res_lower.json()

    res_upper = client.get("/items/search?q=AIRPODS")
    assert res_upper.status_code == 200
    data_upper = res_upper.json()

    assert len(data_lower) == 1
    assert len(data_upper) == 1
    assert data_lower == data_upper
    assert data_lower[0]["title"] == "AirPods Pro in white case"


def test_filter_by_item_type_lost(client: TestClient, student_token: str, admin_token: str):
    """
    4. test_filter_by_item_type_lost:
       - GET /items/search?item_type=lost.
       - Assert all returned items have item_type == "lost".
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="Hydro Flask Blue",
        description="Lost during lecture.",
        item_type="lost",
        campus_location="Science Hall"
    )
    create_and_approve_item(
        client, student_token, admin_token,
        title="Set of Keys",
        description="Found near bike rack.",
        item_type="found",
        campus_location="Gym / Recreation"
    )

    response = client.get("/items/search?item_type=lost")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert all(item["item_type"] == "lost" for item in results)
    assert any(item["title"] == "Hydro Flask Blue" for item in results)
    assert not any(item["title"] == "Set of Keys" for item in results)


def test_filter_by_item_type_found(client: TestClient, student_token: str, admin_token: str):
    """
    5. test_filter_by_item_type_found:
       - GET /items/search?item_type=found.
       - Assert all returned items have item_type == "found".
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="Hydro Flask Blue",
        description="Lost during lecture.",
        item_type="lost",
        campus_location="Science Hall"
    )
    create_and_approve_item(
        client, student_token, admin_token,
        title="Set of Keys",
        description="Found near bike rack.",
        item_type="found",
        campus_location="Gym / Recreation"
    )

    response = client.get("/items/search?item_type=found")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert all(item["item_type"] == "found" for item in results)
    assert any(item["title"] == "Set of Keys" for item in results)
    assert not any(item["title"] == "Hydro Flask Blue" for item in results)


def test_filter_by_campus_location(client: TestClient, student_token: str, admin_token: str):
    """
    6. test_filter_by_campus_location:
       - GET /items/search?location=Library.
       - Assert returned items match the "Library" campus location.
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="Graphing Notebook",
        description="Left on 3rd floor desk.",
        item_type="lost",
        campus_location="Library"
    )
    create_and_approve_item(
        client, student_token, admin_token,
        title="Umbrella",
        description="Found by dining entrance.",
        item_type="found",
        campus_location="Dining Commons"
    )

    response = client.get("/items/search?location=Library")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["campus_location"] == "Library"
    assert results[0]["title"] == "Graphing Notebook"


def test_combined_keyword_and_filters(client: TestClient, student_token: str, admin_token: str):
    """
    7. test_combined_keyword_and_filters:
       - GET /items/search?q=wallet&item_type=lost&location=Student+Center.
       - Assert returned items simultaneously satisfy all three conditions.
    """
    # Matches all 3 conditions: q=wallet, item_type=lost, location=Student Center
    create_and_approve_item(
        client, student_token, admin_token,
        title="Brown leather wallet",
        description="Lost with student ID card inside.",
        item_type="lost",
        campus_location="Student Center"
    )
    # Different type (found)
    create_and_approve_item(
        client, student_token, admin_token,
        title="Black wallet",
        description="Found near cash register.",
        item_type="found",
        campus_location="Student Center"
    )
    # Different location (Library)
    create_and_approve_item(
        client, student_token, admin_token,
        title="Lost travel wallet",
        description="Zipper wallet with receipts.",
        item_type="lost",
        campus_location="Library"
    )
    # Different keyword (Backpack)
    create_and_approve_item(
        client, student_token, admin_token,
        title="Blue Backpack",
        description="Left in cafeteria.",
        item_type="lost",
        campus_location="Student Center"
    )

    response = client.get("/items/search?q=wallet&item_type=lost&location=Student+Center")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    match = results[0]
    assert "wallet" in (match["title"] + match["description"]).lower()
    assert match["item_type"] == "lost"
    assert match["campus_location"] == "Student Center"
    assert match["title"] == "Brown leather wallet"


def test_search_excludes_pending_and_rejected_items(client: TestClient, student_token: str, admin_token: str):
    """
    8. test_search_excludes_pending_and_rejected_items:
       - Create item containing keyword "Umbrella" in pending status, and another "Umbrella" in rejected status.
       - GET /items/search?q=Umbrella.
       - Assert returned list is empty ([]).
    """
    # Create pending item (not reviewed)
    client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Red Umbrella",
            "description": "Left on bench.",
            "item_type": "lost",
            "campus_location": "Student Center"
        }
    )

    # Create another item and reject it
    rej_res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Black Umbrella",
            "description": "Found in rain.",
            "item_type": "found",
            "campus_location": "Engineering Hall"
        }
    )
    rejected_id = rej_res.json()["id"]
    client.post(
        f"/moderation/{rejected_id}/review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"decision": "rejected", "comments": "Duplicate umbrella post."}
    )

    response = client.get("/items/search?q=Umbrella")
    assert response.status_code == 200
    results = response.json()
    assert results == []


def test_search_empty_query_returns_all_approved(client: TestClient, student_token: str, admin_token: str):
    """
    9. test_search_empty_query_returns_all_approved:
       - GET /items/search.
       - Assert returns all approved items ordered newest to oldest.
    """
    item1 = create_and_approve_item(
        client, student_token, admin_token,
        title="First Item",
        description="First item description.",
        item_type="lost",
        campus_location="Library"
    )
    item2 = create_and_approve_item(
        client, student_token, admin_token,
        title="Second Item",
        description="Second item description.",
        item_type="found",
        campus_location="Gym / Recreation"
    )
    item3 = create_and_approve_item(
        client, student_token, admin_token,
        title="Third Item",
        description="Third item description.",
        item_type="lost",
        campus_location="Student Center"
    )

    response = client.get("/items/search")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 3
    # Ordered newest to oldest: item3, item2, item1
    result_ids = [item["id"] for item in results]
    assert result_ids == [item3["id"], item2["id"], item1["id"]]


def test_search_no_matches_returns_empty_list(client: TestClient, student_token: str, admin_token: str):
    """
    10. test_search_no_matches_returns_empty_list:
        - GET /items/search?q=NonExistentQueryString12345.
        - Assert HTTP 200 OK and response body is [].
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="Existing Laptop Charger",
        description="Found in room 101.",
        item_type="found",
        campus_location="Engineering Hall"
    )

    response = client.get("/items/search?q=NonExistentQueryString12345")
    assert response.status_code == 200
    assert response.json() == []


def test_search_special_characters_handled_safely(client: TestClient, student_token: str, admin_token: str):
    """
    11. test_search_special_characters_handled_safely:
        - GET /items/search?q=%27%20OR%201=1--%20%25_.
        - Assert HTTP 200 OK without SQL syntax or internal server errors.
    """
    create_and_approve_item(
        client, student_token, admin_token,
        title="Normal Item",
        description="Normal item description.",
        item_type="lost",
        campus_location="Library"
    )

    # %27%20OR%201=1--%20%25_ decodes to "' OR 1=1-- %_"
    response = client.get("/items/search?q=%27%20OR%201=1--%20%25_")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)

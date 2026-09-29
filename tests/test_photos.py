import io
import os
import shutil
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
    # Clean up any uploaded test files
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if f != ".gitkeep":
                try:
                    os.remove(os.path.join(upload_dir, f))
                except OSError:
                    pass


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


@pytest.fixture
def sample_item_id(client: TestClient, student_token: str) -> int:
    res = client.post(
        "/items/",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Lost Hydro Flask",
            "description": "Black 32oz water bottle with mountain stickers.",
            "item_type": "lost",
            "campus_location": "Student Recreation Center",
        }
    )
    return res.json()["id"]


# 1x1 transparent PNG bytes for testing
SAMPLE_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
    b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal JPEG header bytes for testing
SAMPLE_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f"
    b"\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


def test_upload_photo_with_caption_success(client: TestClient, student_token: str, sample_item_id: int):
    """
    1. test_upload_photo_with_caption_success:
       - POST /items/{item_id}/photos with valid image bytes (image/jpeg), a caption ("Corner scratch"), and owner's auth token.
       - Assert HTTP 201 Created; response includes id, image_url, caption, and timestamp.
    """
    files = {
        "file": ("test_image.jpg", SAMPLE_JPEG_BYTES, "image/jpeg")
    }
    data = {
        "caption": "Corner scratch"
    }

    response = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {student_token}"},
        files=files,
        data=data
    )

    assert response.status_code == 201
    photo = response.json()
    assert "id" in photo
    assert photo["caption"] == "Corner scratch"
    assert "image_url" in photo
    assert photo["image_url"].startswith("/uploads/")
    assert photo["image_url"].endswith(".jpg") or photo["image_url"].endswith(".jpeg")
    assert "created_at" in photo


def test_upload_multiple_photos_to_same_item(client: TestClient, student_token: str, sample_item_id: int):
    """
    2. test_upload_multiple_photos_to_same_item:
       - Upload two consecutive photos with distinct captions to the same item_id.
       - GET /items/{item_id}. Assert the returned item contains both photo objects in photos array.
    """
    # Upload photo 1
    res1 = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {student_token}"},
        files={"file": ("photo1.png", SAMPLE_PNG_BYTES, "image/png")},
        data={"caption": "Front view"}
    )
    assert res1.status_code == 201

    # Upload photo 2
    res2 = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {student_token}"},
        files={"file": ("photo2.jpg", SAMPLE_JPEG_BYTES, "image/jpeg")},
        data={"caption": "Back view showing sticker"}
    )
    assert res2.status_code == 201

    # GET /items/{item_id}
    item_res = client.get(f"/items/{sample_item_id}")
    assert item_res.status_code == 200
    item_data = item_res.json()
    assert "photos" in item_data
    assert len(item_data["photos"]) == 2

    captions = [p["caption"] for p in item_data["photos"]]
    assert "Front view" in captions
    assert "Back view showing sticker" in captions


def test_upload_photo_to_other_user_item_forbidden(client: TestClient, second_student_token: str, sample_item_id: int):
    """
    3. test_upload_photo_to_other_user_item_forbidden:
       - Attempt photo upload using an auth token for a student who does NOT own the post.
       - Assert HTTP 403 Forbidden.
    """
    files = {
        "file": ("test.png", SAMPLE_PNG_BYTES, "image/png")
    }
    response = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {second_student_token}"},
        files=files,
        data={"caption": "Trying to attach photo to someone else's item"}
    )
    assert response.status_code == 403


def test_upload_photo_to_nonexistent_item_not_found(client: TestClient, student_token: str):
    """
    4. test_upload_photo_to_nonexistent_item_not_found:
       - POST /items/99999/photos.
       - Assert HTTP 404 Not Found.
    """
    files = {
        "file": ("test.png", SAMPLE_PNG_BYTES, "image/png")
    }
    response = client.post(
        "/items/99999/photos",
        headers={"Authorization": f"Bearer {student_token}"},
        files=files,
        data={"caption": "Nonexistent item photo"}
    )
    assert response.status_code == 404


def test_upload_unsupported_file_format_fails(client: TestClient, student_token: str, sample_item_id: int):
    """
    5. test_upload_unsupported_file_format_fails:
       - Attempt upload with a .txt or .exe file (text/plain or application/octet-stream).
       - Assert HTTP 400 Bad Request with an unsupported media type message.
    """
    # Test .txt file
    txt_bytes = b"Hello, this is not an image file."
    files = {
        "file": ("notes.txt", txt_bytes, "text/plain")
    }
    response = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {student_token}"},
        files=files,
        data={"caption": "Text file upload"}
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower() or "image" in response.json()["detail"].lower()

    # Test .exe file
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {
        "file": ("program.exe", exe_bytes, "application/octet-stream")
    }
    response2 = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {student_token}"},
        files=files,
        data={"caption": "Executable file upload"}
    )
    assert response2.status_code == 400


def test_upload_oversized_file_fails(client: TestClient, student_token: str, sample_item_id: int):
    """
    6. test_upload_oversized_file_fails:
       - Attempt upload exceeding the 5 MB threshold.
       - Assert HTTP 400 Bad Request (or 413 Payload Too Large).
    """
    # 5 MB + 1 KB
    large_bytes = b"\x00" * (5 * 1024 * 1024 + 1024)
    files = {
        "file": ("huge_photo.jpg", large_bytes, "image/jpeg")
    }
    response = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {student_token}"},
        files=files,
        data={"caption": "Oversized photo"}
    )
    assert response.status_code in [400, 413]
    assert "size" in response.json()["detail"].lower() or "5" in response.json()["detail"].lower()


def test_upload_unauthenticated_fails(client: TestClient, sample_item_id: int):
    """
    7. test_upload_unauthenticated_fails:
       - POST /items/{item_id}/photos without auth token.
       - Assert HTTP 401 Unauthorized.
    """
    files = {
        "file": ("photo.jpg", SAMPLE_JPEG_BYTES, "image/jpeg")
    }
    response = client.post(
        f"/items/{sample_item_id}/photos",
        files=files,
        data={"caption": "No auth"}
    )
    assert response.status_code == 401


def test_upload_photo_by_admin_success(client: TestClient, admin_token: str, sample_item_id: int):
    """
    Extra: Administrator can upload photos to any item.
    """
    files = {
        "file": ("admin_upload.webp", SAMPLE_PNG_BYTES, "image/webp")
    }
    response = client.post(
        f"/items/{sample_item_id}/photos",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=files,
        data={"caption": "Admin verified photo"}
    )
    assert response.status_code == 201
    assert response.json()["caption"] == "Admin verified photo"

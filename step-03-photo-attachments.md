# Step 03: Photo Attachments for Posts

## 1. Session Scope
- **Target FR:** FR-3 (Photo Attachments)
- **Feature Boundaries:**
  - File upload endpoint accepting image attachments with user-defined captions for a specific item post.
  - Server-side file validation enforcing permitted MIME types (JPEG, PNG, WebP) and maximum file size (5 MB).
  - Secure storage of image assets in `static/uploads/` with UUID-based unique filenames to prevent path traversal or overwrites.
  - Database persistence of `Photo` records linked to `Item` via foreign key relationship.
  - Ownership enforcement: only the post author (or administrator) can upload photos to an item.
  - Frontend gallery component rendering thumbnails and captions on item cards.

---

## 2. Prerequisites
- `step-02-item-posting.md` completed and committed.
- `uv run pytest tests/test_items.py` passes 100%.
- Item creation, retrieval, and author identification fully functional.

---

## 3. TDD Test Suite: `tests/test_photos.py`
Create `tests/test_photos.py` testing single/multiple uploads, ownership protection, file-type filtering, and response payloads.

### Required Test Cases:
1. `test_upload_photo_with_caption_success`:
   - POST `/items/{item_id}/photos` with valid image bytes (`image/jpeg`), a caption (`"Corner scratch"`), and owner's auth token.
   - Assert HTTP 201 Created; response includes `id`, `image_url`, `caption`, and timestamp.
2. `test_upload_multiple_photos_to_same_item`:
   - Upload two consecutive photos with distinct captions to the same `item_id`.
   - GET `/items/{item_id}`. Assert the returned item contains both photo objects in `photos` array.
3. `test_upload_photo_to_other_user_item_forbidden`:
   - Attempt photo upload using an auth token for a student who does NOT own the post.
   - Assert HTTP 403 Forbidden.
4. `test_upload_photo_to_nonexistent_item_not_found`:
   - POST `/items/99999/photos`.
   - Assert HTTP 404 Not Found.
5. `test_upload_unsupported_file_format_fails`:
   - Attempt upload with a `.txt` or `.exe` file (`text/plain` or `application/octet-stream`).
   - Assert HTTP 400 Bad Request with an unsupported media type message.
6. `test_upload_oversized_file_fails`:
   - Attempt upload exceeding the 5 MB threshold.
   - Assert HTTP 400 Bad Request (or 413 Payload Too Large).
7. `test_upload_unauthenticated_fails`:
   - POST `/items/{item_id}/photos` without auth token.
   - Assert HTTP 401 Unauthorized.

---

## 4. Backend Implementation Deliverables
### 4.1 Data Models (`models.py`)
Add the `Photo` model and relationship to `Item`:
```python
# models.py additions
class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String, nullable=False)
    caption = Column(String(255), nullable=True, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    item = relationship("Item", back_populates="photos")
```
*(In `Item` model, add: `photos = relationship("Photo", back_populates="item", cascade="all, delete-orphan")`).*

### 4.2 Pydantic Schemas (`schemas.py`)
- `PhotoResponse`: `id: int`, `image_url: str`, `caption: Optional[str]`, `created_at: datetime`.
- Update `ItemResponse`: include `photos: list[PhotoResponse] = []`.

### 4.3 API Endpoint (`routers/items.py` or `routers/photos.py`)
- `POST /items/{item_id}/photos`:
  - Request format: `multipart/form-data` with `file: UploadFile = File(...)` and `caption: str = Form("")`.
  - Check item existence (raise 404 if missing).
  - Verify `item.user_id == current_user.id` or `current_user.role == 'admin'` (raise 403 if unauthorized).
  - Validate file extension (`.jpg`, `.jpeg`, `.png`, `.webp`) and MIME content-type.
  - Read bytes to check file size limit (<= 5 MB).
  - Generate a collision-resistant filename using `uuid.uuid4()`.
  - Save to disk under `static/uploads/{unique_name}`.
  - Persist `Photo` record with `image_url = f"/uploads/{unique_name}"`.
  - Return HTTP 201 with `PhotoResponse`.

### 4.4 App Entrypoint & Directory Config (`main.py`)
- Ensure directory `static/uploads` exists on app startup: `os.makedirs("static/uploads", exist_ok=True)`.
- Mount `static/uploads` to path `/uploads`: `app.mount("/uploads", StaticFiles(directory="static/uploads"), name="uploads")`.

---

## 5. Frontend Minimal UI (`static/`)
### 5.1 HTML Layout (`static/index.html`)
- On Item Cards (for authored posts) & inside the Create Item modal:
  - Add an "Add Photo" section with file input (`accept="image/png, image/jpeg, image/webp"`) and caption text field.
- In Item Card & Details Modal:
  - Photo Gallery Grid / Carousel:
    - Display responsive thumbnails (e.g. `h-40 w-full object-cover rounded-md mb-2`).
    - Render caption subtitle beneath each thumbnail (e.g. `<p class="text-xs text-gray-500 italic mt-1">${photo.caption}</p>`).
    - Clicking a thumbnail opens full-resolution modal preview.

### 5.2 JavaScript Fetch Logic (`static/app.js`)
- `async function uploadPhoto(itemId, fileInput, captionInput)`:
  - Build `FormData()` appending `file` and `caption`.
  - `fetch(`/items/${itemId}/photos`, { method: "POST", headers: { "Authorization": `Bearer ${token}` }, body: formData })`.
  - Handle success and refresh item display; handle error alerts if file is invalid or oversized.
- Update `renderItems()` to map through `item.photos` and generate HTML `<img>` tags and captions.

---

## 6. Definition of Done
1. **Automated Test Suite Pass:**
   ```bash
   uv run pytest tests/test_photos.py -v
   ```
   *Expected result: 7/7 tests pass with 0 errors.*
2. **Manual UI Verification:**
   - Launch server: `uv run fastapi dev`
   - Log in as the author of an item.
   - Choose a photo (JPG/PNG), enter caption `"Front view with stickers"`, and upload.
   - Confirm thumbnail and caption immediately appear on the item card.
   - Test validation: Attempt to upload a `.txt` file; observe an error toast/alert indicating invalid file format.

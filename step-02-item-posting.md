# Step 02: Item Posting & Lifecycle Management

## 1. Session Scope
- **Target FR:** FR-2 (Item Posting)
- **Feature Boundaries:**
  - Create item posts capturing `title`, `description`, `item_type` (`"lost"` or `"found"`), and `campus_location`.
  - Initialize item posts with default moderation status (`"pending"`) and resolution flag (`is_resolved = False`).
  - Edit existing item posts (title, description, campus location) with strict author ownership checks.
  - Mark an item post as resolved (`is_resolved = True`) restricted to the post author or an administrator.
  - Public retrieval of item listings and single item details.
  - Minimal frontend UI for reporting items, viewing item cards, and toggling resolved status.

---

## 2. Prerequisites
- `step-01-user-management.md` completed and committed.
- `uv run pytest tests/test_users.py` must pass with 0 errors.
- Active user authentication and `User` database model operational.

---

## 3. TDD Test Suite: `tests/test_items.py`
Create `tests/test_items.py` asserting post creation, retrieval, updates, resolution, and ownership enforcement.

### Required Test Cases:
1. `test_create_lost_item_success`:
   - POST `/items/` as authenticated student with `item_type="lost"`, `title`, `description`, and `campus_location`.
   - Assert HTTP 201 Created; response includes `id`, `user_id`, `status="pending"`, `is_resolved=False`.
2. `test_create_found_item_success`:
   - POST `/items/` as authenticated student with `item_type="found"`.
   - Assert HTTP 201 Created and `item_type="found"`.
3. `test_create_item_unauthenticated_fails`:
   - POST `/items/` without auth token.
   - Assert HTTP 401 Unauthorized.
4. `test_create_item_invalid_type_fails`:
   - POST `/items/` with `item_type="stolen"` or invalid string.
   - Assert HTTP 422 Unprocessable Entity.
5. `test_create_item_missing_required_fields`:
   - POST `/items/` with empty title or missing location.
   - Assert HTTP 422 Unprocessable Entity.
6. `test_list_items`:
   - GET `/items/`.
   - Assert HTTP 200 OK and response is a JSON list containing created items.
7. `test_get_single_item_detail`:
   - GET `/items/{item_id}` for an existing item.
   - Assert HTTP 200 OK with matching fields and author details.
8. `test_get_nonexistent_item_returns_404`:
   - GET `/items/99999`.
   - Assert HTTP 404 Not Found.
9. `test_update_own_item_success`:
   - PUT `/items/{item_id}` by the original author updating `title` and `description`.
   - Assert HTTP 200 OK with updated attributes.
10. `test_update_other_user_item_forbidden`:
    - PUT `/items/{item_id}` with an auth token belonging to a *different* student.
    - Assert HTTP 403 Forbidden.
11. `test_mark_item_resolved_success`:
    - PATCH `/items/{item_id}/resolve` by the author.
    - Assert HTTP 200 OK and `is_resolved == True`.
12. `test_mark_other_user_item_resolved_forbidden`:
    - PATCH `/items/{item_id}/resolve` by a non-owner user.
    - Assert HTTP 403 Forbidden.

---

## 4. Backend Implementation Deliverables
### 4.1 Data Models (`models.py`)
Add the `Item` model linked to `users`:
```python
# models.py additions
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    item_type = Column(String, nullable=False) # 'lost' or 'found'
    campus_location = Column(String, nullable=False, index=True)
    status = Column(String, default="pending", nullable=False) # 'pending', 'approved', 'rejected'
    is_resolved = Column(Boolean, default=False, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="items")
```
*(Ensure `items = relationship("Item", back_populates="user")` is added to `User`).*

### 4.2 Pydantic Schemas (`schemas.py`)
- `ItemBase`: `title: str`, `description: str`, `item_type: Literal['lost', 'found']`, `campus_location: str`.
- `ItemCreate(ItemBase)`: inherited fields with validation constraints (`min_length=3`).
- `ItemUpdate`: `title: Optional[str] = None`, `description: Optional[str] = None`, `campus_location: Optional[str] = None`.
- `ItemResponse(ItemBase)`: `id: int`, `status: str`, `is_resolved: bool`, `user_id: int`, `created_at: datetime`, `user: UserResponse`.

### 4.3 API Router (`routers/items.py`)
- `POST /items/`: Authenticate user via token dependency; create item with `status="pending"` and `is_resolved=False`. Return 201.
- `GET /items/`: Query database for items; return list of `ItemResponse`.
- `GET /items/{item_id}`: Query item by ID; raise 404 if not found. Return `ItemResponse`.
- `PUT /items/{item_id}`: Authenticate user; verify `item.user_id == current_user.id` or `current_user.role == 'admin'` (raise 403 if unauthorized); update fields; return updated `ItemResponse`.
- `PATCH /items/{item_id}/resolve`: Authenticate user; verify ownership (raise 403 if unauthorized); set `item.is_resolved = True`; return updated `ItemResponse`.

### 4.4 App Entrypoint (`main.py`)
- Import and register `items.router`: `app.include_router(items.router, prefix="/items", tags=["items"])`.

---

## 5. Frontend Minimal UI (`static/`)
### 5.1 HTML Layout (`static/index.html`)
- Add a prominent action button: "+ Report Lost or Found Item" (visible when logged in).
- **Create Item Modal / Form:**
  - Item Type selector (Radio / Toggle: "Lost Item" vs "Found Item").
  - Title input (`e.g. Blue North Face Backpack`).
  - Campus Location input (`e.g. Campus Library, 2nd Floor`).
  - Description textarea (`e.g. Left near study carrel 14 around 3 PM...`).
  - Submit button with loading feedback.
- **Main Feed Grid:**
  - Container for dynamic item cards.
  - Card layout displaying:
    - Item Type pill: Red badge for "LOST", Green badge for "FOUND".
    - Title & Campus Location.
    - Description preview.
    - Author name and posting date.
    - Resolution indicator: "Resolved" badge if `is_resolved` is true.
    - Action buttons: "Mark as Resolved" and "Edit" (only rendered on cards authored by the logged-in user).

### 5.2 JavaScript Fetch Logic (`static/app.js`)
- `async function fetchItems()`: GET `/items/`, loop through items, render cards into `#items-feed`.
- `async function createItem(itemData)`: POST to `/items/` with Bearer token. On success, hide modal and refresh items feed.
- `async function markResolved(itemId)`: PATCH to `/items/${itemId}/resolve` with Bearer token; refresh feed.

---

## 6. Definition of Done
1. **Automated Test Suite Pass:**
   ```bash
   uv run pytest tests/test_items.py -v
   ```
   *Expected result: 12/12 tests pass with 0 errors.*
2. **Manual UI Verification:**
   - Launch server: `uv run fastapi dev`
   - Log in as a registered student.
   - Click "Report Lost or Found Item", fill out form for a lost item, and submit.
   - Verify the card immediately appears in the feed with a "LOST" badge and your name.
   - Click "Mark as Resolved" and confirm the card changes to indicate "Resolved".
   - Open a private/incognito window, inspect the post, and verify that the "Mark as Resolved" button is not accessible.

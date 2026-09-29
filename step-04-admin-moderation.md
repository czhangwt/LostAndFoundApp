# Step 04: Admin Moderation System & Records

## 1. Session Scope
- **Target FR:** FR-4 (Moderation Records)
- **Feature Boundaries:**
  - Dedicated admin queue retrieving all pending item posts requiring review.
  - Moderation review endpoint allowing administrators to approve or reject a post, logging `decision`, `review comments`, and automatic server `review timestamp`.
  - Database persistence of `ModerationRecord` entities establishing a permanent audit trail.
  - Strict role-based access control restricting moderation views and review submissions to `role == "admin"`.
  - Public feed isolation: unapproved (`"pending"` or `"rejected"`) items are hidden from public listing, remaining accessible only to their author and administrators.
  - Frontend admin dashboard for reviewing pending submissions with approval and rejection actions.

---

## 2. Prerequisites
- `step-01-user-management.md`, `step-02-item-posting.md`, and `step-03-photo-attachments.md` completed and committed.
- All previous tests (`tests/test_users.py`, `tests/test_items.py`, `tests/test_photos.py`) passing with 0 errors.

---

## 3. TDD Test Suite: `tests/test_moderation.py`
Create `tests/test_moderation.py` testing moderation authorization, approval/rejection workflows, comment validation, and public feed filtering.

### Required Test Cases:
1. `test_student_access_moderation_queue_forbidden`:
   - GET `/moderation/pending` using an auth token with `role="student"`.
   - Assert HTTP 403 Forbidden.
2. `test_admin_access_moderation_queue_success`:
   - GET `/moderation/pending` using an admin auth token.
   - Assert HTTP 200 OK and response contains a list of pending items.
3. `test_admin_approve_item_creates_record`:
   - POST `/moderation/{item_id}/review` with `decision="approved"`, `comments="Item meets guidelines"`.
   - Assert HTTP 201 (or 200); verify item's `status` changes to `"approved"` and returned record contains `reviewed_at` timestamp.
4. `test_admin_reject_item_without_comments_fails`:
   - POST `/moderation/{item_id}/review` with `decision="rejected"` and empty comments string.
   - Assert HTTP 422 Unprocessable Entity.
5. `test_admin_reject_item_creates_record`:
   - POST `/moderation/{item_id}/review` with `decision="rejected"` and `comments="Duplicate post"`.
   - Assert HTTP 200/201; verify item's `status` changes to `"rejected"`.
6. `test_invalid_decision_string_fails`:
   - POST `/moderation/{item_id}/review` with `decision="maybe"`.
   - Assert HTTP 422 Unprocessable Entity.
7. `test_unapproved_item_hidden_from_public_feed`:
   - Student creates an item (defaults to `status="pending"`).
   - Unauthenticated GET `/items/`.
   - Assert the pending item does NOT appear in the public list.
8. `test_author_can_view_own_pending_item`:
   - Student author requests GET `/items/{item_id}` for their own pending item.
   - Assert HTTP 200 OK (authors can inspect their pending posts).
9. `test_view_moderation_history`:
   - GET `/moderation/{item_id}/history` as admin.
   - Assert HTTP 200 OK and returns past review decisions with timestamps and comments.

---

## 4. Backend Implementation Deliverables
### 4.1 Data Models (`models.py`)
Add the `ModerationRecord` model:
```python
# models.py additions
class ModerationRecord(Base):
    __tablename__ = "moderation_records"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False) # 'approved' or 'rejected'
    comments = Column(Text, nullable=False)
    reviewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    item = relationship("Item", back_populates="moderation_records")
    admin = relationship("User")
```
*(In `Item` model, add: `moderation_records = relationship("ModerationRecord", back_populates="item", cascade="all, delete-orphan")`).*

### 4.2 Pydantic Schemas (`schemas.py`)
- `ModerationReviewRequest`:
  - `decision: Literal["approved", "rejected"]`
  - `comments: str` (with validator ensuring non-empty when `decision == "rejected"`).
- `ModerationRecordResponse`:
  - `id: int`, `item_id: int`, `admin_id: int`, `decision: str`, `comments: str`, `reviewed_at: datetime`.

### 4.3 API Router (`routers/moderation.py`)
- Admin verification dependency: helper `require_admin(current_user: User)` checking `current_user.role == 'admin'`, raising 403 if false.
- `GET /moderation/pending`:
  - Query items where `Item.status == 'pending'`.
  - Return `list[ItemResponse]`.
- `POST /moderation/{item_id}/review`:
  - Find item by `item_id` (raise 404 if not found).
  - Update `item.status = request.decision`.
  - Create and save `ModerationRecord(item_id=item.id, admin_id=current_user.id, decision=request.decision, comments=request.comments, reviewed_at=datetime.utcnow())`.
  - Return `ModerationRecordResponse`.
- `GET /moderation/{item_id}/history`:
  - Allow admin or the item's author.
  - Return `list[ModerationRecordResponse]`.

### 4.4 Feed Visibility Update (`routers/items.py`)
- Update `GET /items/`:
  - When called publicly without user session, filter query: `query.filter(Item.status == 'approved')`.
  - If authenticated user supplies query parameter `include_pending=true` or requests their own posts, show only authorized records.

### 4.5 App Entrypoint (`main.py`)
- Register `moderation.router`: `app.include_router(moderation.router, prefix="/moderation", tags=["moderation"])`.

---

## 5. Frontend Minimal UI (`static/`)
### 5.1 HTML Layout (`static/index.html`)
- Top Navigation: Add "Moderation Dashboard" tab/button, visible only when logged in as an `admin`.
- **Moderation Panel (`#moderation-view`):**
  - Section title: "Pending Post Approvals".
  - Empty queue notification: `"All posts have been reviewed."`
  - Pending cards displaying:
    - Post title, campus location, item type tag, author name, timestamp.
    - Attached photos preview with captions.
    - Action Bar:
      - Quick "Approve" button (green).
      - "Reject" button (red), which prompts a modal with required textarea for rejection comments.
- **Author View Indicator:** On user's own item cards, display a badge indicating moderation status:
  - Yellow badge: `Pending Admin Review`.
  - Red badge: `Rejected - View Comments`.
  - Green badge: `Approved`.

### 5.2 JavaScript Fetch Logic (`static/app.js`)
- `async function loadModerationQueue()`: GET `/moderation/pending` with admin Bearer token.
- `async function reviewItem(itemId, decision, comments)`:
  - POST to `/moderation/${itemId}/review` with JSON payload `{ decision, comments }`.
  - Animate item card removal from queue and show confirmation alert.
- Update `checkSession()` to reveal the Moderation tab if `currentUser.role === 'admin'`.

---

## 6. Definition of Done
1. **Automated Test Suite Pass:**
   ```bash
   uv run pytest tests/test_moderation.py -v
   ```
   *Expected result: 9/9 tests pass with 0 errors.*
2. **Manual UI Verification:**
   - Launch server: `uv run fastapi dev`
   - Log in as a student user, create a new item post ("Lost Watch - Gym").
   - Switch to public view (or log out) and confirm "Lost Watch - Gym" is **not visible** on the main feed.
   - Log in as an administrator account. Open "Moderation Dashboard".
   - Confirm "Lost Watch - Gym" appears in the pending queue.
   - Click "Approve" with comment "Post meets policy".
   - Return to main public feed; verify that "Lost Watch - Gym" is now visible to all users.

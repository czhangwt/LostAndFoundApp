# Step 05: Dedicated Search & Multi-Filter Engine

## 1. Session Scope
- **Target FR:** FR-5 (Search and Filtering)
- **Feature Boundaries:**
  - Dedicated search and filter endpoint supporting keyword matching across post title and description.
  - Multi-attribute filtering by `item_type` (`"lost"` or `"found"`), `campus_location`, and resolution status (`is_resolved`).
  - Strict enforcement of moderation boundary: search queries only return admin-approved (`status == "approved"`) posts.
  - Case-insensitive search and safe escaping of special characters.
  - Graceful handling of empty queries and empty result sets.
  - Frontend interactive search toolbar with instant or debounced filtering and responsive empty states.

---

## 2. Prerequisites
- `step-01-user-management.md` through `step-04-admin-moderation.md` completed and committed.
- All test suites (`tests/test_users.py`, `tests/test_items.py`, `tests/test_photos.py`, `tests/test_moderation.py`) passing with 0 errors.

---

## 3. TDD Test Suite: `tests/test_search.py`
Create `tests/test_search.py` evaluating keyword matching, filter combinations, moderation isolation, and input safety.

### Required Test Cases:
1. `test_search_keyword_matches_title`:
   - Seed two approved items: "AirPods Pro in white case" and "Black leather wallet".
   - GET `/items/search?q=AirPods`.
   - Assert HTTP 200 OK and response list contains only the "AirPods" item.
2. `test_search_keyword_matches_description`:
   - Seed approved item with title "Calculus Textbook" and description "Contains handwritten notes in margin".
   - GET `/items/search?q=handwritten`.
   - Assert HTTP 200 OK and matching item is returned.
3. `test_search_case_insensitive`:
   - GET `/items/search?q=airpods` and `/items/search?q=AIRPODS`.
   - Assert both queries return identical matching items.
4. `test_filter_by_item_type_lost`:
   - GET `/items/search?item_type=lost`.
   - Assert all returned items have `item_type == "lost"`.
5. `test_filter_by_item_type_found`:
   - GET `/items/search?item_type=found`.
   - Assert all returned items have `item_type == "found"`.
6. `test_filter_by_campus_location`:
   - GET `/items/search?location=Library`.
   - Assert returned items match the "Library" campus location.
7. `test_combined_keyword_and_filters`:
   - GET `/items/search?q=wallet&item_type=lost&location=Student+Center`.
   - Assert returned items simultaneously satisfy all three conditions.
8. `test_search_excludes_pending_and_rejected_items`:
   - Create item containing keyword "Umbrella" in `pending` status, and another "Umbrella" in `rejected` status.
   - GET `/items/search?q=Umbrella`.
   - Assert returned list is empty (`[]`).
9. `test_search_empty_query_returns_all_approved`:
   - GET `/items/search`.
   - Assert returns all approved items ordered newest to oldest.
10. `test_search_no_matches_returns_empty_list`:
    - GET `/items/search?q=NonExistentQueryString12345`.
    - Assert HTTP 200 OK and response body is `[]`.
11. `test_search_special_characters_handled_safely`:
    - GET `/items/search?q=%27%20OR%201=1--%20%25_`.
    - Assert HTTP 200 OK without SQL syntax or internal server errors.

---

## 4. Backend Implementation Deliverables
### 4.1 Search API Endpoint (`routers/items.py`)
Add the dedicated search endpoint:
```python
@router.get("/search", response_model=list[schemas.ItemResponse])
def search_items(
    q: Optional[str] = Query(None, description="Keyword search in title and description"),
    item_type: Optional[str] = Query(None, description="Filter by lost or found"),
    location: Optional[str] = Query(None, description="Filter by campus location"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Item).filter(models.Item.status == "approved")

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                models.Item.title.ilike(search_term),
                models.Item.description.ilike(search_term)
            )
        )

    if item_type and item_type.lower() in ["lost", "found"]:
        query = query.filter(models.Item.item_type == item_type.lower())

    if location and location.strip():
        query = query.filter(models.Item.campus_location.ilike(f"%{location.strip()}%"))

    if is_resolved is not None:
        query = query.filter(models.Item.is_resolved == is_resolved)
    else:
        # Default behavior: show unresolved items first or all active items
        pass

    return query.order_by(models.Item.created_at.desc()).all()
```

### 4.2 Query Sanitization & Indexing (`models.py`)
- Verify that `Item.title`, `Item.campus_location`, and `Item.status` have database indices (`index=True`) to maintain query efficiency.

---

## 5. Frontend Minimal UI (`static/`)
### 5.1 HTML Layout (`static/index.html`)
- Position a Search & Filter Toolbar directly above the Item Feed:
  - **Search Input:** `<input id="search-keyword" type="text" placeholder="Search by keyword (title, description)..." class="..."/>`
  - **Item Type Selector:**
    ```html
    <select id="filter-type" class="...">
      <option value="">All Types</option>
      <option value="lost">Lost Items</option>
      <option value="found">Found Items</option>
    </select>
    ```
  - **Campus Location Filter:**
    ```html
    <select id="filter-location" class="...">
      <option value="">All Locations</option>
      <option value="Library">Library</option>
      <option value="Student Center">Student Center</option>
      <option value="Engineering Hall">Engineering Hall</option>
      <option value="Dining Commons">Dining Commons</option>
      <option value="Gym / Recreation">Gym / Recreation</option>
    </select>
    ```
  - **Resolution Toggle:**
    ```html
    <label class="flex items-center space-x-2 text-sm text-gray-700">
      <input type="checkbox" id="filter-include-resolved" class="rounded">
      <span>Include Resolved</span>
    </label>
    ```
  - **Reset Button:** `<button id="btn-reset-filters" class="...">Clear Filters</button>`
- **Empty State Container (`#empty-state`):**
  - Displays when 0 items match:
    ```html
    <div id="empty-state" class="hidden text-center py-12">
      <p class="text-xl font-medium text-gray-600">No items match your search criteria.</p>
      <p class="text-sm text-gray-400 mt-1">Try adjusting your keywords or clearing selected filters.</p>
    </div>
    ```

### 5.2 JavaScript Fetch Logic (`static/app.js`)
- `async function executeSearch()`:
  - Gather values: `q`, `item_type`, `location`, and `include_resolved`.
  - Build `URLSearchParams`:
    ```javascript
    const params = new URLSearchParams();
    if (keyword) params.append("q", keyword);
    if (type) params.append("item_type", type);
    if (location) params.append("location", location);
    if (!includeResolved) params.append("is_resolved", "false");
    ```
  - Call `fetch('/items/search?' + params.toString())`.
  - If results length is 0, display `#empty-state` and clear items feed; otherwise, hide `#empty-state` and invoke `renderItems(results)`.
- Attach input debounce listener (`300ms`) on `#search-keyword` and immediate `change` listeners on filter dropdowns.
- Bind `btn-reset-filters` to clear form values and re-run search.

---

## 6. Definition of Done
1. **Automated Test Suite Pass:**
   ```bash
   uv run pytest tests/test_search.py -v
   ```
   *Expected result: 11/11 tests pass with 0 errors.*
2. **Full Project Test Suite Pass:**
   ```bash
   uv run pytest -v
   ```
   *Expected result: All tests across `tests/test_users.py`, `tests/test_items.py`, `tests/test_photos.py`, `tests/test_moderation.py`, and `tests/test_search.py` pass cleanly (100% green).*
3. **Manual UI Verification:**
   - Launch server: `uv run fastapi dev`
   - Open `http://127.0.0.1:8000`.
   - Search for a keyword from an approved post; verify matching item immediately renders.
   - Filter by `Item Type = "Found"`; verify that lost items disappear.
   - Filter by a campus location with no matches; observe the clean `#empty-state` message.
   - Click "Clear Filters" and verify that all approved items reload into the feed.

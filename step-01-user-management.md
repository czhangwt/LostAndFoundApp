# Step 01: Project Setup, Database Foundation & User Management

## 1. Session Scope
- **Target FR:** FR-1 (User Management)
- **Feature Boundaries:**
  - Initialize project dependencies using `uv` (`fastapi`, `uvicorn`, `sqlalchemy`, `pytest`, `httpx`, `pydantic`, `pwdlib` / `passlib`).
  - Configure the SQLite database engine (`lost_and_found.db`) and SQLAlchemy session dependency.
  - Implement student and administrator registration with name, email address, phone number, password, and role.
  - Implement login authentication returning an auth token or session identifier.
  - Implement the current-user profile endpoint (`GET /users/me`).
  - Deliver minimal frontend authentication UI in vanilla HTML/JS with Tailwind CSS CDN.

---

## 2. Prerequisites
- Python 3.10+ and `uv` package manager installed.
- Clean working directory with `AGENTS.md` and `FRs.md`.
- No prior database files required (database tables will be auto-created on startup or test run).

---

## 3. TDD Test Suite: `tests/test_users.py`
Create `tests/test_users.py` using `pytest` and FastAPI's `TestClient` (from `httpx`). Implement tests asserting expected status codes and validation behaviors before writing router logic.

### Required Test Cases:
1. `test_register_student_success`:
   - POST `/users/register` with valid `name`, `email`, `phone_number`, `password`, and `role="student"`.
   - Assert HTTP 201 Created; response contains user ID, name, email, phone number, role, but NO password.
2. `test_register_admin_success`:
   - POST `/users/register` with `role="admin"` (plus admin invite code if implemented).
   - Assert HTTP 201 Created and response reflects `role="admin"`.
3. `test_register_duplicate_email_conflict`:
   - Register a user with email `test@campus.edu`. Attempt registering again with same email.
   - Assert HTTP 409 Conflict (or HTTP 400 Bad Request) with informative error detail.
4. `test_register_missing_or_invalid_fields`:
   - POST `/users/register` with missing email, missing name, or invalid email format.
   - Assert HTTP 422 Unprocessable Entity.
5. `test_login_success`:
   - POST `/users/login` with correct credentials.
   - Assert HTTP 200 OK; response contains an access token / token identifier and user details.
6. `test_login_invalid_credentials_fails`:
   - POST `/users/login` with wrong password or nonexistent email.
   - Assert HTTP 401 Unauthorized with detail message.
7. `test_get_current_user_profile`:
   - GET `/users/me` with valid Authorization header.
   - Assert HTTP 200 OK and matching profile fields.
8. `test_get_current_user_unauthenticated_fails`:
   - GET `/users/me` without Authorization header.
   - Assert HTTP 401 Unauthorized.

---

## 4. Backend Implementation Deliverables
### 4.1 Dependency Setup
Run:
```bash
uv init --no-readme
uv add fastapi uvicorn sqlalchemy pydantic passlib bcrypt python-multipart httpx pytest
```

### 4.2 Database Configuration (`database.py`)
- Setup SQLite engine: `sqlite:///./lost_and_found.db` (`connect_args={"check_same_thread": False}`).
- Define `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`.
- Define declarative `Base = declarative_base()`.
- Provide `get_db()` generator dependency yielding a session and closing it on teardown.

### 4.3 Data Models (`models.py`)
- `User` table (`users`):
  - `id`: Integer, primary key, indexed.
  - `name`: String, non-nullable.
  - `email`: String, unique, indexed, non-nullable.
  - `phone_number`: String, non-nullable.
  - `password_hash`: String, non-nullable.
  - `role`: String, non-nullable, default `"student"` (`"student"` or `"admin"`).
  - `created_at`: DateTime, default `datetime.utcnow`.

### 4.4 Pydantic Schemas (`schemas.py`)
- `UserCreate`: `name: str`, `email: EmailStr`, `phone_number: str`, `password: str`, `role: str = "student"`.
- `UserLogin`: `email: EmailStr`, `password: str`.
- `UserResponse`: `id: int`, `name: str`, `email: EmailStr`, `phone_number: str`, `role: str`, `created_at: datetime`.
- `TokenResponse`: `access_token: str`, `token_type: str`, `user: UserResponse`.

### 4.5 API Router (`routers/users.py`)
- `POST /users/register`: Validate uniqueness, hash password, insert user record, return 201 with `UserResponse`.
- `POST /users/login`: Authenticate email & password, generate token, return `TokenResponse`.
- `GET /users/me`: Dependency-injected endpoint validating Authorization header and returning current `UserResponse`.

### 4.6 App Entrypoint (`main.py`)
- Instantiate `FastAPI(title="Campus Lost and Found")`.
- Initialize database tables: `Base.metadata.create_all(bind=engine)`.
- Mount `routers/users.py`.
- Mount `static/` directory to serve frontend assets (`app.mount("/", StaticFiles(directory="static", html=True), name="static")`).

---

## 5. Frontend Minimal UI (`static/`)
### 5.1 HTML Layout (`static/index.html`)
- Import Tailwind CSS via CDN: `<script src="https://cdn.tailwindcss.com"></script>`.
- Top Navigation Bar:
  - Brand header: "Campus Lost & Found".
  - Logged-out state: "Register" and "Login" buttons.
  - Logged-in state: Display user name, role badge (`student` or `admin`), and "Logout" button.
- Modal / Card components for:
  - **Register Form:** Fields for Name, University Email, Phone Number, Password, Role selector (`student` / `admin`).
  - **Login Form:** Fields for Email and Password.
  - Status/Feedback banner for alerts and error notifications.

### 5.2 JavaScript Fetch Logic (`static/app.js`)
- Store auth token and user state in `localStorage`.
- `async function registerUser(formData)`: POST to `/users/register`.
- `async function loginUser(email, password)`: POST to `/users/login`, persist token, call `updateAuthUI()`.
- `function logoutUser()`: Clear `localStorage`, refresh auth UI.
- `async function checkSession()`: GET `/users/me` with Bearer token on page load to verify validity and populate UI.

---

## 6. Definition of Done
1. **Automated Test Suite Pass:**
   ```bash
   uv run pytest tests/test_users.py -v
   ```
   *Expected result: 8/8 tests pass with 0 errors.*
2. **Manual UI Verification:**
   - Launch server: `uv run fastapi dev`
   - Open browser at `http://127.0.0.1:8000`.
   - Register a new student account (`teststudent@campus.edu`, name, phone, password).
   - Log in and verify that the user's name and role badge appear in the top navigation bar.
   - Click "Logout" and confirm the UI returns to the logged-out state.

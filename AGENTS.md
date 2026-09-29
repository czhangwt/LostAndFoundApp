## 1. Project Overview
The Campus Lost & Found App is an educational, lightweight web application for students to report and search for lost items, and for administrators to review posts.
Functional requirements are defined in file `@FRs.md`.
## 2. Tech Stack & Commands
Keep the codebase simple, approachable, and easy for students to read.
- **Backend:** FastAPI (Python 3.10+)
- **Database:** SQLite via SQLAlchemy ORM (single file: `lost_and_found.db`)
- **Frontend:** Vanilla HTML, modern JavaScript (`fetch`), and Tailwind CSS via CDN.
- **Package Manager:** `uv`
  - Add package: `uv add <package>`
  - Run server: `uv run fastapi dev`
  - Run tests: `uv run pytest`
## 3. Project Structure
Keep the file tree flat and readable:
LostAndFoundApp/
  ├── main.py              # FastAPI app initialization & routes inclusion
  ├── database.py          # SQLite engine & session setup
  ├── models.py            # SQLAlchemy database models
  ├── schemas.py           # Pydantic request/response schemas
  ├── routers/             # API Endpoint modules (users, items, moderation)
  └── static/              # Vanilla HTML, JS, CSS frontend assets
  └── tests/               # Simple pytest files (test_items.py, test_users.py)
## 4. Architectural & Coding Guidelines
1. RESTful Principles: Ensure explicit HTTP methods (GET, POST, PUT, DELETE) and standard HTTP status codes.
2. Keep data models, request validation (Pydantic), business logic, and API routes cleanly separated.
3. Do not install Node.js, npm, webpack, or frontend build pipelines. All frontend scripts must run natively in the browser.
## 5. Implementation Strategy (Step-by-Step Test-Driven Development)
Work incrementally, feature by feature, following strict Test-Driven Development:
1. Write endpoint and unit tests in `tests/` asserting expected behavior, input validation, and HTTP response codes.
2. Run `uv run pytest` to confirm tests fail as expected.
3. Implement the minimal backend schemas, models, and router logic required to pass the tests.
4. Verify all tests pass (`uv run pytest` returns exit code 0).
5. Implement the corresponding frontend UI components in `static/` and wire up API integrations.
## 6. Git Commit Directives
After completing a step and verifying that `uv run pytest` passes:
- Stage only relevant modified files (`git add`).
- Commit using conventional commit format: `git commit -m "<type>(<scope>): <short description>"`.
  - Example: `feat(items): add campus location filter`
- Report the commit message and hash upon completion.

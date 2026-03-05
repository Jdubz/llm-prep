# Bookmark API

A complete link-saving REST API built with FastAPI. This mini-project ties
together concepts from multiple course modules into a single, runnable
application with authentication, CRUD operations, filtering, pagination,
and a full test suite.

## Learning Objectives

- Build a multi-route FastAPI application from scratch
- Implement JWT authentication using only the Python standard library
- Design Pydantic models for request validation and response serialization
- Use FastAPI dependencies for auth enforcement and ownership checks
- Write async route handlers backed by an async-safe in-memory store
- Structure a project with routers, models, and a storage layer
- Write comprehensive integration tests with `httpx` and `pytest`

## Course Modules Covered

| Module | Topics applied in this project |
|--------|-------------------------------|
| **01 -- FastAPI Fundamentals** | App creation, routers, path operations, status codes |
| **02 -- Pydantic Models** | Request/response models, field validation, serialization |
| **03 -- Request Handling** | Path/query parameters, pagination, error responses, middleware |
| **04 -- Dependencies & Security** | `Depends()`, `HTTPBearer`, JWT auth, ownership guards |
| **06 -- Async Patterns** | `async def` routes, `asyncio.Lock`, lifespan events |

## Architecture Overview

```
bookmark-api/
  app/
    main.py          # FastAPI app, lifespan, middleware, exception handlers
    models.py         # Pydantic models (User, Bookmark, request/response variants)
    auth.py           # JWT creation/verification, password hashing, auth deps
    storage.py        # Async-safe in-memory storage (dict-backed)
    routes/
      users.py        # POST /register, POST /login
      bookmarks.py    # Full CRUD + filtering + pagination
  tests/
    test_api.py       # Integration tests covering all endpoints
  requirements.txt
  pyproject.toml
  README.md
```

**Key design decisions:**

- **No external database** -- uses an in-memory `dict` behind `asyncio.Lock`
  so the project has zero infrastructure dependencies.
- **No third-party auth libraries** -- JWT and password hashing use only
  `hmac`, `hashlib`, `base64`, and `json` from the standard library.
- **Ownership enforcement** -- users can only read/update/delete their own
  bookmarks (returns 403 for attempts on other users' resources).

## Setup Instructions

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API server
uvicorn app.main:app --reload

# 4. Open the interactive docs
#    http://127.0.0.1:8000/docs
```

## Running Tests

```bash
pytest tests/ -v
```

## API Endpoints

### Users

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/register` | Create a new user account | No |
| POST | `/login` | Authenticate and receive a JWT | No |

### Bookmarks

All bookmark endpoints require a valid JWT in the `Authorization: Bearer <token>` header.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/bookmarks` | Create a new bookmark |
| GET | `/bookmarks` | List bookmarks (supports `tag`, `search`, `page`, `size` query params) |
| GET | `/bookmarks/{id}` | Get a single bookmark (owner only) |
| PUT | `/bookmarks/{id}` | Update a bookmark (owner only) |
| DELETE | `/bookmarks/{id}` | Delete a bookmark (owner only) |

### Other

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

## Example Workflow

```bash
# Register
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "securepass123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "securepass123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create bookmark
curl -X POST http://localhost:8000/bookmarks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"url": "https://fastapi.tiangolo.com", "title": "FastAPI Docs", "tags": ["python", "web"]}'

# List bookmarks (filter by tag)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/bookmarks?tag=python&page=1&size=10"
```

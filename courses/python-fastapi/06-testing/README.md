# Module 06: Testing & Quality

## Prerequisites

You should be comfortable with pytest basics and have written at least a few FastAPI endpoints.
If you've done extensive testing in Vitest/Jest, most concepts transfer — but Python's testing
ecosystem has different idioms worth internalizing.

---

## 1. pytest Fundamentals for TypeScript Engineers

### The Mental Model Shift

In Vitest/Jest, you think in `describe` blocks, `beforeEach`/`afterEach`, and `it` functions.
In pytest, the primary abstraction is the **fixture** — a composable, dependency-injected setup
function that replaces `beforeEach`, factories, and mocking setup all at once.

```python
import pytest

@pytest.fixture
def db():
    """This IS your beforeEach. Cleanup goes after yield."""
    database = create_test_db()
    yield database          # <-- test runs here
    database.cleanup()      # <-- this is your afterEach

def test_creates_user(db):  # <-- db is injected automatically by name
    user = db.create_user(name="Alice")
    assert user.name == "Alice"
```

### Key Differences from Vitest/Jest

| Vitest/Jest | pytest | Notes |
|---|---|---|
| `describe()` | Test classes or modules | Classes optional; file grouping is common |
| `beforeEach()` | `@pytest.fixture` | Fixtures compose; `beforeEach` doesn't |
| `afterEach()` | `yield` in fixture | Teardown in the same fixture function |
| `beforeAll()` | `@pytest.fixture(scope="session")` | Session/module/class/function scope |
| `it()` / `test()` | `def test_*()` | Must start with `test_` |
| `expect(x).toBe(y)` | `assert x == y` | Plain assert + pytest introspection |
| `jest.mock()` | `monkeypatch` / `unittest.mock` | Multiple approaches |
| `.env.test` | `conftest.py` + fixtures | Config via fixtures |

### Fixtures in Depth

```python
# Function scope (default) — once per test
@pytest.fixture
def user():
    return User(name="Test User", email="test@example.com")

# Session scope — once for entire test suite
@pytest.fixture(scope="session")
def database_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

# Fixtures depend on other fixtures (composable DI)
@pytest.fixture
def authenticated_client(api_client, user):
    token = create_token(user)
    api_client.headers["Authorization"] = f"Bearer {token}"
    return api_client

# Autouse — applies to every test without being requested
@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
```

### Parametrize — Data-Driven Tests

```python
@pytest.mark.parametrize("email,is_valid", [
    ("user@example.com", True),
    ("user@.com", False),
    ("", False),
    ("user+tag@example.com", True),
])
def test_email_validation(email: str, is_valid: bool):
    assert validate_email(email) == is_valid

# With IDs for readable output
@pytest.mark.parametrize("status_code,expected", [
    pytest.param(200, {"status": "ok"}, id="success"),
    pytest.param(404, {"detail": "Not found"}, id="not-found"),
])
def test_error_responses(status_code, expected): ...
```

### Markers

```python
@pytest.mark.slow
def test_large_dataset(): ...

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature(): ...

@pytest.mark.xfail(reason="Known bug #123")
def test_known_broken(): ...

# Run: pytest -m "not slow"
```

### conftest.py — Shared Fixtures

`conftest.py` is pytest's mechanism for sharing fixtures across test files.

```
tests/
    conftest.py          # Available to ALL tests
    test_users.py
    api/
        conftest.py      # Available to tests in api/
        test_endpoints.py
```

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def db_session():
    async with AsyncSession(engine) as session:
        async with session.begin():
            yield session
            await session.rollback()

@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

---

## 2. Async Testing with pytest-asyncio

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

```python
# With asyncio_mode = "auto", just write async test functions
async def test_async_database_query(db_session):
    user = User(name="Alice", email="alice@example.com")
    db_session.add(user)
    await db_session.flush()
    result = await db_session.execute(select(User).where(User.email == "alice@example.com"))
    assert result.scalar_one().name == "Alice"
```

---

## 3. Integration Testing with httpx.AsyncClient

Python's equivalent of `supertest`. Tests your FastAPI app in-process via ASGI transport.

```python
from httpx import AsyncClient, ASGITransport

async def test_create_user(client: AsyncClient):
    response = await client.post("/users/", json={"name": "Alice", "email": "a@t.com"})
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
    assert "id" in response.json()

async def test_auth_required(client: AsyncClient):
    response = await client.get("/protected/resource")
    assert response.status_code == 401

async def test_authenticated_request(client: AsyncClient):
    login = await client.post("/auth/login", json={"email": "a@t.com", "password": "s"})
    token = login.json()["access_token"]
    response = await client.get("/protected/resource",
                                headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
```

### TestClient (Synchronous Alternative)

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
```

---

## 4. Dependency Overrides for Mocking

FastAPI's killer testing feature — swap real dependencies with test doubles at the app level.

```python
async def test_get_me(client: AsyncClient):
    mock_user = User(id=1, name="Test", email="test@test.com")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = await client.get("/me")
    assert response.status_code == 200
    assert response.json()["name"] == "Test"

    app.dependency_overrides.clear()
```

### Override as Fixture (Cleaner)

```python
@pytest.fixture
def authenticated_app(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield app
    app.dependency_overrides.clear()
```

### Overriding Database Dependency

```python
@pytest.fixture
async def db_session():
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn)
        try:
            yield session
        finally:
            await trans.rollback()
            await session.close()

@pytest.fixture(autouse=True)
async def override_db(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()
```

---

## 5. Test Database Setup

### Transaction Rollback Pattern

Each test runs in a transaction that rolls back. Fast, isolated, no cleanup.

```python
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_db"
test_engine = create_async_engine(TEST_DATABASE_URL)
TestSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db():
    async with TestSession() as session:
        async with session.begin():
            yield session
```

### Testcontainers (Ephemeral Docker Databases)

```python
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_url():
    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg")
```

---

## 6. Factory Patterns

### factory_boy with SQLAlchemy

```python
import factory
from factory.alchemy import SQLAlchemyModelFactory

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "flush"

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    role = "user"
    is_active = True

class AdminFactory(UserFactory):
    role = "admin"

class PostFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Post
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "flush"

    title = factory.Faker("sentence")
    body = factory.Faker("paragraph", nb_sentences=5)
    author = factory.SubFactory(UserFactory)
```

```python
# Usage in tests
async def test_list_posts(client, db_session):
    PostFactory.create_batch(5)
    await db_session.flush()
    response = await client.get("/posts/")
    assert len(response.json()["items"]) == 5
```

---

## 7. Mocking

### unittest.mock

```python
from unittest.mock import AsyncMock, patch

async def test_send_email(client):
    with patch("app.services.email.send_email", new_callable=AsyncMock) as mock:
        mock.return_value = {"message_id": "abc123"}
        response = await client.post("/users/", json={"name": "Alice", "email": "a@t.com"})
        assert response.status_code == 201
        mock.assert_called_once()
```

### pytest-mock

```python
async def test_process_payment(client, mocker):
    mock_stripe = mocker.patch("app.services.payment.stripe.PaymentIntent.create",
                               new_callable=AsyncMock)
    mock_stripe.return_value = MagicMock(id="pi_123", status="succeeded")
    response = await client.post("/payments/", json={"amount": 1000, "currency": "usd"})
    assert response.json()["payment_id"] == "pi_123"
```

### monkeypatch

```python
def test_debug_mode(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    settings = get_settings()
    assert settings.debug is True
```

### When NOT to Mock

1. **Don't mock your database in integration tests.** Use a real test DB with transaction rollback.
2. **Don't mock Pydantic models.** Just construct real ones.
3. **Don't mock what you own.** Mock at the boundary (external APIs, third-party services).
4. **Don't mock to make tests pass.** If a test needs mocking everything, the code needs refactoring.

```python
# BAD: mocking your own repository
async def test_create_user_bad(mocker):
    mock_repo = mocker.patch("app.services.user_service.UserRepository")
    mock_repo.return_value.create.return_value = User(id=1, name="Alice")
    # Tests nothing useful

# GOOD: real database
async def test_create_user_good(client, db_session):
    response = await client.post("/users/", json={"name": "Alice", "email": "a@t.com"})
    assert response.status_code == 201
    user = await db_session.execute(select(User).where(User.email == "a@t.com"))
    assert user.scalar_one().name == "Alice"
```

---

## 8. Testing WebSocket Endpoints

```python
from fastapi.testclient import TestClient

def test_websocket_echo():
    with TestClient(app).websocket_connect("/ws") as ws:
        ws.send_text("hello")
        assert ws.receive_text() == "Echo: hello"

def test_websocket_room_broadcast():
    client = TestClient(app)
    with client.websocket_connect("/ws/room/general?user=alice") as ws1:
        with client.websocket_connect("/ws/room/general?user=bob") as ws2:
            ws1.send_json({"message": "hello"})
            assert ws2.receive_json()["message"] == "hello"
```

---

## 9. Testing Background Tasks

Background tasks run synchronously in tests with `TestClient`.

```python
async def test_background_email_sent(client):
    with patch("app.tasks.send_email", new_callable=AsyncMock) as mock:
        response = await client.post("/users/", json={"name": "Alice", "email": "a@t.com"})
        assert response.status_code == 201
    mock.assert_called_once()
```

---

## 10. Testing File Uploads

```python
import io

async def test_upload_file(client: AsyncClient):
    response = await client.post("/upload/",
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")})
    assert response.status_code == 200
    assert response.json()["filename"] == "test.txt"

async def test_upload_too_large(client: AsyncClient):
    big_file = io.BytesIO(b"x" * (10 * 1024 * 1024 + 1))
    response = await client.post("/upload/",
        files={"file": ("big.bin", big_file, "application/octet-stream")})
    assert response.status_code == 413
```

---

## 11. Coverage and Mutation Testing

```bash
pytest --cov=app --cov-report=html --cov-fail-under=80
```

```toml
[tool.coverage.run]
source = ["app"]
omit = ["app/migrations/*", "app/tests/*"]

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:"]
```

Mutation testing with `mutmut` changes your code and checks if tests catch it:

```bash
pip install mutmut
mutmut run --paths-to-mutate=app/services/
mutmut results
```

---

## 12. Type Checking with mypy

```toml
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy", "sqlalchemy.ext.mypy.plugin"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

```python
# Typed dependencies
from typing import Annotated

CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]

@app.get("/me")
async def get_me(user: CurrentUser, db: DbSession) -> UserResponse: ...
```

---

## 13. Linting with Ruff

Ruff replaces flake8, isort, black, and more. Written in Rust, extremely fast.

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "SIM", "ASYNC", "S", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

```bash
ruff check app/ --fix && ruff format app/
```

---

## 14. Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, sqlalchemy[mypy]]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: detect-private-key
```

---

## Interview Questions

### Conceptual

1. **How does pytest's fixture system differ from `beforeEach`/`afterEach`, and what advantages does it offer?**

   Fixtures are composable and dependency-injected. Each fixture manages one concern, can depend on other fixtures (forming a DAG), and has scoping (function/class/module/session). `yield` unifies setup and teardown. Tests declare what they need; pytest resolves the graph automatically.

2. **You need to test an endpoint that calls an external payment API. Mocking strategy?**

   Use `app.dependency_overrides` to replace the payment service dependency. Mock at the HTTP boundary using `respx` or `httpx_mock` rather than internal methods. This tests your serialization, error handling, and retry logic against realistic HTTP responses.

3. **Explain the transaction rollback testing pattern. Why faster than truncating tables?**

   Each test runs inside a DB transaction that rolls back instead of committing. No data hits disk. Faster than `TRUNCATE` (requires table lock, WAL write) and `DELETE` (row-level undo). Trade-off: can't test commit-dependent behavior (triggers, certain constraint checks).

4. **`TestClient` (sync) vs `httpx.AsyncClient` — when to use which?**

   Use `httpx.AsyncClient` for async fixtures, async databases, and consistent async behavior. `TestClient` is simpler but runs async code in a thread, potentially masking concurrency issues. Prefer `AsyncClient` in fully async codebases.

5. **Test suite takes 15 minutes. How to speed it up?**

   Transaction rollback (not truncation). Parallel with `pytest-xdist`. Session-scoped fixtures for expensive setup. Replace slow integration tests with unit tests where possible. `pytest -x` to fail fast. Profile with `--durations=20`. SQLite for unit tests, Postgres only for integration.

### Coding Challenges

6. **Write a pytest fixture providing a clean async DB session with transaction rollback, wired to FastAPI dependency overrides and `httpx.AsyncClient`.**

7. **Write parametrized tests for email validation — valid, invalid, duplicates, edge cases.**

8. **Implement a `factory_boy` factory for `User` with related `Post` objects. Test pagination with batch-created data.**

9. **Write an integration test for a WebSocket chat endpoint — connection, broadcasting, disconnection.**

10. **Configure mypy strict mode for FastAPI. Type a generic paginated response and dependency-injected endpoint.**

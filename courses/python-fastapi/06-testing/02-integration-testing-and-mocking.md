# 02 – Integration Testing and Mocking

## Integration Testing with httpx.AsyncClient

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

---

## Dependency Overrides for Mocking

FastAPI's killer testing feature — swap real dependencies with test doubles at the app level.

```python
async def test_get_me(client: AsyncClient):
    mock_user = User(id=1, name="Test", email="test@test.com")
    app.dependency_overrides[get_current_user] = lambda: mock_user

    response = await client.get("/me")
    assert response.status_code == 200
    assert response.json()["name"] == "Test"

    app.dependency_overrides.clear()

# As a fixture (cleaner — cleanup guaranteed)
@pytest.fixture
def authenticated_app(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield app
    app.dependency_overrides.clear()

# Dependency override template
@pytest.fixture(autouse=True)
def override_deps(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(id=1, name="Test")
    yield
    app.dependency_overrides.clear()
```

---

## Test Database Setup

### Transaction Rollback Pattern

Each test runs in a transaction that rolls back. Fast, isolated, no cleanup:

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
            await session.rollback()
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

### Testcontainers (Ephemeral Docker Databases)

```python
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_url():
    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg")
```

---

## Factory Patterns

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

# Usage in tests
async def test_list_posts(client, db_session):
    PostFactory._meta.sqlalchemy_session = db_session
    PostFactory.create_batch(5)
    await db_session.flush()
    response = await client.get("/posts/")
    assert len(response.json()["items"]) == 5
```

Usage: `UserFactory()`, `UserFactory.create_batch(10)`, `AdminFactory()`

---

## Mocking

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

## Testing WebSocket Endpoints

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

## Testing Background Tasks

Background tasks run synchronously in tests with `TestClient`:

```python
async def test_background_email_sent(client):
    with patch("app.tasks.send_email", new_callable=AsyncMock) as mock:
        response = await client.post("/users/", json={"name": "Alice", "email": "a@t.com"})
        assert response.status_code == 201
    mock.assert_called_once()
```

---

## Testing File Uploads

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

## Testing Celery Tasks

### Eager Mode (Synchronous)

```python
@pytest.fixture(autouse=True)
def celery_eager():
    from app.worker import celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False

def test_process_order():
    from app.tasks import process_order
    result = process_order.delay(order_id=42)
    assert result.get() == {"status": "processed", "order_id": 42}
```

### Testing Retry Logic

```python
def test_task_retries_on_failure():
    with patch("app.tasks.external_api.send") as mock:
        mock.side_effect = [
            ConnectionError("timeout"),
            ConnectionError("timeout"),
            {"status": "sent"},
        ]
        result = send_notification.delay(user_id=1, message="hello")
        assert result.get() == {"status": "sent"}
        assert mock.call_count == 3
```

### With Real Broker (Integration)

```python
@pytest.fixture(scope="session")
def celery_config():
    return {"broker_url": "redis://localhost:6379/15",
            "result_backend": "redis://localhost:6379/15"}

def test_task_with_real_worker(celery_app, celery_worker):
    result = compute_report.delay(report_id="test-123")
    output = result.get(timeout=10)
    assert output["report_id"] == "test-123"
```

---

## Testing with Docker Compose

```yaml
# docker-compose.test.yml
services:
  db:
    image: postgres:16
    environment: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: test_db }
    healthcheck:
      test: pg_isready -U test
      interval: 2s
      retries: 5
  redis:
    image: redis:7
    healthcheck:
      test: redis-cli ping
      interval: 2s
      retries: 5
  test-runner:
    build: .
    command: pytest tests/integration/ -v --tb=short
    environment:
      DATABASE_URL: postgresql+asyncpg://test:test@db:5432/test_db
      REDIS_URL: redis://redis:6379/0
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
```

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

---

## Practice Exercises

Work through these exercises in `exercises.py` to practice the concepts from this file:

- **Exercise 2 (`TestCreateItem`)** — Practice integration testing with `httpx.AsyncClient`. POST JSON payloads, check 201/422/409 status codes, and verify Pydantic validation error structure (`response.json()["detail"]`). Covers: POST requests, validation error assertions, duplicate detection (409).

- **Exercise 3 (`TestWeatherEndpoint`)** — Practice `app.dependency_overrides` to replace an external service (`WeatherService`) with a fake class. Build a `FakeWeatherService`, wire it into the app, create your own `AsyncClient`, and clean up overrides. Covers: dependency override pattern, inline client creation, fake service classes.

- **Exercise 4 (`TestWebSocketChat`)** — Practice WebSocket testing using `TestClient(exercise_app)` with `websocket_connect()`. Send and receive JSON messages, handle the welcome message protocol, and test ping/pong. Covers: `TestClient` for sync WS tests, `send_json`/`receive_json`, multi-message sequences.

See also `examples.py` sections 5, 7, and 9 for working reference implementations of these patterns.

---

## Key Takeaways

- `app.dependency_overrides` lets you swap any dependency with a test double — use it in fixtures.
- Transaction rollback is faster than TRUNCATE and leaves no cleanup artifacts.
- Mock at boundaries (external APIs, third-party services); use real implementations internally.
- `factory_boy` with `SQLAlchemyModelFactory` replaces manual fixture data creation.
- `AsyncMock` is for async functions; `MagicMock` is for sync functions — don't mix them up.
- `TestClient` for WebSocket tests; `httpx.AsyncClient` for HTTP tests in async codebases.

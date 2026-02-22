# Module 06 Cheat Sheet: Testing & Quality

## pytest vs Vitest Quick Reference

| Vitest / Jest | pytest | Notes |
|---|---|---|
| `describe("group", () => {})` | `class TestGroup:` or group by file | Classes optional |
| `it("does X", () => {})` | `def test_does_x():` | Must start with `test_` |
| `expect(x).toBe(y)` | `assert x == y` | Plain assert; pytest rewrites for diffs |
| `expect(x).toEqual(y)` | `assert x == y` | Python `==` does deep comparison |
| `expect(fn).toThrow()` | `with pytest.raises(Error):` | Context manager |
| `beforeEach(() => {})` | `@pytest.fixture` | Injected by argument name |
| `afterEach(() => {})` | `yield` inside fixture | Code after yield is teardown |
| `beforeAll()` | `@pytest.fixture(scope="session")` | Session/module/class scope |
| `jest.mock("module")` | `monkeypatch` or `mock.patch` | Multiple approaches |
| `jest.fn()` | `MagicMock()` / `AsyncMock()` | From `unittest.mock` |
| `test.each([...])` | `@pytest.mark.parametrize` | More flexible |
| `vitest --coverage` | `pytest --cov=app` | Requires `pytest-cov` |
| `supertest(app)` | `httpx.AsyncClient` / `TestClient` | In-process ASGI testing |

---

## Fixture Template

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db, Base

TEST_DB = "postgresql+asyncpg://test:test@localhost:5432/test_db"
engine = create_async_engine(TEST_DB)
TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db():
    async with TestSession() as session:
        async with session.begin():
            yield session
            await session.rollback()

@pytest.fixture
async def client(db):
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

---

## httpx Test Client Template

```python
# Async (preferred)
async def test_create_user(client: AsyncClient):
    resp = await client.post("/users/", json={"name": "Alice", "email": "a@t.com"})
    assert resp.status_code == 201

# Sync (simpler)
from fastapi.testclient import TestClient
def test_health():
    assert TestClient(app).get("/health").status_code == 200

# With auth
async def test_protected(client: AsyncClient):
    resp = await client.get("/me", headers={"Authorization": "Bearer token"})
    assert resp.status_code == 200

# File upload
async def test_upload(client: AsyncClient):
    import io
    resp = await client.post("/upload/",
        files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")})
    assert resp.status_code == 200
```

---

## Dependency Override Template

```python
# As a fixture (recommended)
@pytest.fixture(autouse=True)
def override_deps(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(id=1, name="Test")
    yield
    app.dependency_overrides.clear()
```

---

## Factory Template (factory_boy)

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

class AdminFactory(UserFactory):
    role = "admin"

class PostFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Post
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "flush"
    title = factory.Faker("sentence")
    author = factory.SubFactory(UserFactory)

# Usage: UserFactory(), UserFactory.create_batch(10), AdminFactory()
```

---

## mypy Configuration

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

**Typed dependencies:**

```python
from typing import Annotated
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
```

---

## Ruff Configuration

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
ruff check app/ --fix       # Lint
ruff format app/            # Format
```

---

## Quick Commands

```bash
pytest                              # Run all
pytest --cov=app --cov-report=term  # With coverage
pytest tests/test_users.py          # Specific file
pytest -m "not slow"                # By marker
pytest -x --tb=short               # Fail fast, short traceback
pytest --durations=10               # Find slow tests
pytest -n auto                      # Parallel (pytest-xdist)
mypy app/ --strict                  # Type check
ruff check app/ --fix && ruff format app/  # Lint + format
```

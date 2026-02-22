# Module 06 Deep Dive: Advanced Testing Techniques

This deep dive covers property-based testing, contract testing, performance benchmarking,
and CI pipeline design for Python projects.

---

## 1. Property-Based Testing with Hypothesis

Hypothesis is Python's fast-check. Instead of specific test cases, you describe _properties_
your code should satisfy, and Hypothesis generates random inputs to find violations.

### Basic Examples

```python
from hypothesis import given, strategies as st

@given(st.integers(), st.integers())
def test_addition_is_commutative(a: int, b: int):
    assert a + b == b + a

@given(st.lists(st.integers()))
def test_sorted_is_ordered(xs: list[int]):
    result = sorted(xs)
    for i in range(len(result) - 1):
        assert result[i] <= result[i + 1]
```

### Testing Pydantic Models

```python
user_strategy = st.builds(
    UserCreate,
    name=st.text(min_size=1, max_size=100).filter(str.strip),
    email=st.emails(),
    age=st.integers(min_value=0, max_value=150),
)

@given(user_data=user_strategy)
def test_user_roundtrip(user_data: UserCreate):
    json_str = user_data.model_dump_json()
    restored = UserCreate.model_validate_json(json_str)
    assert restored == user_data
```

### Testing API Endpoints

```python
@given(name=st.text(min_size=1, max_size=200).filter(str.strip),
       age=st.integers(min_value=0, max_value=200))
@settings(max_examples=50)
@pytest.mark.anyio
async def test_create_user_never_500s(client: AsyncClient, name: str, age: int):
    response = await client.post("/users/",
        json={"name": name, "email": f"{name[:10]}@test.com", "age": age})
    assert response.status_code in (201, 422)  # Never 500
```

### Stateful Testing (Model-Based)

Hypothesis generates random sequences of operations and verifies invariants.

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize

class UserAPIMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.client = TestClient(app)
        self.known_users: dict[int, str] = {}

    @initialize()
    def setup(self):
        self.client.post("/test/reset-db")

    @rule(name=st.text(min_size=1, max_size=50).filter(str.strip))
    def create_user(self, name: str):
        email = f"{name[:8].replace(' ', '')}_{len(self.known_users)}@test.com"
        resp = self.client.post("/users/", json={"name": name, "email": email})
        if resp.status_code == 201:
            self.known_users[resp.json()["id"]] = name

    @rule()
    def list_users(self):
        resp = self.client.get("/users/")
        assert len(resp.json()["items"]) == len(self.known_users)

    @rule(data=st.data())
    def get_user(self, data):
        if not self.known_users:
            return
        uid = data.draw(st.sampled_from(list(self.known_users.keys())))
        resp = self.client.get(f"/users/{uid}")
        assert resp.json()["name"] == self.known_users[uid]

TestUserAPI = UserAPIMachine.TestCase
```

---

## 2. Contract Testing with Schemathesis

Schemathesis auto-generates test cases from your OpenAPI schema — finding crashes, validation
errors, and spec violations.

```bash
# CLI
schemathesis run http://localhost:8000/openapi.json

# Directly against the app (no server)
schemathesis run --app=app.main:app /openapi.json
```

### Programmatic Usage

```python
import schemathesis
from app.main import app

schema = schemathesis.from_asgi("/openapi.json", app=app)

@schema.parametrize()
def test_api_contract(case):
    response = case.call_asgi()
    case.validate_response(response)

# Targeted
@schema.parametrize(endpoint="/users/.*", method="POST")
def test_user_creation_contract(case):
    response = case.call_asgi()
    case.validate_response(response)
```

### What Schemathesis Catches

1. **500 errors** from unexpected input combinations
2. **Response schema violations** (response doesn't match declared model)
3. **Missing error handling** (empty strings, negative numbers, Unicode)
4. **Content-Type mismatches**
5. **Undeclared response codes**

---

## 3. Snapshot Testing

Capture output and compare against a stored snapshot.

```python
# syrupy (pytest plugin)
def test_user_response_shape(client, snapshot):
    response = client.get("/users/1")
    assert response.json() == snapshot

# Run with --snapshot-update to regenerate
```

---

## 4. Testing Celery Tasks

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

## 5. Testing with Docker Compose

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

### Testcontainers Alternative

```python
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture(scope="session")
async def app_with_deps(postgres, redis):
    os.environ["DATABASE_URL"] = postgres.get_connection_url().replace("psycopg2", "asyncpg")
    from app.main import app
    yield app
```

---

## 6. CI Pipeline Design

### GitHub Actions

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      - run: uv run ruff check app/
      - run: uv run ruff format --check app/
      - run: uv run mypy app/ --strict

  test-unit:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      - run: uv run pytest tests/unit/ -v --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4

  test-integration:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: test, POSTGRES_PASSWORD: test, POSTGRES_DB: test_db }
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 5s --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]
        options: --health-cmd "redis-cli ping" --health-interval 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      - run: uv run pytest tests/integration/ -v
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
```

### Pipeline Best Practices

1. **Parallelize independent jobs.** Lint, unit tests, security can run simultaneously.
2. **Fail fast.** Lint first — don't run tests if formatting is wrong.
3. **Use `uv`** for fast dependency resolution and caching.
4. **Integration tests on PR only**, not every commit, to save CI minutes.
5. **Use GitHub Actions services** for Postgres/Redis (faster than Testcontainers in CI).

---

## 7. Benchmarking with pytest-benchmark

### Basic Benchmarking

```python
def test_json_serialization_speed(benchmark):
    user = UserResponse(id=1, name="Alice", email="alice@test.com", role="user")
    result = benchmark(user.model_dump_json)
    assert result

def test_database_query_speed(benchmark, db_session):
    for i in range(1000):
        db_session.add(User(name=f"User {i}", email=f"u{i}@test.com"))
    db_session.commit()

    def query():
        return db_session.execute(
            select(User).where(User.name.ilike("%User 5%")).limit(10)
        ).scalars().all()

    result = benchmark(query)
    assert len(result) > 0
```

### Preventing Regressions

```bash
# Save baseline
pytest tests/benchmarks/ --benchmark-save=baseline

# Compare in CI — fail if >5% slower
pytest tests/benchmarks/ --benchmark-compare=baseline --benchmark-compare-fail=mean:5%
```

### What to Benchmark

1. **Serialization** — Pydantic model validation and dumping
2. **Database queries** — Complex joins and aggregations
3. **Authentication** — Token generation/verification
4. **Business logic** — Computationally intensive operations

### What NOT to Benchmark in Unit Tests

1. **Network calls** — Use load testing tools (locust, k6)
2. **DB writes under load** — Use load testing, not pytest-benchmark
3. **High-variance operations** — If results vary >20%, the benchmark is unreliable

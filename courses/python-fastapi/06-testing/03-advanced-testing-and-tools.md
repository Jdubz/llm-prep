# 03 – Advanced Testing and Tools

## Property-Based Testing with Hypothesis

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
from hypothesis import settings

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

Hypothesis generates random sequences of operations and verifies invariants:

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

## Contract Testing with Schemathesis

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

## Snapshot Testing

Capture output and compare against a stored snapshot:

```python
# syrupy (pytest plugin)
def test_user_response_shape(client, snapshot):
    response = client.get("/users/1")
    assert response.json() == snapshot

# Run with --snapshot-update to regenerate
```

---

## Coverage and Mutation Testing

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

## Benchmarking with pytest-benchmark

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

# Compare in CI -- fail if >5% slower
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

---

## CI Pipeline Design

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

## Interview Questions

### Conceptual

**1. How does pytest's fixture system differ from `beforeEach`/`afterEach`, and what advantages does it offer?**

Fixtures are composable and dependency-injected. Each fixture manages one concern, can depend on other fixtures (forming a DAG), and has scoping (function/class/module/session). `yield` unifies setup and teardown. Tests declare what they need; pytest resolves the graph automatically.

**2. You need to test an endpoint that calls an external payment API. Mocking strategy?**

Use `app.dependency_overrides` to replace the payment service dependency. Mock at the HTTP boundary using `respx` or `httpx_mock` rather than internal methods. This tests your serialization, error handling, and retry logic against realistic HTTP responses.

**3. Explain the transaction rollback testing pattern. Why faster than truncating tables?**

Each test runs inside a DB transaction that rolls back instead of committing. No data hits disk. Faster than `TRUNCATE` (requires table lock, WAL write) and `DELETE` (row-level undo). Trade-off: can't test commit-dependent behavior (triggers, certain constraint checks).

**4. `TestClient` (sync) vs `httpx.AsyncClient` — when to use which?**

Use `httpx.AsyncClient` for async fixtures, async databases, and consistent async behavior. `TestClient` is simpler but runs async code in a thread, potentially masking concurrency issues. Prefer `AsyncClient` in fully async codebases.

**5. Test suite takes 15 minutes. How to speed it up?**

Transaction rollback (not truncation). Parallel with `pytest-xdist`. Session-scoped fixtures for expensive setup. Replace slow integration tests with unit tests where possible. `pytest -x` to fail fast. Profile with `--durations=20`. SQLite for unit tests, Postgres only for integration.

### Coding Challenges

**6. Write a pytest fixture** providing a clean async DB session with transaction rollback, wired to FastAPI dependency overrides and `httpx.AsyncClient`.

**7. Write parametrized tests for email validation** — valid, invalid, duplicates, edge cases.

**8. Implement a `factory_boy` factory for `User`** with related `Post` objects. Test pagination with batch-created data.

**9. Write an integration test for a WebSocket chat endpoint** — connection, broadcasting, disconnection.

**10. Configure mypy strict mode for FastAPI.** Type a generic paginated response and dependency-injected endpoint.

---

## Practice Exercises

Work through these exercises in `exercises.py` to practice the concepts from this file:

- **Exercise 5 (`test_valid_item_creation`, `test_invalid_item_creation`)** — Practice parametrized testing for validation edge cases. These exercises connect to the "Parametrize" syntax from `01-pytest-fixtures-and-basics.md` but apply it to boundary-value testing: minimum/maximum valid values, type errors, missing fields. This is the manual version of what Hypothesis and Schemathesis do automatically.

- **All exercises** — After completing exercises 1-5, consider how property-based testing (Hypothesis) could replace your hand-written parametrize lists. For example, Exercise 5b's invalid payloads are exactly the kind of edge cases Schemathesis would auto-generate from your OpenAPI schema.

See also `examples.py` section 6 (test_create_user_validation) for a complete parametrized validation test.

---

## Key Takeaways

- Property-based testing (Hypothesis) finds edge cases you wouldn't think to test manually.
- Schemathesis auto-tests your entire API against its OpenAPI schema — essential for catching regressions.
- Mutation testing (`mutmut`) checks whether your tests actually verify behavior, not just coverage.
- Benchmarks catch performance regressions; use `--benchmark-compare-fail=mean:5%` in CI.
- CI pipelines should: run lint first, parallelize independent jobs, use services for databases.
- `uv` is the modern Python package manager — faster than pip, use `uv sync --frozen` in CI.

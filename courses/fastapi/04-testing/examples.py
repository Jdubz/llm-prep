"""
Module 06 — Testing & Quality: Complete Examples
=================================================

Runnable testing patterns for FastAPI using pytest, httpx, and dependency overrides.

Run with:  pytest examples.py -v
Requires:  fastapi, httpx, pytest, pytest-asyncio
Configure: [tool.pytest.ini_options] asyncio_mode = "auto"
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

# =============================================================================
# 1. A Small FastAPI App to Test Against (User CRUD, in-memory store)
# =============================================================================

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r"^[\w.+-]+@[\w-]+\.[\w.]+$")
    role: str = Field(default="user")

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: str

fake_db: dict[str, dict] = {}

def get_db() -> dict[str, dict]:
    return fake_db

SECRET_TOKEN = "test-secret-token-123"

def get_current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    """Simplified auth. Vitest: you'd mock middleware; here we override the dependency."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if authorization.removeprefix("Bearer ") != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user_id": "admin-001", "role": "admin"}

class EmailService:
    """External service stub -- raises in production to catch unoverridden calls."""
    async def send_welcome_email(self, email: str, name: str) -> dict:
        raise RuntimeError("Real email service called in tests!")

def get_email_service() -> EmailService:
    return EmailService()

app = FastAPI(title="Testing Examples")

@app.post("/users/", status_code=201)
async def create_user(
    user: UserCreate,
    db: Annotated[dict, Depends(get_db)],
    email_svc: Annotated[EmailService, Depends(get_email_service)],
) -> UserResponse:
    for existing in db.values():
        if existing["email"] == user.email:
            raise HTTPException(status_code=409, detail="Email already registered")
    user_id = str(uuid.uuid4())
    record = {"id": user_id, "name": user.name, "email": user.email,
              "role": user.role, "created_at": datetime.now(timezone.utc).isoformat()}
    db[user_id] = record
    await email_svc.send_welcome_email(user.email, user.name)
    return UserResponse(**record)

@app.get("/users/")
async def list_users(db: Annotated[dict, Depends(get_db)], role: str | None = None):
    users = [u for u in db.values() if not role or u["role"] == role]
    return [UserResponse(**u) for u in users]

@app.get("/users/{user_id}")
async def get_user(user_id: str, db: Annotated[dict, Depends(get_db)]):
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**db[user_id])

@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str, db: Annotated[dict, Depends(get_db)],
                      _auth: Annotated[dict, Depends(get_current_user)]):
    if user_id not in db:
        raise HTTPException(status_code=404, detail="User not found")
    del db[user_id]

@app.get("/admin/dashboard")
async def admin_dashboard(current_user: Annotated[dict, Depends(get_current_user)]):
    return {"message": f"Welcome, {current_user['user_id']}", "role": current_user["role"]}

@app.websocket("/ws/echo")
async def websocket_echo(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        if data == "close":
            await websocket.close()
            break
        await websocket.send_text(f"Echo: {data}")


# =============================================================================
# 2. Fixtures (replace beforeEach/afterEach from Vitest/Jest)
# =============================================================================
# Vitest:  beforeEach(() => { db = {}; client = supertest(app); });
# pytest:  each fixture manages its own setup AND teardown via yield.

@pytest.fixture
def test_db() -> dict[str, dict]:
    """Fresh in-memory database per test. Vitest: beforeEach(() => { db = {} })"""
    return {}

@pytest.fixture
def mock_email_service():
    """Fake that records calls. Vitest: const send = vi.fn().mockResolvedValue({})"""
    class FakeEmailService:
        def __init__(self):
            self.sent: list[dict] = []
        async def send_welcome_email(self, email: str, name: str) -> dict:
            self.sent.append({"email": email, "name": name})
            return {"sent": True}
    return FakeEmailService()

@pytest.fixture
async def client(test_db, mock_email_service) -> AsyncClient:
    """Async HTTP client with dependency overrides. Equivalent to supertest(app)."""
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_email_service] = lambda: mock_email_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SECRET_TOKEN}"}

@pytest.fixture
async def authenticated_client(client: AsyncClient, auth_headers) -> AsyncClient:
    """Client pre-configured with valid auth headers."""
    client.headers.update(auth_headers)
    return client


# =============================================================================
# 3. Factory Pattern (manual -- no factory_boy dependency)
# =============================================================================
# Vitest: function buildUser(overrides = {}) { return { name: 'Test', ...overrides }; }

_counter = 0

def build_user(**overrides) -> dict:
    """Returns user creation payload with sensible defaults."""
    global _counter
    _counter += 1
    return {"name": f"User {_counter}", "email": f"u{_counter}@example.com",
            "role": "user", **overrides}

def build_admin(**overrides) -> dict:
    return build_user(role="admin", **overrides)


# =============================================================================
# 4. Async Integration Tests with httpx.AsyncClient
# =============================================================================
# Vitest: const res = await request(app).post('/users').send({...});
#         expect(res.status).toBe(201);

class TestUserCRUD:
    """Group related tests in a class (optional -- equivalent to describe())."""

    async def test_create_user(self, client: AsyncClient, mock_email_service):
        response = await client.post("/users/", json=build_user(name="Alice", email="a@example.com"))
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice"
        assert "id" in data
        # Verify side effect: welcome email was "sent"
        assert mock_email_service.sent[0]["email"] == "a@example.com"

    async def test_list_users_empty(self, client: AsyncClient):
        response = await client.get("/users/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_and_filter_by_role(self, client: AsyncClient):
        await client.post("/users/", json=build_user(email="u@example.com", role="user"))
        await client.post("/users/", json=build_admin(email="a@example.com"))
        response = await client.get("/users/", params={"role": "admin"})
        assert len(response.json()) == 1
        assert response.json()[0]["role"] == "admin"

    async def test_get_user_not_found(self, client: AsyncClient):
        response = await client.get("/users/nonexistent-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    async def test_get_user_by_id(self, client: AsyncClient):
        created = await client.post("/users/", json=build_user(name="Charlie", email="c@example.com"))
        response = await client.get(f"/users/{created.json()['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "Charlie"


# =============================================================================
# 5. Dependency Override Pattern for Mocking
# =============================================================================
# Override any Depends() at the app level -- cleaner than monkeypatching.

async def test_dependency_override_inline(test_db):
    """Override inline for fine-grained per-test control (spy pattern)."""
    calls: list[dict] = []
    class SpyEmailService:
        async def send_welcome_email(self, email: str, name: str) -> dict:
            calls.append({"email": email, "name": name})
            return {"sent": True}

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_email_service] = SpyEmailService
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/users/", json={"name": "Spy", "email": "spy@example.com"})
    assert resp.status_code == 201
    assert len(calls) == 1
    app.dependency_overrides.clear()


# =============================================================================
# 6. Parametrized Tests for Validation Edge Cases
# =============================================================================
# Vitest: test.each([['', 422], ['valid', 201]])('name=%s -> %i', ...)

@pytest.mark.parametrize("payload,expected_status,error_field", [
    pytest.param({"name": "Valid", "email": "v@example.com"}, 201, None, id="valid-user"),
    pytest.param({"name": "", "email": "v@example.com"}, 422, "name", id="empty-name"),
    pytest.param({"name": "A" * 101, "email": "v@example.com"}, 422, "name", id="name-too-long"),
    pytest.param({"name": "Valid", "email": "not-an-email"}, 422, "email", id="bad-email"),
    pytest.param({"name": "Valid", "email": ""}, 422, "email", id="empty-email"),
    pytest.param({"email": "no@name.com"}, 422, "name", id="missing-name"),
    pytest.param({"name": "No Email"}, 422, "email", id="missing-email"),
])
async def test_create_user_validation(client: AsyncClient, payload, expected_status, error_field):
    response = await client.post("/users/", json=payload)
    assert response.status_code == expected_status
    if expected_status == 422:
        error_locs = [e["loc"][-1] for e in response.json()["detail"]]
        assert error_field in error_locs


# =============================================================================
# 7. Testing Error Responses and Status Codes
# =============================================================================

async def test_duplicate_email_returns_409(client: AsyncClient):
    payload = build_user(email="dupe@example.com")
    first = await client.post("/users/", json=payload)
    assert first.status_code == 201
    second = await client.post("/users/", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"

async def test_delete_nonexistent_returns_404(authenticated_client: AsyncClient):
    assert (await authenticated_client.delete("/users/nope")).status_code == 404

async def test_delete_success_returns_204(authenticated_client: AsyncClient):
    created = await authenticated_client.post("/users/", json=build_user(email="del@example.com"))
    user_id = created.json()["id"]
    assert (await authenticated_client.delete(f"/users/{user_id}")).status_code == 204
    assert (await authenticated_client.get(f"/users/{user_id}")).status_code == 404


# =============================================================================
# 8. Testing Auth-Protected Endpoints with Token Fixture
# =============================================================================
# Vitest: expect(res.status).toBe(401)  /  .set('Authorization', `Bearer ${token}`)

async def test_no_token_returns_401(client: AsyncClient):
    resp = await client.get("/admin/dashboard")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"

async def test_invalid_token_returns_401(client: AsyncClient):
    resp = await client.get("/admin/dashboard", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"

async def test_malformed_auth_header(client: AsyncClient):
    resp = await client.get("/admin/dashboard", headers={"Authorization": "Token xyz"})
    assert resp.status_code == 401

async def test_valid_token_grants_access(client: AsyncClient, auth_headers):
    resp = await client.get("/admin/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

async def test_delete_requires_auth(client: AsyncClient):
    """Auth failure (401) takes precedence over not-found (404)."""
    assert (await client.delete("/users/any-id")).status_code == 401

async def test_override_auth_for_business_logic(test_db):
    """Override auth entirely to focus on delete logic, not token mechanics."""
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_email_service] = lambda: type(
        "Fake", (), {"send_welcome_email": staticmethod(lambda *a, **k: None)})()
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "t", "role": "admin"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        created = await ac.post("/users/", json=build_user(email="ov@example.com"))
        assert (await ac.delete(f"/users/{created.json()['id']}")).status_code == 204
    app.dependency_overrides.clear()


# =============================================================================
# 9. WebSocket Testing (uses sync TestClient -- httpx has no WS support)
# =============================================================================
# Vitest: const ws = new WebSocket(url); ws.send('hello'); expect(msg).toBe(...)

def test_websocket_echo():
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/echo") as ws:
            ws.send_text("hello")
            assert ws.receive_text() == "Echo: hello"
            ws.send_text("world")
            assert ws.receive_text() == "Echo: world"

def test_websocket_close():
    with TestClient(app) as tc:
        with tc.websocket_connect("/ws/echo") as ws:
            ws.send_text("close")


# =============================================================================
# Quick Reference: pytest vs Vitest/Jest
# =============================================================================
# Test grouping       | class TestXyz / module       | describe('xyz', () => {})
# Setup/teardown      | @pytest.fixture + yield      | beforeEach / afterEach
# Shared fixtures     | conftest.py                  | Global setup files
# HTTP client         | httpx.AsyncClient + ASGI     | supertest(app)
# Mock dependencies   | app.dependency_overrides      | vi.mock() / jest.mock()
# Parametrized tests  | @pytest.mark.parametrize     | test.each([...])
# Assertions          | assert x == y                | expect(x).toBe(y)
# WebSocket           | TestClient.websocket_connect | ws / mock-socket

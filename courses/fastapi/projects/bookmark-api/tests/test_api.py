"""
Complete test suite for the Bookmark API.

Tests cover:
- User registration and login
- CRUD operations on bookmarks
- Auth protection (401 without token)
- Ownership checks (403 for other users' bookmarks)
- Filtering and pagination
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage import storage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def _clear_storage():
    """Ensure every test starts with a clean slate."""
    await storage.clear()
    yield
    await storage.clear()


@pytest.fixture()
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register_user(
    client: AsyncClient,
    username: str = "alice",
    email: str = "alice@example.com",
    password: str = "securepass123",
) -> dict:
    """Helper: register a user and return the response JSON."""
    resp = await client.post(
        "/register",
        json={"username": username, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login_user(
    client: AsyncClient,
    username: str = "alice",
    password: str = "securepass123",
) -> str:
    """Helper: login and return the access token."""
    resp = await client.post(
        "/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# User registration & login tests
# ---------------------------------------------------------------------------

class TestUserRegistration:

    @pytest.mark.anyio
    async def test_register_success(self, client: AsyncClient):
        data = await _register_user(client)
        assert "id" in data
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"
        # Password must never appear in the response
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.anyio
    async def test_register_duplicate_username(self, client: AsyncClient):
        await _register_user(client)
        resp = await client.post(
            "/register",
            json={
                "username": "alice",
                "email": "other@example.com",
                "password": "securepass123",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_register_duplicate_email(self, client: AsyncClient):
        await _register_user(client)
        resp = await client.post(
            "/register",
            json={
                "username": "bob",
                "email": "alice@example.com",
                "password": "securepass123",
            },
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_register_validation_short_password(self, client: AsyncClient):
        resp = await client.post(
            "/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "short",
            },
        )
        assert resp.status_code == 422


class TestUserLogin:

    @pytest.mark.anyio
    async def test_login_success(self, client: AsyncClient):
        await _register_user(client)
        resp = await client.post(
            "/login",
            json={"username": "alice", "password": "securepass123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    @pytest.mark.anyio
    async def test_login_wrong_password(self, client: AsyncClient):
        await _register_user(client)
        resp = await client.post(
            "/login",
            json={"username": "alice", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_login_unknown_user(self, client: AsyncClient):
        resp = await client.post(
            "/login",
            json={"username": "nobody", "password": "irrelevant"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Auth protection tests
# ---------------------------------------------------------------------------

class TestAuthProtection:

    @pytest.mark.anyio
    async def test_create_bookmark_without_token(self, client: AsyncClient):
        resp = await client.post(
            "/bookmarks",
            json={"url": "https://example.com", "title": "Example"},
        )
        assert resp.status_code in (401, 403)  # depends on FastAPI/Starlette version

    @pytest.mark.anyio
    async def test_list_bookmarks_without_token(self, client: AsyncClient):
        resp = await client.get("/bookmarks")
        assert resp.status_code in (401, 403)  # depends on FastAPI/Starlette version

    @pytest.mark.anyio
    async def test_invalid_token(self, client: AsyncClient):
        resp = await client.get(
            "/bookmarks",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Bookmark CRUD tests
# ---------------------------------------------------------------------------

class TestBookmarkCRUD:

    @pytest.mark.anyio
    async def test_create_bookmark(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)

        resp = await client.post(
            "/bookmarks",
            json={
                "url": "https://fastapi.tiangolo.com",
                "title": "FastAPI Docs",
                "description": "Official docs",
                "tags": ["python", "web"],
            },
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["url"] == "https://fastapi.tiangolo.com"
        assert body["title"] == "FastAPI Docs"
        assert body["tags"] == ["python", "web"]
        assert "id" in body
        assert "created_at" in body

    @pytest.mark.anyio
    async def test_get_bookmark(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)

        create_resp = await client.post(
            "/bookmarks",
            json={"url": "https://example.com", "title": "Example"},
            headers=_auth_header(token),
        )
        bm_id = create_resp.json()["id"]

        resp = await client.get(
            f"/bookmarks/{bm_id}", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == bm_id

    @pytest.mark.anyio
    async def test_get_nonexistent_bookmark(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)

        resp = await client.get(
            "/bookmarks/does-not-exist", headers=_auth_header(token)
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_update_bookmark(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)

        create_resp = await client.post(
            "/bookmarks",
            json={"url": "https://example.com", "title": "Old Title"},
            headers=_auth_header(token),
        )
        bm_id = create_resp.json()["id"]

        resp = await client.put(
            f"/bookmarks/{bm_id}",
            json={"title": "New Title", "tags": ["updated"]},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "New Title"
        assert body["tags"] == ["updated"]
        # url should remain unchanged
        assert body["url"] == "https://example.com"

    @pytest.mark.anyio
    async def test_delete_bookmark(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)

        create_resp = await client.post(
            "/bookmarks",
            json={"url": "https://example.com", "title": "To Delete"},
            headers=_auth_header(token),
        )
        bm_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/bookmarks/{bm_id}", headers=_auth_header(token)
        )
        assert resp.status_code == 204

        # Confirm it's gone
        resp = await client.get(
            f"/bookmarks/{bm_id}", headers=_auth_header(token)
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Ownership tests
# ---------------------------------------------------------------------------

class TestOwnership:

    @pytest.mark.anyio
    async def test_cannot_read_others_bookmark(self, client: AsyncClient):
        # Alice creates a bookmark
        await _register_user(client, "alice", "alice@example.com", "securepass123")
        alice_token = await _login_user(client, "alice", "securepass123")

        create_resp = await client.post(
            "/bookmarks",
            json={"url": "https://alice.dev", "title": "Alice's site"},
            headers=_auth_header(alice_token),
        )
        bm_id = create_resp.json()["id"]

        # Bob tries to access it
        await _register_user(client, "bob", "bob@example.com", "securepass456")
        bob_token = await _login_user(client, "bob", "securepass456")

        resp = await client.get(
            f"/bookmarks/{bm_id}", headers=_auth_header(bob_token)
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_cannot_update_others_bookmark(self, client: AsyncClient):
        await _register_user(client, "alice", "alice@example.com", "securepass123")
        alice_token = await _login_user(client, "alice", "securepass123")

        create_resp = await client.post(
            "/bookmarks",
            json={"url": "https://alice.dev", "title": "Alice's site"},
            headers=_auth_header(alice_token),
        )
        bm_id = create_resp.json()["id"]

        await _register_user(client, "bob", "bob@example.com", "securepass456")
        bob_token = await _login_user(client, "bob", "securepass456")

        resp = await client.put(
            f"/bookmarks/{bm_id}",
            json={"title": "Hacked!"},
            headers=_auth_header(bob_token),
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_cannot_delete_others_bookmark(self, client: AsyncClient):
        await _register_user(client, "alice", "alice@example.com", "securepass123")
        alice_token = await _login_user(client, "alice", "securepass123")

        create_resp = await client.post(
            "/bookmarks",
            json={"url": "https://alice.dev", "title": "Alice's site"},
            headers=_auth_header(alice_token),
        )
        bm_id = create_resp.json()["id"]

        await _register_user(client, "bob", "bob@example.com", "securepass456")
        bob_token = await _login_user(client, "bob", "securepass456")

        resp = await client.delete(
            f"/bookmarks/{bm_id}", headers=_auth_header(bob_token)
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Filtering & pagination tests
# ---------------------------------------------------------------------------

class TestFilteringAndPagination:

    async def _seed_bookmarks(self, client: AsyncClient, token: str):
        """Create several bookmarks for filtering/pagination tests."""
        bookmarks_data = [
            {
                "url": "https://fastapi.tiangolo.com",
                "title": "FastAPI Docs",
                "description": "Official FastAPI documentation",
                "tags": ["python", "web", "api"],
            },
            {
                "url": "https://docs.pydantic.dev",
                "title": "Pydantic Docs",
                "description": "Data validation library",
                "tags": ["python", "validation"],
            },
            {
                "url": "https://react.dev",
                "title": "React Docs",
                "description": "JavaScript UI library",
                "tags": ["javascript", "web"],
            },
            {
                "url": "https://htmx.org",
                "title": "HTMX",
                "description": "High-power tools for HTML",
                "tags": ["web", "html"],
            },
            {
                "url": "https://python.org",
                "title": "Python.org",
                "description": "The Python programming language",
                "tags": ["python"],
            },
        ]
        for bm in bookmarks_data:
            await client.post(
                "/bookmarks", json=bm, headers=_auth_header(token)
            )

    @pytest.mark.anyio
    async def test_list_all_bookmarks(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        resp = await client.get("/bookmarks", headers=_auth_header(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 5

    @pytest.mark.anyio
    async def test_filter_by_tag(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        resp = await client.get(
            "/bookmarks", params={"tag": "python"}, headers=_auth_header(token)
        )
        body = resp.json()
        assert body["total"] == 3
        titles = {item["title"] for item in body["items"]}
        assert "FastAPI Docs" in titles
        assert "Pydantic Docs" in titles
        assert "Python.org" in titles

    @pytest.mark.anyio
    async def test_filter_by_tag_case_insensitive(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        resp = await client.get(
            "/bookmarks", params={"tag": "Python"}, headers=_auth_header(token)
        )
        assert resp.json()["total"] == 3

    @pytest.mark.anyio
    async def test_search_title(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        resp = await client.get(
            "/bookmarks", params={"search": "docs"}, headers=_auth_header(token)
        )
        body = resp.json()
        assert body["total"] == 3  # FastAPI Docs, Pydantic Docs, React Docs (description has "docs" via search)

    @pytest.mark.anyio
    async def test_search_description(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        resp = await client.get(
            "/bookmarks",
            params={"search": "javascript"},
            headers=_auth_header(token),
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "React Docs"

    @pytest.mark.anyio
    async def test_pagination(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        # Page 1, size 2
        resp = await client.get(
            "/bookmarks",
            params={"page": 1, "size": 2},
            headers=_auth_header(token),
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["size"] == 2

        # Page 3, size 2 -- should have 1 item left
        resp = await client.get(
            "/bookmarks",
            params={"page": 3, "size": 2},
            headers=_auth_header(token),
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 1

    @pytest.mark.anyio
    async def test_pagination_beyond_last_page(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        resp = await client.get(
            "/bookmarks",
            params={"page": 100, "size": 20},
            headers=_auth_header(token),
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 0

    @pytest.mark.anyio
    async def test_combined_filter_and_pagination(self, client: AsyncClient):
        await _register_user(client)
        token = await _login_user(client)
        await self._seed_bookmarks(client, token)

        resp = await client.get(
            "/bookmarks",
            params={"tag": "web", "page": 1, "size": 2},
            headers=_auth_header(token),
        )
        body = resp.json()
        # "web" tag: FastAPI Docs, React Docs, HTMX  => total 3
        assert body["total"] == 3
        assert len(body["items"]) == 2

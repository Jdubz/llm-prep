"""
Module 02 — Testing: Python Testing Examples
=============================================

Core pytest patterns: fixtures, parametrize, mocking, factories.
No web framework dependencies — pure Python testing.

Run with:  pytest examples.py -v
Requires:  pytest, pytest-asyncio
Configure: [tool.pytest.ini_options] asyncio_mode = "auto"
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# 1. A Simple Module to Test (no frameworks)
# =============================================================================

class UserStore:
    """In-memory user store for testing examples."""
    def __init__(self):
        self._users: dict[str, dict] = {}
        self._counter = 0

    def create(self, name: str, email: str) -> dict:
        self._counter += 1
        user = {"id": self._counter, "name": name, "email": email}
        self._users[str(self._counter)] = user
        return user

    def get(self, user_id: str) -> dict | None:
        return self._users.get(user_id)

    def list_all(self) -> list[dict]:
        return list(self._users.values())

    def delete(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False


class EmailService:
    """External service stub."""
    async def send(self, to: str, subject: str) -> dict:
        raise RuntimeError("Real email service called in tests!")


class UserService:
    """Business logic layer that depends on store + email."""
    def __init__(self, store: UserStore, email_service: EmailService):
        self.store = store
        self.email = email_service

    async def register(self, name: str, email: str) -> dict:
        for user in self.store.list_all():
            if user["email"] == email:
                raise ValueError(f"Email {email} already registered")
        user = self.store.create(name, email)
        await self.email.send(email, f"Welcome, {name}!")
        return user


# =============================================================================
# 2. Fixtures (replace beforeEach/afterEach)
# =============================================================================

@pytest.fixture
def store() -> UserStore:
    """Fresh store per test."""
    return UserStore()


@pytest.fixture
def mock_email() -> AsyncMock:
    """Mock email service that records calls."""
    service = AsyncMock(spec=EmailService)
    service.send.return_value = {"sent": True}
    return service


@pytest.fixture
def user_service(store, mock_email) -> UserService:
    """Service with injected dependencies."""
    return UserService(store, mock_email)


@pytest.fixture
def seeded_store() -> UserStore:
    """Store pre-populated with test data."""
    s = UserStore()
    s.create("Alice", "alice@example.com")
    s.create("Bob", "bob@example.com")
    s.create("Charlie", "charlie@example.com")
    return s


# =============================================================================
# 3. Basic Tests with Fixtures
# =============================================================================

class TestUserStore:
    def test_create_user(self, store: UserStore):
        user = store.create("Alice", "alice@example.com")
        assert user["name"] == "Alice"
        assert user["id"] == 1

    def test_get_user(self, store: UserStore):
        created = store.create("Bob", "bob@example.com")
        found = store.get(str(created["id"]))
        assert found is not None
        assert found["name"] == "Bob"

    def test_get_nonexistent(self, store: UserStore):
        assert store.get("999") is None

    def test_list_users(self, seeded_store: UserStore):
        users = seeded_store.list_all()
        assert len(users) == 3

    def test_delete_user(self, store: UserStore):
        user = store.create("Alice", "alice@example.com")
        assert store.delete(str(user["id"])) is True
        assert store.get(str(user["id"])) is None

    def test_delete_nonexistent(self, store: UserStore):
        assert store.delete("999") is False


# =============================================================================
# 4. Async Tests with Mocking
# =============================================================================

class TestUserService:
    async def test_register_user(self, user_service: UserService, mock_email):
        user = await user_service.register("Alice", "alice@example.com")
        assert user["name"] == "Alice"
        mock_email.send.assert_called_once_with("alice@example.com", "Welcome, Alice!")

    async def test_duplicate_email_rejected(self, user_service: UserService):
        await user_service.register("Alice", "alice@example.com")
        with pytest.raises(ValueError, match="already registered"):
            await user_service.register("Bob", "alice@example.com")


# =============================================================================
# 5. Parametrized Tests
# =============================================================================

@pytest.mark.parametrize("name,email,valid", [
    pytest.param("Alice", "alice@example.com", True, id="valid"),
    pytest.param("", "alice@example.com", False, id="empty-name"),
    pytest.param("Alice", "", False, id="empty-email"),
    pytest.param("Alice", "not-an-email", False, id="invalid-email"),
])
def test_validate_user_input(name: str, email: str, valid: bool):
    """Validate user input: name non-empty, email contains @."""
    is_valid = bool(name) and "@" in email
    assert is_valid == valid


# =============================================================================
# 6. Factory Pattern
# =============================================================================

_factory_counter = 0

def build_user(**overrides) -> dict:
    """Factory function for test data with sensible defaults."""
    global _factory_counter
    _factory_counter += 1
    return {"name": f"User {_factory_counter}",
            "email": f"user{_factory_counter}@example.com", **overrides}


class TestWithFactory:
    def test_custom_name(self, store: UserStore):
        data = build_user(name="Custom")
        user = store.create(**data)
        assert user["name"] == "Custom"

    def test_defaults_are_unique(self, store: UserStore):
        u1 = store.create(**build_user())
        u2 = store.create(**build_user())
        assert u1["email"] != u2["email"]


# =============================================================================
# 7. Monkeypatch and patch Examples
# =============================================================================

import os

def get_config() -> dict:
    return {"api_key": os.environ.get("API_KEY", ""), "debug": os.environ.get("DEBUG", "false")}


def test_monkeypatch_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key-123")
    monkeypatch.setenv("DEBUG", "true")
    config = get_config()
    assert config["api_key"] == "test-key-123"
    assert config["debug"] == "true"


def test_monkeypatch_attribute(monkeypatch):
    store = UserStore()
    monkeypatch.setattr(store, "_counter", 100)
    user = store.create("Alice", "alice@example.com")
    assert user["id"] == 101


# =============================================================================
# Quick Reference: pytest vs Vitest/Jest
# =============================================================================
# Test grouping       | class TestXyz / module       | describe('xyz', () => {})
# Setup/teardown      | @pytest.fixture + yield      | beforeEach / afterEach
# Shared fixtures     | conftest.py                  | Global setup files
# Mock objects        | MagicMock() / AsyncMock()     | vi.fn() / jest.fn()
# Mock modules        | monkeypatch / mock.patch     | vi.mock() / jest.mock()
# Parametrized tests  | @pytest.mark.parametrize     | test.each([...])
# Assertions          | assert x == y                | expect(x).toBe(y)
# Exception testing   | with pytest.raises(...)      | expect(...).toThrow()

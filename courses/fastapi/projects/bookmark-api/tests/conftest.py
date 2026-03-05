"""Pytest configuration for the Bookmark API test suite."""

import pytest


# Use anyio (asyncio) for all async tests automatically.
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

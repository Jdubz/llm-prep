"""Pytest configuration for the task queue service tests."""

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy for all tests."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()

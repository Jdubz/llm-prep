"""
Module 02 — Testing: Exercises (Python-only)
=============================================

Practice core pytest patterns: fixtures, parametrize, mocking.
No web framework dependencies.

Run with:  pytest exercises.py -v
Requires:  pytest, pytest-asyncio
Configure: [tool.pytest.ini_options] asyncio_mode = "auto"

Replace `pass` with your implementation.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# =============================================================================
# THE MODULE UNDER TEST — do NOT modify this section
# =============================================================================

class Calculator:
    """A calculator with history tracking."""
    def __init__(self):
        self.history: list[str] = []

    def add(self, a: float, b: float) -> float:
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result

    def clear_history(self) -> None:
        self.history.clear()


class NotificationService:
    """External notification service — raises if called unoverridden."""
    async def notify(self, user_id: str, message: str) -> dict:
        raise RuntimeError("Real notification service called in tests!")


class OrderProcessor:
    """Processes orders and sends notifications."""
    def __init__(self, notifier: NotificationService):
        self.notifier = notifier
        self.orders: dict[str, dict] = {}
        self._counter = 0

    async def create_order(self, user_id: str, items: list[str]) -> dict:
        if not items:
            raise ValueError("Order must have at least one item")
        self._counter += 1
        order = {"id": self._counter, "user_id": user_id, "items": items, "status": "pending"}
        self.orders[str(self._counter)] = order
        await self.notifier.notify(user_id, f"Order #{self._counter} created")
        return order

    async def complete_order(self, order_id: str) -> dict:
        if order_id not in self.orders:
            raise KeyError(f"Order {order_id} not found")
        self.orders[order_id]["status"] = "completed"
        user_id = self.orders[order_id]["user_id"]
        await self.notifier.notify(user_id, f"Order #{order_id} completed")
        return self.orders[order_id]


# =============================================================================
# SHARED FIXTURES — provided for you
# =============================================================================

@pytest.fixture
def calc() -> Calculator:
    return Calculator()


@pytest.fixture
def mock_notifier() -> AsyncMock:
    notifier = AsyncMock(spec=NotificationService)
    notifier.notify.return_value = {"sent": True}
    return notifier


@pytest.fixture
def processor(mock_notifier) -> OrderProcessor:
    return OrderProcessor(mock_notifier)


# =============================================================================
# EXERCISE 1: Basic fixture usage and assertions
# =============================================================================
# SEE: 01-pytest-fixtures-and-basics.md "Fixtures in Depth"
# SEE: examples.py section 3 (Basic Tests with Fixtures)
#
# Pattern:
#   def test_something(calc: Calculator):
#       result = calc.add(2, 3)
#       assert result == 5

class TestCalculator:
    def test_add(self, calc: Calculator):
        """2 + 3 = 5, history has one entry."""
        # YOUR CODE HERE
        pass

    def test_divide(self, calc: Calculator):
        """10 / 4 = 2.5."""
        # YOUR CODE HERE
        pass

    def test_divide_by_zero(self, calc: Calculator):
        """Dividing by 0 raises ZeroDivisionError."""
        # YOUR CODE HERE (use pytest.raises)
        pass

    def test_history_tracks_operations(self, calc: Calculator):
        """After add(1,2) and divide(10,5), history has 2 entries."""
        # YOUR CODE HERE
        pass

    def test_clear_history(self, calc: Calculator):
        """After operations + clear, history is empty."""
        # YOUR CODE HERE
        pass


# =============================================================================
# EXERCISE 2: Parametrized tests
# =============================================================================
# SEE: 01-pytest-fixtures-and-basics.md "Parametrize — Data-Driven Tests"
# SEE: examples.py section 5 (Parametrized Tests)
#
# Pattern:
#   @pytest.mark.parametrize("input,expected", [
#       pytest.param(1, 2, id="case-name"),
#   ])
#   def test_something(calc, input, expected): ...

@pytest.mark.parametrize("a,b,expected", [
    # TODO: Fill in at least 4 test cases with pytest.param(..., id="..."):
    #   - positive numbers
    #   - negative numbers
    #   - zero
    #   - floating point
])
def test_add_parametrized(calc: Calculator, a: float, b: float, expected: float):
    """Each case should produce the expected sum."""
    # YOUR CODE HERE
    pass


@pytest.mark.parametrize("a,b,expected", [
    # TODO: Fill in test cases for divide:
    #   - 10 / 2 = 5.0
    #   - 7 / 2 = 3.5
    #   - -10 / 5 = -2.0
])
def test_divide_parametrized(calc: Calculator, a: float, b: float, expected: float):
    """Each case should produce the expected quotient."""
    # YOUR CODE HERE
    pass


# =============================================================================
# EXERCISE 3: Async tests with mock verification
# =============================================================================
# SEE: 01-pytest-fixtures-and-basics.md "Async Testing with pytest-asyncio"
# SEE: examples.py section 4 (Async Tests with Mocking)
#
# Pattern:
#   async def test_something(processor, mock_notifier):
#       result = await processor.create_order("user-1", ["item"])
#       mock_notifier.notify.assert_called_once_with("user-1", "...")

class TestOrderProcessor:
    async def test_create_order(self, processor: OrderProcessor, mock_notifier):
        """Create order -> returns order with status "pending", notification sent."""
        # YOUR CODE HERE
        pass

    async def test_create_empty_order_rejected(self, processor: OrderProcessor):
        """Create order with empty items -> raises ValueError."""
        # YOUR CODE HERE
        pass

    async def test_complete_order(self, processor: OrderProcessor, mock_notifier):
        """Create then complete -> status is "completed", 2 notifications sent."""
        # YOUR CODE HERE
        pass

    async def test_complete_nonexistent_order(self, processor: OrderProcessor):
        """Complete order that doesn't exist -> raises KeyError."""
        # YOUR CODE HERE
        pass


# =============================================================================
# EXERCISE 4: Write your own fixture
# =============================================================================
# SEE: examples.py section 2 (Fixtures) and section 6 (Factory Pattern)
#
# Write a fixture that provides a processor pre-loaded with 3 orders.
# Then write tests that use it.

# TODO: Write a @pytest.fixture called `seeded_processor` that:
# 1. Creates an OrderProcessor with a mock notifier
# 2. Creates 3 orders (use await processor.create_order(...))
# 3. Yields the processor
#
# Then write these tests:

class TestSeededProcessor:
    async def test_has_three_orders(self, seeded_processor: OrderProcessor):
        """The seeded processor should have 3 orders."""
        # YOUR CODE HERE
        pass

    async def test_all_orders_pending(self, seeded_processor: OrderProcessor):
        """All 3 orders should have status 'pending'."""
        # YOUR CODE HERE
        pass

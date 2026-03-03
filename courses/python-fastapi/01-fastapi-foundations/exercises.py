"""
FastAPI Foundations Exercises

Skeleton functions with TODOs for you to implement. Each exercise builds
on concepts from the module README and examples.py. Work through them
in order -- later exercises assume familiarity with earlier patterns.

Run tests:  python exercises.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator


# ============================================================================
# EXERCISE 1: Create Pydantic Models with Field Validation
# ============================================================================
#
# READ FIRST: 01-http-routing-and-decorators.md
#   - "Pydantic v2 Models" section for BaseModel, Field(), and schema patterns
#   - "Field Validators and Model Validators" section for @field_validator
#   - "Computed Fields and Custom Types" section for @computed_field
# ALSO SEE: examples.py sections 1 and 5 for complete working models
#
# Build the schema layer for a "Book" resource. This is the FastAPI equivalent
# of defining Zod schemas in Express -- but these also generate OpenAPI docs
# and drive serialization automatically.
#
# The Pattern: Separate schemas for Create, Update, and Response.
# A shared "Base" model holds the common fields. Create inherits from Base
# (same fields, nothing extra). Update makes all fields optional so clients
# can send partial updates. Response adds server-generated fields (id,
# timestamps) and computed fields.
#
# Requirements:
#   - BookBase: shared fields (title, author, isbn, genre, page_count, price)
#   - BookCreate(BookBase): what the client sends to POST /books
#   - BookUpdate: partial update (all fields optional)
#   - BookResponse(BookBase): what the API returns (adds id, created_at, in_stock)
#
# Field constraints (use Field() from pydantic):
#   - title: str, 1-200 characters        -> Field(..., min_length=1, max_length=200)
#   - author: str, 1-100 characters       -> Field(..., min_length=1, max_length=100)
#   - isbn: str, validated via @field_validator (see below)
#   - genre: use Literal["fiction", "non-fiction", "sci-fi", "biography", "technical"]
#   - page_count: int, must be > 0        -> Field(..., gt=0)
#   - price: float, must be >= 0          -> Field(..., ge=0)
#   - BookResponse.in_stock: computed field, True if page_count > 0
#
# How @field_validator works:
#   Validators run AFTER Field() constraints. They receive the already-validated
#   value and can transform or reject it. Three rules:
#     1. Decorate with @field_validator("field_name")
#     2. Must also be @classmethod (Pydantic v2 requirement)
#     3. Must return the value -- forgetting this silently sets the field to None
#
#   Example:
#     @field_validator("isbn")
#     @classmethod
#     def validate_isbn(cls, v: str) -> str:
#         if len(v) != 13 or not v.isdigit():
#             raise ValueError("ISBN must be exactly 13 digits")
#         return v   # <-- always return the value!
#
# How @computed_field works:
#   A read-only field derived from other fields. Not stored, but included in
#   serialization and OpenAPI docs. Use @computed_field above @property:
#
#   @computed_field
#   @property
#   def in_stock(self) -> bool:
#       return self.page_count > 0
#
# Expected behavior:
#   BookCreate(title="Dune", author="Frank Herbert", isbn="9780441013593",
#              genre="sci-fi", page_count=412, price=12.99)
#   # OK -- passes validation
#
#   BookCreate(title="", author="X", isbn="123", genre="romance",
#              page_count=-1, price=12.99)
#   # FAILS -- title too short, isbn wrong length, genre invalid, page_count < 1


class BookBase(BaseModel):
    # TODO: Define all 6 shared fields with appropriate Field() constraints.
    # Use Literal[...] for genre to restrict to valid values.
    # Add a @field_validator for isbn (must be @classmethod, must return v).
    ...


class BookCreate(BookBase):
    # BookCreate inherits everything from BookBase. No extra fields needed
    # for this exercise -- the client sends the same fields that BookBase defines.
    ...


class BookUpdate(BaseModel):
    # TODO: All fields optional using the `field_type | None = None` pattern.
    # This does NOT inherit from BookBase because all fields must be optional.
    # Example: title: str | None = None
    # When consuming: use model_dump(exclude_unset=True) to get only sent fields.
    ...


class BookResponse(BookBase):
    # TODO: Add server-generated fields:
    #   - id: UUID (from uuid module, already imported above)
    #   - created_at: datetime (from datetime module, already imported above)
    #   - in_stock: @computed_field @property, returns True if page_count > 0
    ...


# ============================================================================
# EXERCISE 2: Implement a Dependency That Reads Config from Environment
# ============================================================================
#
# READ FIRST: 02-dependency-injection.md
#   - "What Dependency Injection Is" for the mental model
#   - "Basic Dependencies" for Depends() usage
#   - "Nested (Recursive) Dependencies" for chaining dependencies
#   - "Yield Dependencies" for the yield pattern used in get_book_store
# ALSO SEE: examples.py section 2 for a complete dependency chain
#
# Build a dependency chain: get_app_config -> get_book_store
#
# In Express you'd use dotenv + process.env. FastAPI uses Depends() to inject
# typed, validated configuration into your handlers. Instead of middleware
# attaching values to `req`, dependencies are declared in function signatures
# and resolved automatically.
#
# The chain works like this:
#   1. get_app_config() returns an AppConfig instance (simple return)
#   2. get_book_store() depends on get_app_config via Depends(), uses the
#      config to create a store, and yields it (yield dependency pattern)
#   3. Route handlers depend on get_book_store via Depends() to get the store
#
# Requirements:
#   - AppConfig: a Pydantic BaseModel with:
#       store_name: str (default "My Bookshop")
#       max_inventory: int (default 1000)
#       debug: bool (default False)
#   - get_app_config(): returns an AppConfig instance
#   - InMemoryBookStore: class that holds books in a dict
#       __init__ takes max_inventory: int
#       has methods: add(book) -> dict, get(id) -> dict | None,
#                    list_all() -> list[dict], delete(id) -> bool
#   - get_book_store(config=Depends(get_app_config)): yield dependency that
#       creates an InMemoryBookStore and yields it
#
# Yield dependency pattern:
#   A yield dependency is like a context manager. Code before `yield` is setup,
#   the yielded value is injected into the handler, and code after `yield` is
#   cleanup (runs even if the handler raises an exception).
#
#   async def get_book_store(config: AppConfig = Depends(get_app_config)):
#       store = InMemoryBookStore(max_inventory=config.max_inventory)
#       try:
#           yield store        # <-- this value gets injected into the handler
#       finally:
#           print("cleanup")   # <-- runs after handler completes
#
# Expected behavior:
#   config = get_app_config()
#   assert config.store_name == "My Bookshop"
#   assert config.max_inventory == 1000


class AppConfig(BaseModel):
    # TODO: Define config fields with defaults
    ...


def get_app_config() -> AppConfig:
    """Return application configuration. In production, use pydantic-settings."""
    # TODO: Implement
    ...


class InMemoryBookStore:
    """Simple in-memory store for Book records."""

    def __init__(self, max_inventory: int = 1000) -> None:
        self.max_inventory = max_inventory
        self._books: dict[UUID, dict[str, Any]] = {}

    def add(self, book: BookCreate) -> dict[str, Any]:
        """Add a book and return the full record with id and created_at."""
        # TODO: Implement
        # 1. Check if store is at max_inventory -- raise ValueError if full
        # 2. Create a record dict with id=uuid4(), created_at=now, plus book fields
        # 3. Store it and return the record
        ...

    def get(self, book_id: UUID) -> dict[str, Any] | None:
        """Return a book by ID, or None if not found."""
        # TODO: Implement
        ...

    def list_all(self) -> list[dict[str, Any]]:
        """Return all books."""
        # TODO: Implement
        ...

    def delete(self, book_id: UUID) -> bool:
        """Delete a book. Return True if deleted, False if not found."""
        # TODO: Implement
        ...


async def get_book_store(
    config: AppConfig = Depends(get_app_config),
) -> Any:
    """Yield dependency that provides a book store instance."""
    # TODO: Implement as a yield dependency
    # 1. Create InMemoryBookStore(max_inventory=config.max_inventory)
    # 2. yield it
    # 3. (optional) print a cleanup message in a finally block
    ...


# ============================================================================
# EXERCISE 3: Build a CRUD Router for "Book" with Proper Status Codes
# ============================================================================
#
# READ FIRST: 01-http-routing-and-decorators.md
#   - "Path Operations and Decorators" for routing syntax
#   - "Decorator Parameters" for status_code= and response_model=
#   - "Parameter Extraction" for Path, Query, Body parameters
#   - "Response Models and Status Codes" for status code patterns
#   - "Routers and Application Structure" for APIRouter usage
# ALSO READ: 02-dependency-injection.md
#   - "Basic Dependencies" for injecting the store into handlers
# ALSO SEE: examples.py section 1 for a complete CRUD router with users
#
# Express equivalent: router.post("/", handler), router.get("/:id", handler), etc.
# FastAPI routers are similar but add automatic validation and OpenAPI docs.
#
# How routing works:
#   The @router.post("/", ...) decorator registers a handler for POST requests.
#   The decorator accepts parameters that control behavior:
#     - response_model=BookResponse: tells FastAPI to serialize the return value
#       through this Pydantic model (strips extra fields, generates OpenAPI docs)
#     - status_code=201: sets the default HTTP status code for successful responses
#
# How dependency injection works in handlers:
#   Add a parameter with a default of Depends(some_function):
#     async def create_book(
#         book: BookCreate,                                    # from request body
#         store: InMemoryBookStore = Depends(get_book_store),  # injected dependency
#     ) -> Any:
#
# How error handling works:
#   Raise HTTPException to return an error response:
#     raise HTTPException(status_code=404, detail="Book not found")
#   This immediately stops the handler and returns a JSON error response.
#
# Requirements:
#   - POST   /         -> 201, returns BookResponse
#   - GET    /         -> 200, returns list[BookResponse]
#   - GET    /{book_id} -> 200, returns BookResponse (404 if missing)
#   - DELETE /{book_id} -> 204, no content (404 if missing)
#
# Expected behavior:
#   POST /books with valid body -> 201 + BookResponse JSON
#   GET /books/nonexistent-uuid -> 404
#   DELETE /books/{id} -> 204 with empty body

books_router = APIRouter(prefix="/books", tags=["books"])


@books_router.post(
    "/",
    # TODO: Set response_model and status_code
)
async def create_book(
    book: BookCreate,
    # TODO: Inject the book store dependency
) -> Any:
    """Create a new book."""
    # TODO: Implement
    # 1. Call store.add(book)
    # 2. Return the created record
    ...


@books_router.get("/")
async def list_books(
    # TODO: Inject the book store dependency
    # TODO: Add optional query params for filtering (genre, min_price, max_price)
) -> Any:
    """List all books with optional filtering."""
    # TODO: Implement
    # 1. Get all books from store
    # 2. Apply filters if provided
    # 3. Return the list
    ...


@books_router.get("/{book_id}")
async def get_book(
    book_id: UUID,
    # TODO: Inject the book store dependency
) -> Any:
    """Get a single book by ID."""
    # TODO: Implement
    # 1. Look up book in store
    # 2. If not found, raise HTTPException(status_code=404)
    # 3. Return the book
    ...


@books_router.delete(
    "/{book_id}",
    # TODO: Set status_code to 204
)
async def delete_book(
    book_id: UUID,
    # TODO: Inject the book store dependency
) -> None:
    """Delete a book."""
    # TODO: Implement
    # 1. Try to delete from store
    # 2. If not found, raise HTTPException(status_code=404)
    ...


# ============================================================================
# EXERCISE 4: Create a Custom Exception Handler for Structured Errors
# ============================================================================
#
# READ FIRST: 03-middleware-asgi-and-advanced-patterns.md
#   - "Exception Handlers" section for how to register and write handlers
# ALSO SEE: examples.py section 3 for a complete RFC 9457 implementation
#   including AppError base class, NotFoundError, and both handler functions
#
# FastAPI's default error responses are minimal. Production APIs should return
# consistent, structured error bodies -- ideally RFC 9457 Problem Details.
#
# What is RFC 9457?
#   A standard JSON format for HTTP error responses. Instead of ad-hoc error
#   bodies like {"error": "not found"}, you return a structured object:
#     {
#         "type": "/errors/not-found",      <- machine-readable error category
#         "title": "Book Not Found",        <- human-readable short summary
#         "status": 404,                    <- HTTP status code (redundant but useful)
#         "detail": "Book with id '...'...",<- specific explanation
#         "book_id": "..."                  <- optional extension fields
#     }
#   The Content-Type header should be "application/problem+json".
#
# How exception handlers work:
#   1. Define a custom exception class (inherits from Exception)
#   2. Write an async handler function:
#        async def handler(request: Request, exc: YourError) -> JSONResponse:
#            return JSONResponse(
#                status_code=exc.status_code,
#                content={...},
#                media_type="application/problem+json",
#            )
#   3. Register it with the app:
#        app.add_exception_handler(YourError, handler)
#   4. Now any handler that raises YourError gets this response automatically
#
# Requirements:
#   - BookstoreError: base exception class with fields:
#       status_code (int), error_type (str), title (str), detail (str)
#       Store these in __init__ as self.status_code, self.error_type, etc.
#   - BookNotFoundError(BookstoreError): for 404s, includes book_id
#       __init__(self, book_id: str) -> call super().__init__ with:
#         status_code=404, error_type="/errors/not-found",
#         title="Book Not Found", detail=f"Book with id '{book_id}' does not exist."
#       Also store self.book_id = book_id for the extension field
#   - InventoryFullError(BookstoreError): for 409s when store is at capacity
#   - bookstore_error_handler: exception handler that returns Problem Details JSON
#   - exercise_validation_error_handler: override for RequestValidationError
#
# Expected behavior:
#   raise BookNotFoundError(book_id="abc-123")
#   # -> 404 with Problem Details JSON body


class BookstoreError(Exception):
    """Base error for the bookstore API."""
    # TODO: Define __init__ with status_code, error_type, title, detail
    ...


class BookNotFoundError(BookstoreError):
    """Raised when a book ID doesn't exist."""
    # TODO: Implement __init__(self, book_id: str)
    # Set status_code=404, title="Book Not Found", etc.
    ...


class InventoryFullError(BookstoreError):
    """Raised when the store has reached max capacity."""
    # TODO: Implement __init__(self, max_inventory: int)
    # Set status_code=409, title="Inventory Full", etc.
    ...


async def bookstore_error_handler(request: Request, exc: BookstoreError) -> JSONResponse:
    """Convert BookstoreError to RFC 9457 Problem Details response."""
    # TODO: Implement
    # 1. Build a dict with type, title, status, detail
    # 2. Return JSONResponse with media_type="application/problem+json"
    ...


async def exercise_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic validation errors to RFC 9457 format."""
    # TODO: Implement
    # 1. Build Problem Details dict
    # 2. Include an "errors" list with field, message, type for each error
    # 3. Return JSONResponse with status 422
    ...


# ============================================================================
# EXERCISE 5: Implement Request Validation with Custom Validators
# ============================================================================
#
# READ FIRST: 01-http-routing-and-decorators.md
#   - "Field Validators and Model Validators" for @field_validator and
#     @model_validator syntax and the difference between mode="before"/"after"
#   - "Computed Fields and Custom Types" for Annotated validators
# ALSO SEE: examples.py section 1 (UserCreate.password_strength) for a
#   working @field_validator example
#
# Go beyond Field() constraints. Use @field_validator for custom logic and
# @model_validator for cross-field validation.
#
# Execution order:
#   1. Field() constraints run first (min_length, ge, etc.)
#   2. @field_validator runs next on the already-validated value
#   3. @model_validator(mode="after") runs last on the fully built model
#
# @field_validator rules:
#   - Must be @classmethod
#   - Receives (cls, v) where v is the field value
#   - Must return the value (possibly transformed)
#   - Raise ValueError to reject
#   Example:
#     @field_validator("query")
#     @classmethod
#     def normalize_query(cls, v: str) -> str:
#         # strip + collapse multiple spaces using split/join trick
#         return " ".join(v.split())
#
# @model_validator(mode="after") rules:
#   - Receives self (the fully constructed model instance)
#   - Has access to all fields via self.field_name
#   - Must return self
#   - Raise ValueError to reject
#   Example:
#     @model_validator(mode="after")
#     def check_price_range(self) -> "BookSearchParams":
#         if self.min_price is not None and self.max_price is not None:
#             if self.min_price > self.max_price:
#                 raise ValueError("max_price must be >= min_price")
#         return self
#
# Requirements:
#   - BookSearchParams: model for validating search query parameters
#       query: str = Field(..., min_length=1, max_length=200)
#       min_price: float | None = Field(None, ge=0)
#       max_price: float | None = Field(None, ge=0)
#       genres: list[str] = Field(default_factory=list)
#       sort_by: Literal["title", "price", "date"] = "title"
#       page: int = Field(1, ge=1)
#       per_page: int = Field(20, ge=1, le=100)
#
#   Validators:
#       @field_validator("query"): strip whitespace, collapse multiple spaces
#           Hint: " ".join(v.split()) strips outer whitespace AND collapses
#           inner runs of whitespace into single spaces.
#       @field_validator("genres"): lowercase each genre, reject invalid ones
#           Hint: lowered = [g.lower() for g in v], then check each against
#           VALID_GENRES set. Raise ValueError if any are invalid.
#       @model_validator(mode="after"): if both min_price and max_price are set,
#           ensure min_price <= max_price
#
# Expected behavior:
#   BookSearchParams(query="  hello   world  ", page=1)
#   # -> query becomes "hello world" (stripped + collapsed)
#
#   BookSearchParams(query="test", min_price=50, max_price=10)
#   # -> ValidationError: max_price must be >= min_price


VALID_GENRES = {"fiction", "non-fiction", "sci-fi", "biography", "technical"}


class BookSearchParams(BaseModel):
    # TODO: Define all fields with proper constraints
    ...

    # TODO: Add @field_validator("query") to strip and collapse whitespace

    # TODO: Add @field_validator("genres") to lowercase and validate each genre

    # TODO: Add @model_validator(mode="after") for min_price <= max_price check


# ============================================================================
# APP ASSEMBLY (for manual testing)
# ============================================================================

exercise_app = FastAPI(title="FastAPI Exercises", version="0.1.0")

# TODO (after completing exercises):
# 1. Register bookstore_error_handler for BookstoreError
# 2. Register exercise_validation_error_handler for RequestValidationError
# 3. Include books_router
#
# exercise_app.add_exception_handler(BookstoreError, bookstore_error_handler)
# exercise_app.add_exception_handler(RequestValidationError, exercise_validation_error_handler)
# exercise_app.include_router(books_router, prefix="/api/v1")


# ============================================================================
# TESTS -- Uncomment to verify your implementations
# ============================================================================

# def test_exercise_1():
#     """Test Pydantic models and validation."""
#     print("\n=== EXERCISE 1: Pydantic Models ===")
#
#     # Valid book
#     book = BookCreate(
#         title="Dune",
#         author="Frank Herbert",
#         isbn="9780441013593",
#         genre="sci-fi",
#         page_count=412,
#         price=12.99,
#     )
#     print(f"Valid book: {book.title} by {book.author}")
#
#     # Test validation errors
#     import pydantic
#     try:
#         BookCreate(
#             title="",  # too short
#             author="X",
#             isbn="123",  # too short
#             genre="romance",  # invalid
#             page_count=-1,  # must be > 0
#             price=12.99,
#         )
#         print("ERROR: Should have raised ValidationError")
#     except pydantic.ValidationError as e:
#         print(f"Caught {len(e.errors())} validation errors (expected)")
#
#     # Test BookUpdate partial
#     update = BookUpdate(title="Dune Messiah")
#     dumped = update.model_dump(exclude_unset=True)
#     assert "author" not in dumped, "Unset fields should be excluded"
#     print(f"Partial update: {dumped}")
#
#     # Test BookResponse computed field
#     response = BookResponse(
#         id=uuid4(),
#         created_at=datetime.now(),
#         title="Dune",
#         author="Frank Herbert",
#         isbn="9780441013593",
#         genre="sci-fi",
#         page_count=412,
#         price=12.99,
#     )
#     assert response.in_stock is True, "in_stock should be True when page_count > 0"
#     print(f"Response with computed field: in_stock={response.in_stock}")
#     print("EXERCISE 1: PASSED")
#
#
# def test_exercise_2():
#     """Test dependency functions."""
#     print("\n=== EXERCISE 2: Dependencies ===")
#
#     config = get_app_config()
#     assert config.store_name == "My Bookshop"
#     assert config.max_inventory == 1000
#     print(f"Config: {config.model_dump()}")
#
#     store = InMemoryBookStore(max_inventory=2)
#
#     book_data = BookCreate(
#         title="Test Book",
#         author="Test Author",
#         isbn="1234567890123",
#         genre="fiction",
#         page_count=100,
#         price=9.99,
#     )
#
#     record = store.add(book_data)
#     assert record is not None, "add() should return a record"
#     assert "id" in record, "Record should have an id"
#     print(f"Added book: {record['title']} (id: {record['id']})")
#
#     fetched = store.get(record["id"])
#     assert fetched is not None, "get() should find the book"
#     print(f"Fetched: {fetched['title']}")
#
#     all_books = store.list_all()
#     assert len(all_books) == 1
#     print(f"Listed {len(all_books)} book(s)")
#
#     deleted = store.delete(record["id"])
#     assert deleted is True, "delete() should return True"
#     assert store.get(record["id"]) is None, "Book should be gone"
#     print("Delete confirmed")
#     print("EXERCISE 2: PASSED")
#
#
# def test_exercise_3():
#     """Test the CRUD router with FastAPI's test client."""
#     print("\n=== EXERCISE 3: CRUD Router ===")
#     from fastapi.testclient import TestClient
#
#     test_app = FastAPI()
#     test_app.include_router(books_router, prefix="/api/v1")
#
#     client = TestClient(test_app)
#
#     # Create
#     resp = client.post("/api/v1/books/", json={
#         "title": "Test Book",
#         "author": "Test Author",
#         "isbn": "1234567890123",
#         "genre": "fiction",
#         "page_count": 200,
#         "price": 14.99,
#     })
#     assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
#     book = resp.json()
#     book_id = book["id"]
#     print(f"Created: {book['title']} (id: {book_id})")
#
#     # Read
#     resp = client.get(f"/api/v1/books/{book_id}")
#     assert resp.status_code == 200
#     print(f"Fetched: {resp.json()['title']}")
#
#     # List
#     resp = client.get("/api/v1/books/")
#     assert resp.status_code == 200
#     assert len(resp.json()) >= 1
#     print(f"Listed {len(resp.json())} book(s)")
#
#     # Delete
#     resp = client.delete(f"/api/v1/books/{book_id}")
#     assert resp.status_code == 204
#     print("Deleted successfully")
#
#     # 404 after delete
#     resp = client.get(f"/api/v1/books/{book_id}")
#     assert resp.status_code == 404
#     print("Confirmed 404 after delete")
#     print("EXERCISE 3: PASSED")
#
#
# def test_exercise_4():
#     """Test custom exception handlers."""
#     print("\n=== EXERCISE 4: Exception Handlers ===")
#
#     err = BookNotFoundError(book_id="abc-123")
#     assert err.status_code == 404
#     assert "abc-123" in err.detail
#     print(f"BookNotFoundError: {err.detail}")
#
#     err2 = InventoryFullError(max_inventory=100)
#     assert err2.status_code == 409
#     print(f"InventoryFullError: {err2.detail}")
#
#     # Test the handler function directly
#     import asyncio
#     from unittest.mock import MagicMock
#
#     mock_request = MagicMock()
#     response = asyncio.get_event_loop().run_until_complete(
#         bookstore_error_handler(mock_request, err)
#     )
#     assert response.status_code == 404
#     assert response.media_type == "application/problem+json"
#     print(f"Handler returned {response.status_code} with correct media type")
#     print("EXERCISE 4: PASSED")
#
#
# def test_exercise_5():
#     """Test custom validators."""
#     print("\n=== EXERCISE 5: Custom Validators ===")
#     import pydantic
#
#     # Whitespace normalization
#     params = BookSearchParams(query="  hello   world  ")
#     assert params.query == "hello world", f"Expected 'hello world', got '{params.query}'"
#     print(f"Query normalized: '{params.query}'")
#
#     # Genre lowercasing
#     params2 = BookSearchParams(query="test", genres=["SCI-FI", "Fiction"])
#     assert params2.genres == ["sci-fi", "fiction"]
#     print(f"Genres lowercased: {params2.genres}")
#
#     # Invalid genre
#     try:
#         BookSearchParams(query="test", genres=["romance"])
#         print("ERROR: Should have raised ValidationError for invalid genre")
#     except pydantic.ValidationError:
#         print("Caught invalid genre error (expected)")
#
#     # Price range validation
#     try:
#         BookSearchParams(query="test", min_price=50.0, max_price=10.0)
#         print("ERROR: Should have raised ValidationError for price range")
#     except pydantic.ValidationError:
#         print("Caught price range error (expected)")
#
#     # Valid price range
#     params3 = BookSearchParams(query="test", min_price=10.0, max_price=50.0)
#     print(f"Valid price range: {params3.min_price}-{params3.max_price}")
#     print("EXERCISE 5: PASSED")
#
#
# if __name__ == "__main__":
#     test_exercise_1()
#     test_exercise_2()
#     test_exercise_3()
#     test_exercise_4()
#     test_exercise_5()
#     print("\n=== ALL EXERCISES PASSED ===")


"""
LEARNING OBJECTIVES CHECKLIST

After completing these exercises, you should be comfortable with:

Pydantic Models:
- [ ] Defining BaseModel subclasses with Field() constraints
- [ ] Separating Create / Update / Response schemas
- [ ] Using @field_validator for custom per-field logic
- [ ] Using @model_validator for cross-field logic
- [ ] computed_field for derived values
- [ ] model_dump(exclude_unset=True) for partial updates

Dependency Injection:
- [ ] Writing simple Depends() functions
- [ ] Chaining dependencies (config -> store)
- [ ] Yield dependencies with cleanup
- [ ] Injecting dependencies into route handlers

CRUD Routers:
- [ ] APIRouter with prefix and tags
- [ ] Correct HTTP status codes (201, 204, 404)
- [ ] response_model for output serialization
- [ ] Path parameters with type validation (UUID)
- [ ] Query parameters with defaults and constraints

Exception Handling:
- [ ] Custom exception classes with structured data
- [ ] Registering exception handlers on the app
- [ ] RFC 9457 Problem Details response format
- [ ] Overriding default validation error responses

Validation Patterns:
- [ ] Field-level validators that transform input
- [ ] Model-level validators for cross-field rules
- [ ] Combining Field() constraints with custom validators
- [ ] Descriptive ValueError messages

These are the core FastAPI skills for building production APIs!
"""

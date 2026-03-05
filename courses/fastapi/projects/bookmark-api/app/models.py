"""
Pydantic models for the Bookmark API.

Covers course concepts from:
- Module 02: Pydantic models, validation, serialization
- Module 03: Request/response models, field constraints
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


# ---------------------------------------------------------------------------
# User models
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Payload for POST /register."""
    email: str = Field(..., min_length=5, max_length=120, examples=["alice@example.com"])
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Public-facing user representation (never exposes password)."""
    id: str
    email: str
    username: str


class UserInDB(BaseModel):
    """Internal user record stored in the in-memory database."""
    id: str
    email: str
    username: str
    hashed_password: str


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """Payload for POST /login."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token returned after successful login."""
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Bookmark models
# ---------------------------------------------------------------------------

class BookmarkCreate(BaseModel):
    """Payload for POST /bookmarks."""
    url: str = Field(..., min_length=1, max_length=2048, examples=["https://fastapi.tiangolo.com"])
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class BookmarkUpdate(BaseModel):
    """Payload for PUT /bookmarks/{id}.  All fields optional."""
    url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[list[str]] = Field(default=None, max_length=20)


class BookmarkResponse(BaseModel):
    """Public-facing bookmark representation."""
    id: str
    url: str
    title: str
    description: str
    tags: list[str]
    created_at: datetime
    user_id: str


class BookmarkInDB(BaseModel):
    """Internal bookmark record stored in the in-memory database."""
    id: str
    url: str
    title: str
    description: str
    tags: list[str]
    created_at: datetime
    user_id: str


class PaginatedBookmarks(BaseModel):
    """Wrapper for paginated bookmark list responses."""
    items: list[BookmarkResponse]
    total: int
    page: int
    size: int

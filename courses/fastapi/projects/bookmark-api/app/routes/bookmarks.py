"""
Bookmark CRUD routes with ownership enforcement.

Covers course concepts from:
- Module 01: Path operations, query parameters, status codes
- Module 02: Request/response models
- Module 03: Path parameters, query parameter validation, pagination
- Module 04: Dependency injection (auth)
- Module 06: Async route handlers
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import get_current_user
from app.models import (
    BookmarkCreate,
    BookmarkInDB,
    BookmarkResponse,
    BookmarkUpdate,
    PaginatedBookmarks,
    UserInDB,
)
from app.storage import storage

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_response(b: BookmarkInDB) -> BookmarkResponse:
    return BookmarkResponse(**b.model_dump())


async def _get_owned_bookmark(
    bookmark_id: str, user: UserInDB
) -> BookmarkInDB:
    """Fetch a bookmark and verify the current user owns it."""
    bookmark = await storage.get_bookmark_by_id(bookmark_id)
    if bookmark is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found",
        )
    if bookmark.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this bookmark",
        )
    return bookmark


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=BookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bookmark",
)
async def create_bookmark(
    body: BookmarkCreate,
    user: Annotated[UserInDB, Depends(get_current_user)],
) -> BookmarkResponse:
    bookmark = BookmarkInDB(
        id=str(uuid.uuid4()),
        url=body.url,
        title=body.title,
        description=body.description,
        tags=body.tags,
        created_at=datetime.now(timezone.utc),
        user_id=user.id,
    )
    await storage.add_bookmark(bookmark)
    return _to_response(bookmark)


@router.get(
    "",
    response_model=PaginatedBookmarks,
    summary="List bookmarks with optional filtering and pagination",
)
async def list_bookmarks(
    user: Annotated[UserInDB, Depends(get_current_user)],
    tag: Optional[str] = Query(default=None, description="Filter by tag"),
    search: Optional[str] = Query(default=None, description="Search title/description"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginatedBookmarks:
    items, total = await storage.list_bookmarks(
        user_id=user.id, tag=tag, search=search, page=page, size=size
    )
    return PaginatedBookmarks(
        items=[_to_response(b) for b in items],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/{bookmark_id}",
    response_model=BookmarkResponse,
    summary="Get a single bookmark by ID",
)
async def get_bookmark(
    bookmark_id: str,
    user: Annotated[UserInDB, Depends(get_current_user)],
) -> BookmarkResponse:
    bookmark = await _get_owned_bookmark(bookmark_id, user)
    return _to_response(bookmark)


@router.put(
    "/{bookmark_id}",
    response_model=BookmarkResponse,
    summary="Update a bookmark (owner only)",
)
async def update_bookmark(
    bookmark_id: str,
    body: BookmarkUpdate,
    user: Annotated[UserInDB, Depends(get_current_user)],
) -> BookmarkResponse:
    # Verify ownership first
    await _get_owned_bookmark(bookmark_id, user)

    updates = body.model_dump(exclude_unset=True)
    updated = await storage.update_bookmark(bookmark_id, updates)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found",
        )
    return _to_response(updated)


@router.delete(
    "/{bookmark_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a bookmark (owner only)",
)
async def delete_bookmark(
    bookmark_id: str,
    user: Annotated[UserInDB, Depends(get_current_user)],
) -> None:
    await _get_owned_bookmark(bookmark_id, user)
    await storage.delete_bookmark(bookmark_id)

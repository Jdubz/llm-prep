"""
In-memory storage layer that simulates a database.

Uses asyncio.Lock to ensure thread-safety for concurrent requests.
This covers course concepts from Module 06 (async patterns, concurrency).
"""

import asyncio
from typing import Optional

from app.models import BookmarkInDB, UserInDB


class InMemoryStorage:
    """Dict-backed async-safe storage for users and bookmarks."""

    def __init__(self) -> None:
        self._users: dict[str, UserInDB] = {}          # keyed by user id
        self._bookmarks: dict[str, BookmarkInDB] = {}   # keyed by bookmark id
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------

    async def add_user(self, user: UserInDB) -> UserInDB:
        async with self._lock:
            self._users[user.id] = user
            return user

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        async with self._lock:
            return self._users.get(user_id)

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        async with self._lock:
            for user in self._users.values():
                if user.username == username:
                    return user
            return None

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        async with self._lock:
            for user in self._users.values():
                if user.email == email:
                    return user
            return None

    # ------------------------------------------------------------------
    # Bookmark operations
    # ------------------------------------------------------------------

    async def add_bookmark(self, bookmark: BookmarkInDB) -> BookmarkInDB:
        async with self._lock:
            self._bookmarks[bookmark.id] = bookmark
            return bookmark

    async def get_bookmark_by_id(self, bookmark_id: str) -> Optional[BookmarkInDB]:
        async with self._lock:
            return self._bookmarks.get(bookmark_id)

    async def list_bookmarks(
        self,
        user_id: str,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BookmarkInDB], int]:
        """Return a page of bookmarks for a user, with optional filters.

        Returns (items, total_matching_count).
        """
        async with self._lock:
            results = [
                b for b in self._bookmarks.values() if b.user_id == user_id
            ]

            # Filter by tag (case-insensitive)
            if tag:
                tag_lower = tag.lower()
                results = [
                    b for b in results
                    if any(t.lower() == tag_lower for t in b.tags)
                ]

            # Filter by search query (matches title or description)
            if search:
                search_lower = search.lower()
                results = [
                    b for b in results
                    if search_lower in b.title.lower()
                    or search_lower in b.description.lower()
                ]

            # Sort newest first
            results.sort(key=lambda b: b.created_at, reverse=True)

            total = len(results)
            start = (page - 1) * size
            end = start + size
            return results[start:end], total

    async def update_bookmark(
        self, bookmark_id: str, updates: dict
    ) -> Optional[BookmarkInDB]:
        async with self._lock:
            existing = self._bookmarks.get(bookmark_id)
            if existing is None:
                return None
            updated_data = existing.model_dump()
            updated_data.update(
                {k: v for k, v in updates.items() if v is not None}
            )
            updated = BookmarkInDB(**updated_data)
            self._bookmarks[bookmark_id] = updated
            return updated

    async def delete_bookmark(self, bookmark_id: str) -> bool:
        async with self._lock:
            if bookmark_id in self._bookmarks:
                del self._bookmarks[bookmark_id]
                return True
            return False

    async def clear(self) -> None:
        """Reset all data (useful for testing)."""
        async with self._lock:
            self._users.clear()
            self._bookmarks.clear()


# Singleton instance used by the rest of the application.
storage = InMemoryStorage()

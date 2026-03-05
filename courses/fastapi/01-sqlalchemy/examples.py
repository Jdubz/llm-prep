"""
SQLAlchemy 2.0 Examples

Complete, runnable patterns for SQLAlchemy 2.0 with both async and sync engines.
Uses SQLite + aiosqlite for portability -- swap to PostgreSQL + asyncpg for production.
All models use the modern Mapped[] / mapped_column() declarative style.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    joinedload,
    mapped_column,
    relationship,
    selectinload,
    sessionmaker,
)


# ---------------------------------------------------------------------------
# 1. Base and Mixin Definitions
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Declarative base for all models. Replaces the legacy declarative_base()."""
    pass


class TimestampMixin:
    """Mixin that adds created_at / updated_at columns to any model."""
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(),
    )


# ---------------------------------------------------------------------------
# 2. Model Definitions with Relationships
# ---------------------------------------------------------------------------

# Many-to-many association table: Post <-> Tag
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # One-to-many: User -> Post
    posts: Mapped[list[Post]] = relationship(
        back_populates="author", cascade="all, delete-orphan",
    )

    # --- Hybrid property: works in Python AND in SQL WHERE clauses ---
    @hybrid_property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @full_name.expression
    @classmethod
    def full_name(cls):
        # Generates: first_name || ' ' || last_name in SQL
        return cls.first_name + " " + cls.last_name

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class Post(TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(default=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    # Many-to-one: Post -> User
    author: Mapped[User] = relationship(back_populates="posts")
    # One-to-many: Post -> Comment
    comments: Mapped[list[Comment]] = relationship(
        back_populates="post", cascade="all, delete-orphan",
    )
    # Many-to-many: Post <-> Tag
    tags: Mapped[list[Tag]] = relationship(
        secondary=post_tags, back_populates="posts",
    )

    def __repr__(self) -> str:
        return f"<Post id={self.id} title={self.title!r}>"


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str] = mapped_column(Text)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    post: Mapped[Post] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return f"<Comment id={self.id}>"


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    posts: Mapped[list[Post]] = relationship(
        secondary=post_tags, back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# 3. Engine Setup (Async + Sync)
# ---------------------------------------------------------------------------

ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./example.db"
SYNC_DATABASE_URL = "sqlite:///./example.db"

# -- Async engine (primary for FastAPI) --
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,  # Set True to log all generated SQL
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False,
)

# -- Sync engine (useful for scripts, tests, Alembic) --
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# 4. Session-as-FastAPI-Dependency Pattern
# ---------------------------------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession for the duration of a single request.
    Commits on success, rolls back on exception, always closes.

    Usage in a FastAPI route:
        @router.get("/users")
        async def list_users(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_session():
    """Synchronous equivalent for scripts and tests."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 5. Generic Repository Pattern
# ---------------------------------------------------------------------------

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    """
    Generic CRUD repository. Encapsulates common query logic so route handlers
    stay thin. In production, subclass for model-specific queries.
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def list_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[ModelT]:
        stmt = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()  # Generates ID without committing
        return instance

    async def update(self, id: int, **kwargs: Any) -> ModelT | None:
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, id: int) -> bool:
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True


class UserRepository(Repository[User]):
    """User-specific queries built on top of the generic repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(self, limit: int = 50) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.is_active == True)  # noqa: E712
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


# ---------------------------------------------------------------------------
# 6. Query Patterns
# ---------------------------------------------------------------------------

# -- 6a. Offset-based pagination --

async def paginate_offset(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """
    Classic offset pagination. Simple but degrades on large offsets because the
    DB must skip N rows. Fine for admin dashboards; avoid for infinite scroll.
    """
    count_result = await session.execute(select(func.count(User.id)))
    total = count_result.scalar_one()

    stmt = (
        select(User)
        .order_by(User.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.execute(stmt)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


# -- 6b. Cursor-based pagination --

async def paginate_cursor(
    session: AsyncSession,
    cursor: int | None = None,
    size: int = 20,
) -> dict[str, Any]:
    """
    Cursor-based pagination using the ID as a stable cursor. Performs well at
    any depth because it uses a WHERE clause instead of OFFSET.

    The cursor is the last-seen ID; pass it back to get the next page.
    """
    stmt = select(User).order_by(User.id).limit(size + 1)  # Fetch one extra

    if cursor is not None:
        stmt = stmt.where(User.id > cursor)

    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    has_next = len(rows) > size
    items = rows[:size]
    next_cursor = items[-1].id if items and has_next else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_next": has_next,
    }


# -- 6c. Joins and eager loading --

async def get_user_with_posts_and_comments(
    session: AsyncSession, user_id: int,
) -> User | None:
    """
    Load a user with their posts, each post's comments, and comment authors.
    Uses selectinload for collections, joinedload for single objects.
    """
    stmt = (
        select(User)
        .options(
            selectinload(User.posts)
            .selectinload(Post.comments)
            .joinedload(Comment.author),
        )
        .where(User.id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# -- 6d. Aggregation with joins --

async def get_user_post_counts(session: AsyncSession) -> list[dict[str, Any]]:
    """
    Aggregate query: user names with their post counts, sorted by most prolific.
    Demonstrates outerjoin + group_by + having.
    """
    stmt = (
        select(User.first_name, User.last_name, func.count(Post.id).label("post_count"))
        .outerjoin(Post, Post.author_id == User.id)
        .group_by(User.id, User.first_name, User.last_name)
        .having(func.count(Post.id) > 0)
        .order_by(func.count(Post.id).desc())
    )
    result = await session.execute(stmt)
    return [
        {"first_name": row.first_name, "last_name": row.last_name, "post_count": row.post_count}
        for row in result.all()
    ]


# -- 6e. Filtering with the hybrid property --

async def search_users_by_full_name(
    session: AsyncSession, name: str,
) -> Sequence[User]:
    """
    Uses the hybrid_property expression so the concatenation happens in SQL,
    not in Python. Generates: WHERE first_name || ' ' || last_name LIKE '%...%'
    """
    stmt = select(User).where(User.full_name.contains(name))
    result = await session.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# 7. Transaction with Savepoint
# ---------------------------------------------------------------------------

async def create_post_with_tags(
    session: AsyncSession,
    author_id: int,
    title: str,
    content: str,
    tag_names: list[str],
) -> Post:
    """
    Creates a post and associates tags in a savepoint. If tag creation fails
    (e.g. duplicate), the savepoint rolls back but the outer transaction
    survives -- the post is still created without tags.
    """
    post = Post(title=title, content=content, author_id=author_id, is_published=True)
    session.add(post)
    await session.flush()  # Need post.id before associating tags

    try:
        async with session.begin_nested():  # SAVEPOINT
            for name in tag_names:
                # Get existing tag or create new one
                tag_result = await session.execute(
                    select(Tag).where(Tag.name == name)
                )
                tag = tag_result.scalar_one_or_none()
                if tag is None:
                    tag = Tag(name=name)
                    session.add(tag)
                    await session.flush()
                post.tags.append(tag)
            await session.flush()
    except Exception as exc:
        # Savepoint rolled back; post survives without tags
        print(f"Tag association failed (savepoint rolled back): {exc}")

    return post


# ---------------------------------------------------------------------------
# 8. Bulk Insert with Core API
# ---------------------------------------------------------------------------

async def bulk_insert_users(
    session: AsyncSession,
    users_data: list[dict[str, Any]],
) -> None:
    """
    Bulk insert using the Core insert().values() API.
    Much faster than session.add() in a loop because it generates a single
    INSERT statement with multiple value sets.
    """
    if not users_data:
        return
    await session.execute(insert(User).values(users_data))
    await session.flush()


# ---------------------------------------------------------------------------
# 9. Synchronous Equivalents (for scripts, tests, Alembic)
# ---------------------------------------------------------------------------

def sync_get_user_by_email(session: Session, email: str) -> User | None:
    """Synchronous version -- lazy loading works fine here."""
    stmt = select(User).where(User.email == email)
    return session.execute(stmt).scalar_one_or_none()


def sync_paginate(session: Session, page: int = 1, size: int = 20) -> list[User]:
    stmt = select(User).order_by(User.id).offset((page - 1) * size).limit(size)
    return list(session.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# 10. Runnable Demo
# ---------------------------------------------------------------------------

async def demo() -> None:
    """End-to-end demo: create tables, seed data, run every query pattern."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # -- Seed data --
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await bulk_insert_users(session, [
                {"email": "alice@example.com", "first_name": "Alice", "last_name": "Smith", "is_active": True},
                {"email": "bob@example.com", "first_name": "Bob", "last_name": "Jones", "is_active": True},
                {"email": "carol@example.com", "first_name": "Carol", "last_name": "Lee", "is_active": False},
            ])
            alice = (await session.execute(select(User).where(User.email == "alice@example.com"))).scalar_one()
            bob = (await session.execute(select(User).where(User.email == "bob@example.com"))).scalar_one()
            posts = [
                Post(title="Intro to SQLAlchemy", content="Great ORM...", author=alice, is_published=True),
                Post(title="Async Patterns", content="Using async...", author=alice, is_published=True),
                Post(title="Testing Tips", content="How to test...", author=bob, is_published=True),
            ]
            session.add_all(posts)
            await session.flush()
            session.add(Comment(body="Great article!", post=posts[0], author_id=bob.id))

    # -- Run queries --
    async with AsyncSessionLocal() as session:
        page = await paginate_offset(session, page=1, size=2)
        print(f"Offset page 1: {page['items']} (total={page['total']})")

        cur = await paginate_cursor(session, cursor=None, size=2)
        print(f"Cursor page:   {cur['items']} (has_next={cur['has_next']})")

        user = await get_user_with_posts_and_comments(session, user_id=1)
        if user:
            print(f"Eager loaded:  {user} with {len(user.posts)} posts")

        counts = await get_user_post_counts(session)
        print(f"Post counts:   {counts}")

        found = await search_users_by_full_name(session, "Alice")
        print(f"Hybrid search: {[u.full_name for u in found]}")

        repo = UserRepository(session)
        print(f"Repo email:    {await repo.get_by_email('alice@example.com')}")

    # -- Savepoint demo --
    async with AsyncSessionLocal() as session:
        async with session.begin():
            post = await create_post_with_tags(session, 1, "Tagged", "Content", ["python", "async"])
            print(f"Savepoint:     {post} tags={[t.name for t in post.tags]}")

    # Cleanup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(demo())

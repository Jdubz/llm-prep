# Module 03 Cheat Sheet: SQLAlchemy 2.0

## Model Template

```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    bio: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)

    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")
```

## Relationship Patterns

```python
# One-to-Many
class Post(Base):
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    author: Mapped[User] = relationship(back_populates="posts")

# One-to-One
class Profile(Base):
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    user: Mapped[User] = relationship(back_populates="profile", uselist=False)

# Many-to-Many (implicit join table)
post_tags = Table("post_tags", Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)
class Post(Base):
    tags: Mapped[list[Tag]] = relationship(secondary=post_tags, back_populates="posts")
```

## Engine & Session Setup

```python
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost:5432/db",
    pool_size=20, max_overflow=10, pool_pre_ping=True,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

## Session Lifecycle (FastAPI Dependency)

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

## Eager Loading (Required in Async)

```python
from sqlalchemy.orm import selectinload, joinedload

# Collections: selectinload (separate IN query)
stmt = select(User).options(selectinload(User.posts))

# Single objects: joinedload (LEFT JOIN)
stmt = select(Post).options(joinedload(Post.author))

# Nested: chain them
stmt = select(User).options(selectinload(User.posts).joinedload(Post.comments))
```

## Query Patterns Quick Reference

```python
from sqlalchemy import select, insert, update, delete, func, and_, or_

# GET by PK
user = await session.get(User, user_id)

# SELECT with filters
stmt = select(User).where(and_(User.is_active == True, User.role == "admin"))
result = await session.execute(stmt)
users = result.scalars().all()

# SELECT one or None
user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()

# INSERT
session.add(User(email="a@b.com", name="A"))
await session.flush()

# BULK INSERT
await session.execute(insert(User), [{"email": "a@b.com", "name": "A"}, ...])

# UPDATE
await session.execute(update(User).where(User.id == uid).values(name="New"))

# DELETE
await session.execute(delete(User).where(User.id == uid))

# JOIN + aggregate
stmt = (select(User.name, func.count(Post.id))
        .join(Post).group_by(User.name).having(func.count(Post.id) > 5))

# Pagination
stmt = select(User).order_by(User.created_at.desc()).offset(20).limit(10)
```

## Alembic Commands

```bash
alembic init -t async alembic          # Initialize async project
alembic revision --autogenerate -m ""  # Generate migration from models
alembic revision -m ""                 # Empty migration for manual SQL
alembic upgrade head                   # Apply all migrations
alembic downgrade -1                   # Rollback one migration
alembic current                        # Show current revision
alembic history --verbose              # Full migration history
alembic heads                          # Show branch heads
alembic merge -m "merge" rev1 rev2     # Merge divergent branches
```

## ORM Comparison Table

| Feature | SQLAlchemy 2.0 | Prisma | TypeORM | Drizzle |
|---------|---------------|--------|---------|---------|
| Language | Python | TypeScript | TypeScript | TypeScript |
| Paradigm | Data Mapper + Active Record | Query Builder | Active Record | Query Builder |
| Async | Full (asyncpg) | Full (native) | Partial (experimental) | Full |
| Identity Map | Yes | No | No | No |
| Unit of Work | Yes | No (explicit txn) | Yes (basic) | No |
| Migration Tool | Alembic | prisma migrate | TypeORM CLI | drizzle-kit |
| Raw SQL | text() | $queryRaw | .query() | sql`` |
| Schema Source | Python classes | .prisma file | Decorators | pgTable() |
| Connection Pool | Built-in | Built-in | Built-in | External (pg) |
| Maturity | 2006+ | 2019+ | 2016+ | 2022+ |
| Learning Curve | Steep | Low | Medium | Low |
| Complex Queries | Excellent | Limited | Good | Good |

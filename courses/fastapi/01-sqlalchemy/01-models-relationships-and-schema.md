# 01 – Models, Relationships, and Schema

## Overview

This module covers SQLAlchemy 2.0 with async support, the dominant Python ORM for production
applications. Coming from Prisma, TypeORM, or Drizzle, you'll find SQLAlchemy more verbose but
significantly more powerful — fine-grained control over SQL generation, connection management,
and complex query composition that TypeScript ORMs don't match.

The mental model shift: Prisma and Drizzle are query builders with schema management. TypeORM is
closer but lacks SQLAlchemy's maturity. SQLAlchemy is a full database toolkit with an optional
ORM layer on top — you can mix raw SQL, Core query builder, and ORM in the same application.

```bash
pip install "sqlalchemy[asyncio]>=2.0" asyncpg alembic
```

---

## SQLAlchemy 2.0: The Modern API

SQLAlchemy 2.0 introduced a new API style. If you see `session.query(User)`, that's legacy 1.x.
The modern style uses `select()` statements.

### ORM Comparison

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

### Comparison with TypeScript ORM Concepts

| Concept | Prisma | TypeORM | Drizzle | SQLAlchemy |
|---------|--------|---------|---------|------------|
| Connection | `PrismaClient()` | `DataSource` | `drizzle(pool)` | `create_async_engine()` |
| Session | Implicit per query | `EntityManager` | None (stateless) | `AsyncSession` |
| Schema | `.prisma` file | Decorators | `pgTable()` | `DeclarativeBase` |
| Migrations | `prisma migrate` | TypeORM CLI | `drizzle-kit` | Alembic |
| Query style | Method chaining | QueryBuilder | SQL-like builder | `select()` statements |
| Raw SQL | `$queryRaw` | `.query()` | `sql\`...\`` | `text()` |

---

## Declarative Mapping with `mapped_column`

```python
# app/models/base.py
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(),
    )
```

```python
# app/models/user.py
from __future__ import annotations
import uuid
from typing import Optional
from sqlalchemy import String, Text, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")
    profile: Mapped[Optional[Profile]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan",
    )
```

Key differences from TypeORM: `Mapped[str]` replaces `@Column({ type: 'varchar' })` — the
Python type IS the column type. `Optional[str]` means `nullable=True`. `relationship()` replaces
`@OneToMany()` / `@ManyToOne()` decorators.

---

## Relationship Patterns

### One-to-Many

```python
class Post(TimestampMixin, Base):
    __tablename__ = "posts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    author: Mapped[User] = relationship(back_populates="posts")
    comments: Mapped[list[Comment]] = relationship(
        back_populates="post", cascade="all, delete-orphan",
    )
```

### One-to-One

```python
class Profile(Base):
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    user: Mapped[User] = relationship(back_populates="profile", uselist=False)
```

### Many-to-Many

```python
# Association table -- equivalent to Prisma's implicit many-to-many
from sqlalchemy import Table, Column
post_tags = Table("post_tags", Base.metadata,
    Column("post_id", ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    posts: Mapped[list[Post]] = relationship(secondary=post_tags, back_populates="tags")

# On Post model:
#   tags: Mapped[list[Tag]] = relationship(secondary=post_tags, back_populates="posts")
```

### Many-to-Many with Extra Fields (Association Object)

When you need data on the join itself (like Prisma's explicit many-to-many):

```python
class PostAuthor(TimestampMixin, Base):
    __tablename__ = "post_authors"
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))  # "author", "editor", "reviewer"
    post: Mapped[Post] = relationship(back_populates="author_associations")
    user: Mapped[User] = relationship(back_populates="post_associations")
```

---

## Lazy vs Eager Loading

The biggest "gotcha" for async SQLAlchemy: in sync mode, accessing `user.posts` triggers a lazy
load. In async mode, this **raises MissingGreenlet**. You must explicitly eager-load.

```python
from sqlalchemy.orm import selectinload, joinedload

# selectinload: separate SELECT ... WHERE id IN (...) -- best for collections
stmt = select(User).options(selectinload(User.posts)).where(User.id == user_id)

# joinedload: LEFT JOIN in same query -- best for single objects (many-to-one)
stmt = select(User).options(joinedload(User.profile)).where(User.id == user_id)

# Nested: load user -> posts -> comments (3 levels)
stmt = select(User).options(
    selectinload(User.posts).selectinload(Post.comments).joinedload(Comment.author)
).where(User.id == user_id)

# Chained for single nested level
stmt = select(User).options(selectinload(User.posts).joinedload(Post.comments))
```

| Strategy | SQL Generated | Best For |
|----------|--------------|----------|
| `selectinload` | Separate `SELECT ... IN (...)` | Collections (one-to-many) |
| `joinedload` | `LEFT JOIN` in same query | Single objects (many-to-one) |
| `subqueryload` | Separate subquery | Legacy; prefer `selectinload` |
| `lazyload` | On access (sync only) | Never use in async |

---

## Hybrid Properties

Computed properties that work both in Python and in SQL queries:

```python
from sqlalchemy.ext.hybrid import hybrid_property

class User(Base):
    __tablename__ = "users"
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))

    @hybrid_property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @full_name.expression
    @classmethod
    def full_name(cls):
        return cls.first_name + " " + cls.last_name

# Works in queries: generates WHERE first_name || ' ' || last_name = 'Jane Doe'
stmt = select(User).where(User.full_name == "Jane Doe")
```

---

## Alembic Migrations

Alembic is to SQLAlchemy what `prisma migrate` is to Prisma — but far more configurable.

### Async env.py Configuration

```python
# alembic/env.py
import asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.models.base import Base
from app.models import user, post, comment  # noqa: F401 -- force model registration

target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())
```

### Common Alembic Commands

```bash
alembic init -t async alembic                    # Initialize with async template
alembic revision --autogenerate -m "add users"   # Generate from model changes
alembic revision -m "add search index"           # Empty migration for manual SQL
alembic upgrade head                             # Apply all pending migrations
alembic downgrade -1                             # Rollback last migration
alembic current                                  # Show current revision
alembic history --verbose                        # Show migration history
alembic heads                                    # Show branch heads
alembic merge -m "merge" rev1 rev2               # Merge divergent branches
```

### Data Migration Example

```python
def upgrade() -> None:
    roles_table = sa.table("roles", sa.column("id", sa.Integer), sa.column("name", sa.String))
    op.bulk_insert(roles_table, [
        {"id": 1, "name": "admin"},
        {"id": 2, "name": "editor"},
        {"id": 3, "name": "viewer"},
    ])

def downgrade() -> None:
    op.execute("DELETE FROM roles WHERE id IN (1, 2, 3)")
```

### Column With Computed Default Migration

```python
def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(200), nullable=True))
    op.execute("UPDATE users SET display_name = COALESCE(name, split_part(email, '@', 1))")
    op.alter_column("users", "display_name", nullable=False)
```

---

## ORM Alternatives

### SQLModel

Created by the same author as FastAPI (Sebastian Ramirez). It merges Pydantic and SQLAlchemy
into a single class:

```python
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True)
```

**Pros:** Single class for ORM model AND Pydantic schema — no duplication. Feels familiar if
you come from Prisma. FastAPI integration is seamless.

**Cons:** Lags behind SQLAlchemy 2.0 features. Relationship support is less mature. The
single-class approach breaks down when your API schema diverges from your DB schema (which it
always does in real applications). Debugging is harder because you're debugging through two
abstraction layers.

**Recommendation:** Use SQLAlchemy directly for production applications. SQLModel is fine for
prototypes and tutorials.

### Tortoise ORM

Django-inspired async ORM. If you dislike SQLAlchemy's verbosity:

```python
from tortoise import fields, models

class User(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=255, unique=True)

    class Meta:
        table = "users"

# Query style
users = await User.filter(is_active=True).prefetch_related("posts").all()
```

**Pros:** Django-like API; less boilerplate. Built for async from day one. `prefetch_related`
is intuitive.

**Cons:** Smaller ecosystem, fewer production deployments. No equivalent of SQLAlchemy Core for
complex queries. Migration tool (Aerich) is less mature than Alembic. Limited control over
connection pooling and raw SQL integration.

---

## Practice Exercises

The following exercises in `exercises.py` practice the concepts from this file. Also see `examples.py` Section 2 (Model Definitions with Relationships) for complete working models you can reference.

- **Exercise 1 — Define SQLAlchemy Models**: Build `User`, `Article`, and `Tag` models using `Mapped[]` and `mapped_column()` syntax. Practices column definitions, one-to-many relationships with `back_populates` and `cascade`, many-to-many via an association `Table`, and `ForeignKey` with `ondelete` behavior. Covers the Declarative Mapping, Relationship Patterns, and Lazy vs Eager Loading sections above.

---

## Key Takeaways

- `Mapped[str]` with Python types replaces verbose column decorators — the type IS the column.
- `Optional[str]` maps to `nullable=True`; `list[Post]` maps to a one-to-many relationship.
- Async SQLAlchemy prohibits lazy loading — always use `selectinload` or `joinedload`.
- Use `selectinload` for collections (one-to-many), `joinedload` for single objects (many-to-one).
- Alembic is the migration tool; `--autogenerate` diffs your models against the database schema.

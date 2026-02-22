# Module 03: Database Patterns with SQLAlchemy

## Overview

This module covers SQLAlchemy 2.0 with async support, the dominant Python ORM for production
applications. Coming from Prisma, TypeORM, or Drizzle, you'll find SQLAlchemy more verbose but
significantly more powerful -- fine-grained control over SQL generation, connection management,
and complex query composition that TypeScript ORMs don't match.

The mental model shift: Prisma and Drizzle are query builders with schema management. TypeORM is
closer but lacks SQLAlchemy's maturity. SQLAlchemy is a full database toolkit with an optional
ORM layer on top -- you can mix raw SQL, Core query builder, and ORM in the same application.

---

## SQLAlchemy 2.0: The Modern API

SQLAlchemy 2.0 introduced a new API style. If you see `session.query(User)`, that's legacy 1.x.
The modern style uses `select()` statements.

```bash
pip install "sqlalchemy[asyncio]>=2.0" asyncpg alembic
```

### Engine and Session Setup (Async)

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/mydb"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,           # True for SQL logging during development
    pool_size=20,         # Persistent connections in the pool
    max_overflow=10,      # Extra connections when pool is exhausted
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=3600,    # Recycle connections after 1 hour
)

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)
```

**Comparison with TypeScript ORMs:**

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

Key differences from TypeORM: `Mapped[str]` replaces `@Column({ type: 'varchar' })` -- the
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

### Many-to-Many

```python
# Association table -- equivalent to Prisma's implicit many-to-many
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

### Lazy vs Eager Loading

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
```

| Strategy | SQL Generated | Best For |
|----------|--------------|----------|
| `selectinload` | Separate `SELECT ... IN (...)` | Collections (one-to-many) |
| `joinedload` | `LEFT JOIN` in same query | Single objects (many-to-one) |
| `subqueryload` | Separate subquery | Legacy; prefer `selectinload` |
| `lazyload` | On access (sync only) | Never use in async |

---

## Session Management in FastAPI

### The Dependency Pattern

```python
from collections.abc import AsyncGenerator

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

```python
@router.post("/users")
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    user = User(**data.model_dump())
    session.add(user)
    await session.flush()  # Generates ID without committing
    return UserResponse.model_validate(user)
```

### Session Lifecycle

```
Request -> get_session() creates AsyncSession
  -> Handler uses session (add, execute, flush)
    -> Success: commit() | Error: rollback()
  -> Session closed -> Response sent
```

- **`flush()`** -- writes pending changes within the transaction. Generates IDs, triggers constraints.
- **`commit()`** -- finalizes the transaction. Changes visible to other sessions.
- **`refresh()`** -- re-reads an object from DB. Needed after commit if `expire_on_commit=True`.
- **`expire_on_commit=False`** -- prevents SQLAlchemy from marking attributes stale after commit. Critical in async.

### Nested Transactions (Savepoints)

```python
async def transfer_with_audit(session, from_id, to_id, amount):
    async with session.begin_nested():  # SAVEPOINT
        await debit_account(session, from_id, amount)
        await credit_account(session, to_id, amount)
    # Audit log outside savepoint -- always written even if savepoint rolls back
    session.add(AuditLog(action="transfer", details=f"{from_id} -> {to_id}: {amount}"))
```

---

## Alembic Migrations

Alembic is to SQLAlchemy what `prisma migrate` is to Prisma -- but far more configurable.

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

### Common Commands

```bash
alembic init -t async alembic                    # Initialize with async template
alembic revision --autogenerate -m "add users"   # Generate from model changes
alembic upgrade head                             # Apply all pending migrations
alembic downgrade -1                             # Rollback last migration
alembic current                                  # Show current revision
alembic history --verbose                        # Show migration history
alembic revision -m "add search index"           # Empty migration for manual SQL
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

---

## Raw SQL with `text()`

```python
from sqlalchemy import text

# Parameterized query
result = await session.execute(
    text("SELECT * FROM users WHERE email = :email"), {"email": "user@example.com"}
)
row = result.one_or_none()

# Map raw results to ORM objects
result = await session.execute(
    select(User).from_statement(text("SELECT * FROM users WHERE is_active = true"))
)
users = result.scalars().all()
```

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

## Connection Pooling

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Persistent connections
    max_overflow=10,     # Temporary connections (total max = 30)
    pool_timeout=30,     # Wait seconds before raising on full pool
    pool_pre_ping=True,  # SELECT 1 before use (handles stale connections)
    pool_recycle=3600,   # Close connections older than 1 hour
)
```

Sizing: `pool_size` = expected concurrent requests / number of app workers. For gunicorn with
4 workers each at `pool_size=5` = 20 total. PostgreSQL default `max_connections=100`; leave
headroom. Use PgBouncer in production for connection multiplexing.

### Read Replica Routing

```python
write_engine = create_async_engine("postgresql+asyncpg://user:pass@primary:5432/db")
read_engine = create_async_engine("postgresql+asyncpg://user:pass@replica:5432/db")

write_session_factory = async_sessionmaker(write_engine, class_=AsyncSession)
read_session_factory = async_sessionmaker(read_engine, class_=AsyncSession)

async def get_write_session() -> AsyncGenerator[AsyncSession, None]:
    async with write_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_read_session() -> AsyncGenerator[AsyncSession, None]:
    async with read_session_factory() as session:
        yield session  # No commit needed for reads

# Usage: Depends(get_read_session) for GET, Depends(get_write_session) for mutations
```

---

## Query Patterns

### SELECT

```python
from sqlalchemy import select, and_, or_, func

user = await session.get(User, user_id)                                     # By PK
user = (await session.execute(
    select(User).where(User.email == "test@example.com")
)).scalar_one_or_none()                                                     # By filter

users = (await session.execute(
    select(User).where(User.is_active == True)
    .order_by(User.created_at.desc()).offset(20).limit(10)
)).scalars().all()                                                          # Paginated

stmt = select(User).where(and_(
    User.is_active == True,
    or_(User.email.contains("@company.com"), User.role == "admin"),
))                                                                          # Complex filter
```

### INSERT / UPDATE / DELETE

```python
from sqlalchemy import insert, update, delete

# ORM insert
user = User(email="new@example.com", name="New User")
session.add(user)
await session.flush()

# Bulk insert (Core -- much faster)
await session.execute(insert(User).values([
    {"email": "a@test.com", "name": "A"}, {"email": "b@test.com", "name": "B"},
]))

# Bulk update with RETURNING
result = await session.execute(
    update(User).where(User.is_active == False).values(is_active=True).returning(User.id)
)
updated_ids = result.scalars().all()

# Delete
await session.execute(delete(User).where(User.is_active == False))
```

### JOINs

```python
# Through relationship
stmt = select(Post).join(Post.author).where(User.email == "test@example.com")

# Explicit join with aggregation
stmt = (select(User.name, func.count(Post.id).label("post_count"))
        .join(Post, Post.author_id == User.id)
        .group_by(User.name).having(func.count(Post.id) > 5))

# Left outer join
stmt = select(User, Post).outerjoin(Post, Post.author_id == User.id)
```

### Subqueries and CTEs

```python
# Subquery: users ranked by post count
subq = (select(Post.author_id, func.count(Post.id).label("post_count"))
        .group_by(Post.author_id).subquery())
stmt = (select(User, subq.c.post_count)
        .outerjoin(subq, User.id == subq.c.author_id)
        .order_by(subq.c.post_count.desc()))

# Recursive CTE: hierarchical comments with depth
comment_tree = (
    select(Comment.id, Comment.parent_id, Comment.content, literal(0).label("depth"))
    .where(Comment.parent_id == None)
    .cte(name="comment_tree", recursive=True)
)
comment_alias = aliased(Comment)
comment_tree = comment_tree.union_all(
    select(comment_alias.id, comment_alias.parent_id, comment_alias.content,
           (comment_tree.c.depth + 1).label("depth"))
    .join(comment_tree, comment_alias.parent_id == comment_tree.c.id)
)
```

### Window Functions

```python
# Rank users by post count within each role
stmt = select(
    User.name, User.role, func.count(Post.id).label("post_count"),
    func.rank().over(
        partition_by=User.role, order_by=func.count(Post.id).desc(),
    ).label("rank_in_role"),
).join(Post).group_by(User.id, User.name, User.role)

# Running total
stmt = select(
    Transaction.date, Transaction.amount,
    func.sum(Transaction.amount).over(
        order_by=Transaction.date, rows=(None, 0),
    ).label("running_total"),
)
```

---

## Interview Questions

### Conceptual

1. **Explain the Unit of Work pattern in SQLAlchemy. How does it differ from Prisma?**

   SQLAlchemy's Session tracks all objects loaded and modified. On `flush()`/`commit()`, it
   computes the minimal set of INSERT/UPDATE/DELETE in topological (FK dependency) order.
   Prisma has no Unit of Work -- each operation is independent unless wrapped in `$transaction`.

2. **Why does async SQLAlchemy prohibit lazy loading?**

   Lazy loading triggers synchronous I/O when accessing a relationship attribute. In async,
   there's no event loop available in that context. Solution: always use `selectinload`/
   `joinedload` or `await session.refresh(obj, ["relation"])`.

3. **When would you use `selectinload` vs `joinedload`?**

   `joinedload` = single query with LEFT JOIN, efficient for single objects but causes row
   multiplication for collections. `selectinload` = second query with `WHERE id IN (...)`,
   better for collections since each parent row appears only once.

4. **What is `expire_on_commit` and why set it to `False` in async?**

   After `commit()`, SQLAlchemy marks attributes as "expired" -- next access triggers a lazy
   reload. In async this fails. `expire_on_commit=False` keeps values in memory after commit.

### Practical

5. **Design a paginated endpoint with user post counts, filterable and sorted.**

   ```python
   @router.get("/users")
   async def list_users(
       active: bool | None = None,
       page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
       session: AsyncSession = Depends(get_session),
   ):
       stmt = (select(User, func.count(Post.id).label("post_count"))
               .outerjoin(Post).group_by(User.id)
               .order_by(func.count(Post.id).desc())
               .offset((page - 1) * size).limit(size))
       if active is not None:
           stmt = stmt.where(User.is_active == active)
       return [{"user": u, "post_count": c} for u, c in (await session.execute(stmt)).all()]
   ```

6. **How would you implement optimistic locking?**

   ```python
   class Document(Base):
       __tablename__ = "documents"
       id: Mapped[int] = mapped_column(primary_key=True)
       title: Mapped[str] = mapped_column(String(255))
       version: Mapped[int] = mapped_column(default=1)
       __mapper_args__ = {"version_id_col": version}
   ```

   SQLAlchemy adds `WHERE version = :old_version` to UPDATEs. Concurrent modification raises
   `StaleDataError`.

7. **Write an Alembic migration adding a column with computed defaults.**

   ```python
   def upgrade() -> None:
       op.add_column("users", sa.Column("display_name", sa.String(200), nullable=True))
       op.execute("UPDATE users SET display_name = COALESCE(name, split_part(email, '@', 1))")
       op.alter_column("users", "display_name", nullable=False)
   ```

8. **How do you handle the N+1 query problem?**

   Use `selectinload()`/`joinedload()` for eager loading; set `lazy="selectin"` on relationship
   definitions for default eager loading; use Core-style bulk queries for write-heavy code;
   monitor with `echo=True` or event hooks to count queries per request.

### System Design

9. **Design connection pooling for 10 workers, 1 primary, 2 read replicas.**

   PostgreSQL `max_connections=200`. Per worker: `pool_size=5, max_overflow=5` (100 total).
   Separate engine per replica with own pool. PgBouncer for multiplexing. `pool_pre_ping=True`
   for failover. `pool_recycle=3600` for stale connections.

10. **How would you migrate 50M rows from integer IDs to UUIDs without downtime?**

    Phase 1: Add nullable `uuid` column with index. Phase 2: Backfill in batches with
    `server_default=gen_random_uuid()`. Phase 3: Dual-write application code. Phase 4: Make
    non-nullable, add unique constraint. Phase 5: Switch reads to UUID. Phase 6: Drop old PK,
    rename UUID column, set as new PK.

# Module 03 Deep Dive: SQLAlchemy Internals, Alternatives & Advanced Patterns

## SQLAlchemy Internals

### Identity Map

The identity map is a per-session cache keyed by `(type, primary_key)`. When you call
`session.get(User, 1)` twice, the second call returns the same Python object from the map
without hitting the database. This guarantees object identity within a session:

```python
user_a = await session.get(User, user_id)
user_b = await session.get(User, user_id)
assert user_a is user_b  # Same object, not just equal -- same memory address
```

This matters because modifications are tracked on the object itself. If two different objects
represented the same row, changes could conflict. The identity map is equivalent to a
first-level cache in Hibernate/JPA.

**Implications for FastAPI:**

- One session per request means one identity map per request. Objects are never shared across
  requests (which is correct and safe).
- If you load 10,000 objects in a session, they all live in memory. For bulk reads, use
  `yield_per()` or stream results to avoid memory pressure.

```python
# Stream results to avoid loading all rows into the identity map
stmt = select(User).execution_options(yield_per=1000)
result = await session.execute(stmt)
async for partition in result.partitions(1000):
    for row in partition:
        process(row)
```

### Unit of Work Flush Process

When `session.flush()` is called (explicitly or implicitly before queries), SQLAlchemy:

1. Scans the identity map for all "dirty" (modified) objects
2. Scans the "new" list for objects added via `session.add()`
3. Scans the "deleted" list for objects marked via `session.delete()`
4. Topologically sorts operations by foreign key dependencies
5. Emits INSERT, UPDATE, DELETE statements in the correct order
6. Updates primary keys and foreign keys on in-memory objects

```python
# Demonstration: the flush order is automatic
parent = User(name="Parent")
child = Post(title="Child Post", author=parent)  # FK depends on parent.id

session.add(child)  # Only add the child
await session.flush()

# SQLAlchemy figures out it needs to INSERT the User first, get the ID,
# then INSERT the Post with the correct author_id. You don't manage this.
```

**Autoflush behavior:**

By default, SQLAlchemy flushes before every query to ensure consistency. This means:

```python
user = User(name="New User", email="new@test.com")
session.add(user)

# This triggers an autoflush -- the INSERT for "New User" happens BEFORE the SELECT
stmt = select(User).where(User.email == "new@test.com")
result = await session.execute(stmt)
found_user = result.scalar_one()  # Finds the just-added user
```

You can disable autoflush with `async_sessionmaker(autoflush=False)`, but this is rarely a
good idea as it leads to stale query results.

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

**Pros:**
- Single class for ORM model AND Pydantic schema -- no duplication
- Feels familiar if you come from Prisma (schema-as-source-of-truth)
- FastAPI integration is seamless

**Cons:**
- Lags behind SQLAlchemy 2.0 features (limited `Mapped[]` support as of 2025)
- Relationship support is less mature
- The single-class approach breaks down when your API schema diverges from your DB schema
  (which it always does in real applications)
- Debugging is harder because you're debugging through two abstraction layers

**Recommendation:** Use SQLAlchemy directly for production applications. SQLModel is fine for
prototypes and tutorials.

### Tortoise ORM

Django-inspired async ORM. If you hate SQLAlchemy's verbosity:

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

**Pros:**
- Django-like API; less boilerplate
- Built for async from day one
- `prefetch_related` is intuitive

**Cons:**
- Smaller ecosystem, fewer production deployments
- No equivalent of SQLAlchemy Core for complex queries
- Migration tool (Aerich) is less mature than Alembic
- Limited control over connection pooling and raw SQL integration

---

## Database Testing Patterns

### Transaction Rollback Strategy

The gold standard for database tests: run each test inside a transaction that's always rolled
back. Tests are isolated and fast because nothing is written to disk.

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.base import Base

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Each test gets a session wrapped in a transaction that rolls back."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await transaction.rollback()
            await session.close()


@pytest.fixture
async def client(session):
    """Override the get_session dependency in FastAPI."""
    from app.database import get_session
    from app.main import app

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

### Factory Boy Integration

Factory Boy replaces manual fixture creation. Think of it as a typed, composable seed script:

```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from app.models.user import User
from app.models.post import Post


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    is_active = True


class PostFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Post
        sqlalchemy_session_persistence = "flush"

    title = factory.Faker("sentence")
    content = factory.Faker("paragraph")
    author = factory.SubFactory(UserFactory)
```

```python
# tests/test_users.py
async def test_list_active_users(session, client):
    # Arrange
    UserFactory._meta.sqlalchemy_session = session
    active_users = UserFactory.create_batch(5, is_active=True)
    inactive_users = UserFactory.create_batch(3, is_active=False)
    await session.flush()

    # Act
    response = await client.get("/users?active=true")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 5
```

---

## Multi-Tenancy with SQLAlchemy

### Schema-per-Tenant

PostgreSQL schemas provide strong isolation. Each tenant gets their own namespace:

```python
from sqlalchemy import event, text

def set_tenant_schema(session: AsyncSession, tenant_id: str):
    """Set the search_path for this session to the tenant's schema."""
    schema = f"tenant_{tenant_id}"

    @event.listens_for(session.sync_session, "after_begin")
    def set_search_path(session, transaction, connection):
        connection.execute(text(f"SET search_path TO {schema}, public"))


# FastAPI dependency
async def get_tenant_session(
    tenant_id: str = Header(..., alias="X-Tenant-ID"),
) -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        await session.execute(
            text(f"SET search_path TO tenant_{tenant_id}, public")
        )
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Row-Level (Shared Schema) Multi-Tenancy

All tenants share tables with a `tenant_id` discriminator:

```python
class TenantMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )


class User(TenantMixin, TimestampMixin, Base):
    __tablename__ = "users"
    # ... fields ...


# Automatic tenant filtering using SQLAlchemy events
@event.listens_for(AsyncSession, "do_orm_execute")
def _add_tenant_filter(execute_state):
    """Automatically add WHERE tenant_id = :current_tenant to all queries."""
    if execute_state.is_select:
        tenant_id = execute_state.session.info.get("tenant_id")
        if tenant_id:
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    TenantMixin,
                    lambda cls: cls.tenant_id == tenant_id,
                    include_aliases=True,
                )
            )
```

---

## Soft Deletes

```python
class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    @hybrid_property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    async def soft_delete(self, session: AsyncSession):
        self.deleted_at = datetime.utcnow()
        await session.flush()

# Global filter: auto-exclude soft-deleted records (opt out with include_deleted=True)
@event.listens_for(AsyncSession, "do_orm_execute")
def _exclude_soft_deleted(execute_state):
    if (execute_state.is_select
            and not execute_state.execution_options.get("include_deleted", False)):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(SoftDeleteMixin,
                lambda cls: cls.deleted_at.is_(None), include_aliases=True))

# To include deleted records:
stmt = select(User).execution_options(include_deleted=True)
```

---

## Full-Text Search with PostgreSQL

### Model with tsvector and GIN Index

```python
from sqlalchemy.dialects.postgresql import TSVECTOR

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (Index("ix_posts_search_vector", search_vector, postgresql_using="gin"),)
```

### Alembic Migration

```python
def upgrade() -> None:
    op.add_column("posts", sa.Column("search_vector", TSVECTOR, nullable=True))
    op.create_index("ix_posts_search_vector", "posts", ["search_vector"], postgresql_using="gin")
    op.execute("""
        CREATE OR REPLACE FUNCTION posts_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B');
            RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER posts_search_vector_trigger
        BEFORE INSERT OR UPDATE ON posts FOR EACH ROW EXECUTE FUNCTION posts_search_vector_update();
    """)
    op.execute("""UPDATE posts SET search_vector =
        setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(content, '')), 'B')""")
```

### Querying

```python
async def search_posts(session: AsyncSession, query: str, limit: int = 20):
    ts_query = func.plainto_tsquery("english", query)
    stmt = (select(Post, func.ts_rank(Post.search_vector, ts_query).label("rank"))
            .where(Post.search_vector.op("@@")(ts_query))
            .order_by(func.ts_rank(Post.search_vector, ts_query).desc()).limit(limit))
    return (await session.execute(stmt)).all()
```

---

## Query Optimization and EXPLAIN

### Analyzing Queries

```python
from sqlalchemy import explain

# Get the EXPLAIN output for any statement
stmt = select(User).where(User.email == "test@example.com")
explained = await session.execute(
    stmt.prefix_with("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)")
)
plan = explained.scalar()

# Or use SQLAlchemy's explain helper (sync only as of 2.0)
# For async, prefix_with is the practical approach
```

### Common Optimization Patterns

```python
# 1. Only select the columns you need (avoid SELECT *)
stmt = select(User.id, User.name).where(User.is_active == True)

# 2. Use exists() for existence checks instead of loading full objects
from sqlalchemy import exists
stmt = select(exists().where(User.email == email))
result = await session.execute(stmt)
email_taken = result.scalar()

# 3. Use bulk operations instead of ORM for large datasets
from sqlalchemy import insert
await session.execute(
    insert(User),
    [{"email": f"user{i}@test.com", "name": f"User {i}"} for i in range(10000)],
)

# 4. Keyset pagination instead of OFFSET for large tables
stmt = (
    select(User)
    .where(User.created_at < last_seen_timestamp)
    .order_by(User.created_at.desc())
    .limit(20)
)

# 5. Use server-side cursors for streaming large result sets
stmt = select(User).execution_options(yield_per=500)
result = await session.stream(stmt)
async for row in result:
    process(row)
```

### Index Strategy Checklist

1. Primary keys are automatically indexed
2. Add indexes on foreign keys (SQLAlchemy doesn't do this automatically, unlike some ORMs)
3. Add indexes on columns used in WHERE, ORDER BY, and JOIN conditions
4. Use composite indexes for multi-column filters (order matters: most selective first)
5. Use partial indexes for filtered queries (`WHERE is_active = true`)
6. Use GIN indexes for array, JSONB, and full-text search columns
7. Monitor with `pg_stat_user_indexes` to find unused indexes

```python
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_active_created", "is_active", "created_at",
              postgresql_where=text("is_active = true")),  # Partial index
    )
```

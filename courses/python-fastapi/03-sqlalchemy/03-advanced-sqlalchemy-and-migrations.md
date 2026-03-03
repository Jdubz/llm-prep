# 03 – Advanced SQLAlchemy and Migrations

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

Factory Boy replaces manual fixture creation:

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

### Alembic Migration with Trigger

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

### Querying Full-Text Search

```python
async def search_posts(session: AsyncSession, query: str, limit: int = 20):
    ts_query = func.plainto_tsquery("english", query)
    stmt = (select(Post, func.ts_rank(Post.search_vector, ts_query).label("rank"))
            .where(Post.search_vector.op("@@")(ts_query))
            .order_by(func.ts_rank(Post.search_vector, ts_query).desc()).limit(limit))
    return (await session.execute(stmt)).all()
```

---

## Query Optimization and Performance

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

### Analyzing Queries

```python
from sqlalchemy import explain

# Get the EXPLAIN output for any statement
stmt = select(User).where(User.email == "test@example.com")
explained = await session.execute(
    stmt.prefix_with("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)")
)
plan = explained.scalar()
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

### Optimistic Locking

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

---

## Interview Questions

### Conceptual

**1. Explain the Unit of Work pattern in SQLAlchemy. How does it differ from Prisma?**

SQLAlchemy's Session tracks all objects loaded and modified. On `flush()`/`commit()`, it
computes the minimal set of INSERT/UPDATE/DELETE in topological (FK dependency) order.
Prisma has no Unit of Work — each operation is independent unless wrapped in `$transaction`.

**2. Why does async SQLAlchemy prohibit lazy loading?**

Lazy loading triggers synchronous I/O when accessing a relationship attribute. In async,
there's no event loop available in that context. Solution: always use `selectinload`/
`joinedload` or `await session.refresh(obj, ["relation"])`.

**3. When would you use `selectinload` vs `joinedload`?**

`joinedload` = single query with LEFT JOIN, efficient for single objects but causes row
multiplication for collections. `selectinload` = second query with `WHERE id IN (...)`,
better for collections since each parent row appears only once.

**4. What is `expire_on_commit` and why set it to `False` in async?**

After `commit()`, SQLAlchemy marks attributes as "expired" — next access triggers a lazy
reload. In async this fails. `expire_on_commit=False` keeps values in memory after commit.

### Practical

**5. Design a paginated endpoint with user post counts, filterable and sorted.**

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

**6. How do you handle the N+1 query problem?**

Use `selectinload()`/`joinedload()` for eager loading; set `lazy="selectin"` on relationship
definitions for default eager loading; use Core-style bulk queries for write-heavy code;
monitor with `echo=True` or event hooks to count queries per request.

### System Design

**7. Design connection pooling for 10 workers, 1 primary, 2 read replicas.**

PostgreSQL `max_connections=200`. Per worker: `pool_size=5, max_overflow=5` (100 total).
Separate engine per replica with own pool. PgBouncer for multiplexing. `pool_pre_ping=True`
for failover. `pool_recycle=3600` for stale connections.

**8. How would you migrate 50M rows from integer IDs to UUIDs without downtime?**

Phase 1: Add nullable `uuid` column with index. Phase 2: Backfill in batches with
`server_default=gen_random_uuid()`. Phase 3: Dual-write application code. Phase 4: Make
non-nullable, add unique constraint. Phase 5: Switch reads to UUID. Phase 6: Drop old PK,
rename UUID column, set as new PK.

---

## Key Takeaways

- The identity map ensures object identity within a session; one session per request is safe.
- The Unit of Work handles topological INSERT ordering automatically — you don't manage FK order.
- For large result sets, use `yield_per` and streaming to avoid loading everything into the identity map.
- Optimistic locking via `version_id_col` prevents lost updates in concurrent environments.
- Index strategy: always index FK columns, use partial indexes for filtered queries, GIN for JSONB.
- Transaction rollback fixtures are the gold standard for database tests — fast, isolated, clean.

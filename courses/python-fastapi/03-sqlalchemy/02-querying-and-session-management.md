# 02 – Querying and Session Management

## Engine and Session Setup (Async)

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

Key operations:
- **`flush()`** — writes pending changes within the transaction. Generates IDs, triggers constraints.
- **`commit()`** — finalizes the transaction. Changes visible to other sessions.
- **`refresh()`** — re-reads an object from DB. Needed after commit if `expire_on_commit=True`.
- **`expire_on_commit=False`** — prevents SQLAlchemy from marking attributes stale after commit. Critical in async.

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

## Query Patterns Quick Reference

### SELECT

```python
from sqlalchemy import select, and_, or_, func

# GET by PK
user = await session.get(User, user_id)

# SELECT with filters
stmt = select(User).where(and_(User.is_active == True, User.role == "admin"))
result = await session.execute(stmt)
users = result.scalars().all()

# SELECT one or None
user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()

# Paginated list (newest first)
users = (await session.execute(
    select(User).where(User.is_active == True)
    .order_by(User.created_at.desc()).offset(20).limit(10)
)).scalars().all()

# Complex filter
stmt = select(User).where(and_(
    User.is_active == True,
    or_(User.email.contains("@company.com"), User.role == "admin"),
))
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

# JOIN + aggregate (cheat sheet form)
stmt = (select(User.name, func.count(Post.id))
        .join(Post).group_by(User.name).having(func.count(Post.id) > 5))
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

Sizing: `pool_size` = expected concurrent requests / number of app workers. For Gunicorn with
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

## SQLAlchemy Internals: Identity Map

The identity map is a per-session cache keyed by `(type, primary_key)`. When you call
`session.get(User, 1)` twice, the second call returns the same Python object from the map
without hitting the database.

```python
user_a = await session.get(User, user_id)
user_b = await session.get(User, user_id)
assert user_a is user_b  # Same object, not just equal -- same memory address
```

This guarantees object identity within a session. It is equivalent to a first-level cache in
Hibernate/JPA.

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

---

## Unit of Work Flush Process

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

## Practice Exercises

The following exercises in `exercises.py` practice the concepts from this file. Also see `examples.py` Sections 5-8 for complete working implementations of each pattern.

- **Exercise 2 — Generic CRUD Repository**: Implement `get_by_id`, `list_all`, `create`, `update`, and `delete` using `session.get()`, `select()`, `session.add()`, and `session.delete()`. Practices the Session Management, flush vs commit, and Query Patterns SELECT sections above. See `examples.py` Section 5 (Generic Repository Pattern) for a reference implementation.

- **Exercise 3 — Cursor-Based Pagination**: Implement `paginate_articles()` using `select().where().order_by().limit()` with the "fetch size+1 to detect next page" technique. Practices the Query Patterns SELECT section above. See `examples.py` Section 6b (Cursor-based pagination) for the complete pattern.

- **Exercise 4 — Search with Multiple Filters**: Build a composable search function that dynamically applies `where()`, `or_()`, `join()`, and `selectinload()` based on which filters are non-None. Practices the Query Patterns SELECT and JOINs sections above. See `examples.py` Section 6c (Joins and eager loading) and Section 6d (Aggregation with joins).

- **Exercise 5 — Bulk Insert**: Use the Core `insert().values()` API for multi-row inserts instead of ORM `session.add()` loops. Practices the INSERT / UPDATE / DELETE section above. See `examples.py` Section 8 (Bulk Insert with Core API).

---

## Key Takeaways

- One session per request: create in a yield dependency, commit on success, rollback on error.
- `flush()` writes to the transaction; `commit()` makes it durable and visible.
- `expire_on_commit=False` is essential in async to avoid lazy-load errors after commit.
- The identity map ensures object identity within a session and acts as a first-level cache.
- The Unit of Work pattern handles topological ordering of inserts automatically.
- Use read replicas with separate session factories for read-heavy workloads.

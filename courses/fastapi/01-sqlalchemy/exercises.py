"""
SQLAlchemy 2.0 Exercises

Practice defining models, building repositories, writing queries, and working
with transactions. Uses SQLite + aiosqlite for portability.

Run tests:  python exercises.py
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Table,
    Text,
    func,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    selectinload,
)


# ---------------------------------------------------------------------------
# Shared Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ============================================================================
# EXERCISE 1: Define SQLAlchemy Models
# ============================================================================
#
# READ FIRST: 01-models-relationships-and-schema.md
#   - "Declarative Mapping with mapped_column" for column syntax
#   - "Relationship Patterns" for one-to-many and many-to-many
#
# ALSO SEE: examples.py
#   - Section 1 (Base and Mixin Definitions) for TimestampMixin pattern
#   - Section 2 (Model Definitions with Relationships) for complete User/Post/Tag models
#
# Create three models: User, Article, and Tag.
#
# User
#   - id: int, primary key
#   - username: str(80), unique, not nullable
#   - email: str(255), unique, not nullable
#   - is_active: bool, default True
#   - created_at: datetime, server default now()
#   - articles: one-to-many relationship to Article (cascade delete-orphan)
#
# Article
#   - id: int, primary key
#   - title: str(200), not nullable
#   - body: Text, not nullable
#   - is_published: bool, default False
#   - author_id: int, FK to users.id (CASCADE delete)
#   - created_at: datetime, server default now()
#   - author: many-to-one back to User
#   - tags: many-to-many with Tag via article_tags association table
#
# Tag
#   - id: int, primary key
#   - name: str(50), unique, not nullable
#   - articles: many-to-many back to Article
#
# Don't forget the association table for the many-to-many relationship.
#
# ---------------------------------------------------------------------------
# SYNTAX REFERENCE (so you can complete this without leaving the file):
# ---------------------------------------------------------------------------
#
# Column definitions use Mapped[] with mapped_column():
#
#   id: Mapped[int] = mapped_column(primary_key=True)
#   username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
#   is_active: Mapped[bool] = mapped_column(default=True)
#   created_at: Mapped[datetime] = mapped_column(server_default=func.now())
#
# Foreign key column:
#   author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
#
# One-to-many (parent side -- list of children):
#   articles: Mapped[list[Article]] = relationship(
#       back_populates="author", cascade="all, delete-orphan",
#   )
#
# Many-to-one (child side -- single parent):
#   author: Mapped[User] = relationship(back_populates="articles")
#
# Many-to-many association table (plain Table, not a model class):
#   article_tags = Table(
#       "article_tags",
#       Base.metadata,
#       Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
#       Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
#   )
#
# Many-to-many relationship (both sides reference the association table):
#   tags: Mapped[list[Tag]] = relationship(secondary=article_tags, back_populates="articles")
#   articles: Mapped[list[Article]] = relationship(secondary=article_tags, back_populates="tags")

# TODO: Define the article_tags association table
# article_tags = Table(
#     ...
# )


class User(Base):
    __tablename__ = "users"

    # TODO: Define columns and relationships
    #   id, username, email, is_active, created_at, articles
    pass


class Article(Base):
    __tablename__ = "articles"

    # TODO: Define columns and relationships
    #   id, title, body, is_published, author_id, created_at, author, tags
    pass


class Tag(Base):
    __tablename__ = "tags"

    # TODO: Define columns and relationship
    #   id, name, articles
    pass


# ============================================================================
# EXERCISE 2: Generic CRUD Repository
# ============================================================================
#
# READ FIRST: 02-querying-and-session-management.md
#   - "Session Management in FastAPI" for flush() vs commit() semantics
#   - "Query Patterns Quick Reference > SELECT" for select/execute/scalars
#   - "Unit of Work Flush Process" for why flush() is used inside repositories
#
# ALSO SEE: examples.py
#   - Section 5 (Generic Repository Pattern) for a complete working implementation
#   - Section 4 (Session-as-FastAPI-Dependency Pattern) for how sessions are managed
#
# Implement a reusable repository class that provides:
#   - get_by_id(id) -> ModelT | None
#   - list_all(offset, limit) -> Sequence[ModelT]
#   - create(**kwargs) -> ModelT
#   - update(id, **kwargs) -> ModelT | None
#   - delete(id) -> bool
#
# All methods should use flush() (not commit) so the caller controls the
# transaction boundary.
#
# ---------------------------------------------------------------------------
# SYNTAX REFERENCE (so you can complete this without leaving the file):
# ---------------------------------------------------------------------------
#
# Fetch a single object by primary key (returns the object or None):
#   obj = await self.session.get(self.model, id)
#
# Build and execute a SELECT with offset/limit:
#   stmt = select(self.model).offset(offset).limit(limit)
#   result = await self.session.execute(stmt)
#   items = result.scalars().all()       # returns Sequence[ModelT]
#
# Add a new object to the session and flush to generate its ID:
#   instance = self.model(**kwargs)
#   self.session.add(instance)
#   await self.session.flush()           # writes to DB within txn, generates PK
#
# Update attributes dynamically from a dict:
#   for key, value in kwargs.items():
#       setattr(instance, key, value)
#   await self.session.flush()
#
# Delete an object:
#   await self.session.delete(instance)
#   await self.session.flush()
#
# Why flush() instead of commit():
#   flush() writes changes to the DB within the current transaction but does NOT
#   finalize it. This lets the route handler (or test) control when the transaction
#   commits or rolls back. The repository is a participant, not the owner.

ModelT = TypeVar("ModelT", bound=Base)


class CrudRepository(Generic[ModelT]):
    """Generic async CRUD repository."""

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> ModelT | None:
        # TODO: Use session.get() to fetch by primary key
        pass

    async def list_all(
        self, *, offset: int = 0, limit: int = 20,
    ) -> Sequence[ModelT]:
        # TODO: Build a select() with offset/limit, execute, return scalars
        pass

    async def create(self, **kwargs: Any) -> ModelT:
        # TODO: Instantiate model, add to session, flush, return instance
        pass

    async def update(self, id: int, **kwargs: Any) -> ModelT | None:
        # TODO: Fetch by id, set attributes from kwargs, flush, return
        # Return None if not found
        pass

    async def delete(self, id: int) -> bool:
        # TODO: Fetch by id, delete, flush, return True
        # Return False if not found
        pass


# ============================================================================
# EXERCISE 3: Cursor-Based Pagination
# ============================================================================
#
# READ FIRST: 02-querying-and-session-management.md
#   - "Query Patterns Quick Reference > SELECT" for select/where/order_by/limit
#
# ALSO SEE: examples.py
#   - Section 6b (Cursor-based pagination) for a complete working implementation
#   - Section 6a (Offset-based pagination) to compare the two approaches
#
# Implement cursor-based pagination for the Article model, ordered by id.
#
# Parameters:
#   session  -- the async session
#   cursor   -- the last-seen article ID (None for the first page)
#   size     -- page size
#
# Return a dict with:
#   items      -- list of Article objects (at most `size`)
#   next_cursor -- the ID to pass for the next page, or None if no more pages
#   has_next   -- boolean
#
# ---------------------------------------------------------------------------
# SYNTAX REFERENCE (so you can complete this without leaving the file):
# ---------------------------------------------------------------------------
#
# The "fetch size+1" trick for detecting the next page:
#   Instead of running a COUNT(*) query, fetch one extra row beyond the page
#   size. If you get size+1 rows back, there is a next page. Trim the extra
#   row before returning. This avoids the cost of a separate count query.
#
# Building the query:
#   stmt = select(Article).order_by(Article.id).limit(size + 1)
#
# Adding the cursor filter (only when cursor is not None):
#   stmt = stmt.where(Article.id > cursor)
#
# Executing and collecting rows as a plain list:
#   result = await session.execute(stmt)
#   rows = list(result.scalars().all())
#
# Detecting next page and trimming:
#   has_next = len(rows) > size
#   items = rows[:size]                    # trim to page size
#   next_cursor = items[-1].id if items and has_next else None

async def paginate_articles(
    session: AsyncSession,
    cursor: int | None = None,
    size: int = 20,
) -> dict[str, Any]:
    """Cursor-based pagination over articles ordered by id."""
    # TODO: Implement
    # 1. Build select(Article).order_by(Article.id).limit(size + 1)
    # 2. If cursor is not None, add .where(Article.id > cursor)
    # 3. Execute and collect rows
    # 4. Determine has_next (len(rows) > size)
    # 5. Trim to size, compute next_cursor
    # 6. Return {"items": ..., "next_cursor": ..., "has_next": ...}
    pass


# ============================================================================
# EXERCISE 4: Search Query with Multiple Filters
# ============================================================================
#
# READ FIRST: 02-querying-and-session-management.md
#   - "Query Patterns Quick Reference > SELECT" for where/and_/or_ syntax
#   - "Query Patterns Quick Reference > JOINs" for joining related models
#
# ALSO SEE: examples.py
#   - Section 6c (Joins and eager loading) for selectinload usage
#   - Section 6d (Aggregation with joins) for join + filter patterns
#
# Build a search function for articles that supports optional filters:
#   - keyword   (str | None)  -- if provided, title OR body contains this text
#   - author_id (int | None)  -- if provided, filter by author
#   - tag_name  (str | None)  -- if provided, article must have this tag
#   - published_only (bool)   -- if True, only is_published=True
#
# The function should compose filters dynamically -- only apply the ones that
# are not None.
#
# Return the matching articles eager-loaded with their tags.
#
# ---------------------------------------------------------------------------
# SYNTAX REFERENCE (so you can complete this without leaving the file):
# ---------------------------------------------------------------------------
#
# Start with a base query and conditionally add filters:
#   stmt = select(Article)
#
# Keyword search across multiple columns with or_():
#   from sqlalchemy import or_
#   stmt = stmt.where(or_(
#       Article.title.contains(keyword),
#       Article.body.contains(keyword),
#   ))
#
# Filter by a foreign key value:
#   stmt = stmt.where(Article.author_id == author_id)
#
# Filter by a related model's attribute (requires a join):
#   stmt = stmt.join(Article.tags).where(Tag.name == tag_name)
#
# Boolean filter:
#   stmt = stmt.where(Article.is_published == True)
#
# Eager-load a relationship to avoid N+1 queries in async:
#   stmt = stmt.options(selectinload(Article.tags))
#
# Execute and return results:
#   result = await session.execute(stmt)
#   return result.scalars().all()
#
# IMPORTANT: The .where() calls are composable -- each call adds an AND
# condition. Build the statement step by step, only adding filters that
# have non-None values. You do NOT need to use and_() explicitly when
# chaining .where() calls.

async def search_articles(
    session: AsyncSession,
    *,
    keyword: str | None = None,
    author_id: int | None = None,
    tag_name: str | None = None,
    published_only: bool = False,
) -> Sequence[Article]:
    """Search articles with composable filters."""
    # TODO: Implement
    # 1. Start with stmt = select(Article)
    # 2. If keyword: add .where(or_(Article.title.contains(...), Article.body.contains(...)))
    # 3. If author_id: add .where(Article.author_id == author_id)
    # 4. If tag_name: join Tag and filter by Tag.name == tag_name
    # 5. If published_only: add .where(Article.is_published == True)
    # 6. Add .options(selectinload(Article.tags)) for eager loading
    # 7. Execute and return scalars
    pass


# ============================================================================
# EXERCISE 5: Bulk Insert with insert().values()
# ============================================================================
#
# READ FIRST: 02-querying-and-session-management.md
#   - "Query Patterns Quick Reference > INSERT / UPDATE / DELETE" for Core insert syntax
#
# ALSO SEE: examples.py
#   - Section 8 (Bulk Insert with Core API) for a complete working implementation
#
# READ ALSO: 03-advanced-sqlalchemy-and-migrations.md
#   - "Query Optimization and Performance > Common Optimization Patterns" (pattern 3)
#     for why bulk operations outperform ORM loops
#
# Write a function that bulk-inserts articles using the Core insert() API.
# This is significantly faster than calling session.add() in a loop because
# it generates a single multi-row INSERT statement.
#
# Parameters:
#   session       -- the async session
#   articles_data -- list of dicts, each with keys: title, body, author_id
#
# After inserting, flush the session so IDs are generated.
#
# ---------------------------------------------------------------------------
# SYNTAX REFERENCE (so you can complete this without leaving the file):
# ---------------------------------------------------------------------------
#
# Core insert with multiple rows (single INSERT with many value sets):
#   await session.execute(insert(Article).values(articles_data))
#
# Compare with ORM approach (N separate INSERT statements -- slow):
#   for data in articles_data:
#       session.add(Article(**data))
#
# Guard against empty lists (avoid generating an empty INSERT):
#   if not articles_data:
#       return 0
#
# Flush to write the rows within the current transaction:
#   await session.flush()
#
# Return the count of inserted rows:
#   return len(articles_data)

async def bulk_insert_articles(
    session: AsyncSession,
    articles_data: list[dict[str, Any]],
) -> int:
    """
    Bulk insert articles. Return the number of rows inserted.
    """
    # TODO: Implement
    # 1. Guard: if articles_data is empty, return 0
    # 2. Execute insert(Article).values(articles_data)
    # 3. Flush
    # 4. Return len(articles_data)
    pass


# ============================================================================
# TESTS
# ============================================================================

ASYNC_URL = "sqlite+aiosqlite:///:memory:"


async def _make_session() -> tuple[Any, async_sessionmaker[AsyncSession]]:
    """Create an in-memory engine and session factory for tests."""
    engine = create_async_engine(ASYNC_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def test_exercise_1() -> None:
    print("\n=== EXERCISE 1: Model Definitions ===")
    engine, factory = await _make_session()
    async with factory() as session:
        async with session.begin():
            user = User(username="alice", email="alice@example.com")
            session.add(user)
            await session.flush()

            article = Article(title="Hello", body="World", author_id=user.id)
            session.add(article)
            await session.flush()

            tag = Tag(name="python")
            session.add(tag)
            await session.flush()

            article.tags.append(tag)
            await session.flush()

        # Verify
        async with factory() as read_session:
            stmt = (
                select(Article)
                .options(selectinload(Article.tags), selectinload(Article.author))
                .where(Article.id == article.id)
            )
            result = await read_session.execute(stmt)
            loaded = result.scalar_one()
            print(f"  Article: {loaded.title}")
            print(f"  Author:  {loaded.author.username}")
            print(f"  Tags:    {[t.name for t in loaded.tags]}")

    await engine.dispose()
    print("  PASSED")


async def test_exercise_2() -> None:
    print("\n=== EXERCISE 2: CRUD Repository ===")
    engine, factory = await _make_session()
    async with factory() as session:
        async with session.begin():
            repo = CrudRepository(User, session)

            # Create
            user = await repo.create(username="bob", email="bob@example.com")
            assert user is not None and user.id is not None
            print(f"  Created: id={user.id}, username={user.username}")

            # Read
            fetched = await repo.get_by_id(user.id)
            assert fetched is not None and fetched.username == "bob"
            print(f"  Fetched: {fetched.username}")

            # Update
            updated = await repo.update(user.id, username="bobby")
            assert updated is not None and updated.username == "bobby"
            print(f"  Updated: {updated.username}")

            # List
            items = await repo.list_all(offset=0, limit=10)
            assert len(items) == 1
            print(f"  Listed:  {len(items)} item(s)")

            # Delete
            deleted = await repo.delete(user.id)
            assert deleted is True
            print(f"  Deleted: {deleted}")

    await engine.dispose()
    print("  PASSED")


async def test_exercise_3() -> None:
    print("\n=== EXERCISE 3: Cursor Pagination ===")
    engine, factory = await _make_session()
    async with factory() as session:
        async with session.begin():
            user = User(username="alice", email="alice@example.com")
            session.add(user)
            await session.flush()
            for i in range(5):
                session.add(Article(title=f"Post {i}", body="...", author_id=user.id))
            await session.flush()

        # Page 1
        page1 = await paginate_articles(session, cursor=None, size=2)
        assert page1 is not None
        assert len(page1["items"]) == 2
        assert page1["has_next"] is True
        print(f"  Page 1: {[a.title for a in page1['items']]}, next={page1['next_cursor']}")

        # Page 2
        page2 = await paginate_articles(session, cursor=page1["next_cursor"], size=2)
        assert len(page2["items"]) == 2
        print(f"  Page 2: {[a.title for a in page2['items']]}, next={page2['next_cursor']}")

        # Page 3 (last)
        page3 = await paginate_articles(session, cursor=page2["next_cursor"], size=2)
        assert len(page3["items"]) == 1
        assert page3["has_next"] is False
        print(f"  Page 3: {[a.title for a in page3['items']]}, has_next={page3['has_next']}")

    await engine.dispose()
    print("  PASSED")


async def test_exercise_4() -> None:
    print("\n=== EXERCISE 4: Search with Filters ===")
    engine, factory = await _make_session()
    async with factory() as session:
        async with session.begin():
            alice = User(username="alice", email="alice@example.com")
            bob = User(username="bob", email="bob@example.com")
            session.add_all([alice, bob])
            await session.flush()

            tag_py = Tag(name="python")
            tag_db = Tag(name="database")
            session.add_all([tag_py, tag_db])
            await session.flush()

            a1 = Article(title="Learn Python", body="Basics of Python", author_id=alice.id, is_published=True)
            a2 = Article(title="SQLAlchemy Guide", body="Database patterns", author_id=alice.id, is_published=True)
            a3 = Article(title="Draft Post", body="Work in progress", author_id=bob.id, is_published=False)
            session.add_all([a1, a2, a3])
            await session.flush()

            a1.tags.append(tag_py)
            a2.tags.extend([tag_py, tag_db])
            await session.flush()

        # By keyword
        results = await search_articles(session, keyword="Python")
        assert results is not None
        print(f"  keyword='Python':      {[a.title for a in results]}")

        # By tag
        results = await search_articles(session, tag_name="database")
        print(f"  tag='database':        {[a.title for a in results]}")

        # Published only
        results = await search_articles(session, published_only=True)
        print(f"  published_only=True:   {[a.title for a in results]}")

        # Combined
        results = await search_articles(session, keyword="Python", tag_name="python", published_only=True)
        print(f"  combined filters:      {[a.title for a in results]}")

    await engine.dispose()
    print("  PASSED")


async def test_exercise_5() -> None:
    print("\n=== EXERCISE 5: Bulk Insert ===")
    engine, factory = await _make_session()
    async with factory() as session:
        async with session.begin():
            user = User(username="alice", email="alice@example.com")
            session.add(user)
            await session.flush()

            data = [
                {"title": f"Bulk Post {i}", "body": f"Content {i}", "author_id": user.id}
                for i in range(100)
            ]
            count = await bulk_insert_articles(session, data)
            assert count is not None

        # Verify
        result = await session.execute(select(func.count(Article.id)))
        total = result.scalar_one()
        print(f"  Inserted: {count}")
        print(f"  Total in DB: {total}")
        assert total == 100

    await engine.dispose()
    print("  PASSED")


async def run_all_tests() -> None:
    tests = [
        test_exercise_1,
        test_exercise_2,
        test_exercise_3,
        test_exercise_4,
        test_exercise_5,
    ]
    for test in tests:
        try:
            await test()
        except Exception as exc:
            print(f"  FAILED: {exc}")

    print("\n--- All exercises attempted. ---")


# Uncomment to run tests:
# asyncio.run(run_all_tests())


"""
LEARNING OBJECTIVES CHECKLIST

After completing these exercises, you should be comfortable with:

Model Definitions (Exercise 1):
- [ ] DeclarativeBase and Mapped[] / mapped_column() syntax
- [ ] One-to-many relationships with back_populates and cascade
- [ ] Many-to-many via association Table
- [ ] ForeignKey with ondelete behavior

Repository Pattern (Exercise 2):
- [ ] Generic[ModelT] typing for reusable classes
- [ ] session.get() vs select() for primary key lookups
- [ ] flush() vs commit() and why repositories use flush()
- [ ] setattr() for dynamic attribute updates

Cursor Pagination (Exercise 3):
- [ ] WHERE id > cursor vs OFFSET for pagination
- [ ] Fetching size+1 rows to detect next page
- [ ] Building stable cursor values

Query Composition (Exercise 4):
- [ ] Dynamic filter building with conditional .where() clauses
- [ ] or_() for combining conditions
- [ ] .join() for filtering by related model attributes
- [ ] selectinload() for eager loading in async

Bulk Operations (Exercise 5):
- [ ] Core insert().values() vs ORM session.add()
- [ ] Performance difference between single-row and multi-row inserts
- [ ] When to use Core API vs ORM API
"""

# 02 – Authorization and RBAC

## Role-Based Access Control (RBAC)

### Database Model

```python
from sqlalchemy import Table, Column, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

user_roles = Table("user_roles", Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
)
role_permissions = Table("role_permissions", Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    permissions: Mapped[list[Permission]] = relationship(secondary=role_permissions, back_populates="roles")

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # e.g., "posts:write"
    roles: Mapped[list[Role]] = relationship(secondary=role_permissions, back_populates="permissions")
```

### Role Check Dependency (Factory Pattern)

```python
from sqlalchemy.orm import selectinload

# Simple role check using inline role field
def require_role(*roles: str):
    async def checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return checker

@router.get("/admin/dashboard")
async def admin_dashboard(user: User = Depends(require_role("admin", "superadmin"))):
    ...

# Full RBAC with many-to-many roles table
def require_role(*role_names: str):
    async def _check_role(
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        stmt = select(User).options(selectinload(User.roles)).where(User.id == current_user.id)
        user = (await session.execute(stmt)).scalar_one()
        if not {r.name for r in user.roles}.intersection(role_names):
            raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(role_names)}")
        return user
    return _check_role

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: uuid.UUID, user: User = Depends(require_role("admin"))):
    ...
```

### Permission Check Dependency

```python
def require_permission(*permission_names: str):
    async def checker(user: User = Depends(get_current_active_user),
                      session: AsyncSession = Depends(get_session)) -> User:
        stmt = (select(User)
                .options(selectinload(User.roles).selectinload(Role.permissions))
                .where(User.id == user.id))
        user = (await session.execute(stmt)).scalar_one()
        user_perms = {p.name for r in user.roles for p in r.permissions}
        if not set(permission_names).issubset(user_perms):
            raise HTTPException(status_code=403, detail="Missing permissions")
        return user
    return checker

@router.post("/posts")
async def create_post(user: User = Depends(require_permission("posts:write"))): ...

def require_permission(*perms: str):
    async def _check(
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        stmt = (select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                .where(User.id == current_user.id))
        user = (await session.execute(stmt)).scalar_one()
        user_perms = {p.name for r in user.roles for p in r.permissions}
        missing = set(perms) - user_perms
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing: {', '.join(missing)}")
        return user
    return _check
```

---

## OAuth2 Scopes

OAuth2 scopes provide a fine-grained mechanism to restrict what an access token can do.

```python
# Define scopes on the OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={
        "users:read": "Read user profiles",
        "users:write": "Create and modify users",
        "posts:read": "Read posts",
        "posts:write": "Create and modify posts",
        "admin": "Full administrative access",
    },
)

# Check scopes in the dependency
async def get_current_user(
    security_scopes: SecurityScopes,  # Auto-populated by FastAPI
    token: str = Depends(oauth2_scheme),
):
    payload = decode_token(token)
    for scope in security_scopes.scopes:
        if scope not in payload.get("scopes", []):
            raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")
    ...

# Require scopes on endpoints
@router.get("/users")
async def list_users(
    user: User = Security(get_current_active_user, scopes=["users:read"]),
):
    ...
```

### Hierarchical Scopes

```python
SCOPE_HIERARCHY = {
    "admin": ["users:read", "users:write", "posts:read", "posts:write", "admin"],
    "users:write": ["users:read", "users:write"],
    "posts:write": ["posts:read", "posts:write"],
}

def expand_scopes(granted: list[str]) -> set[str]:
    expanded = set()
    for scope in granted:
        expanded.update(SCOPE_HIERARCHY.get(scope, [scope]))
    return expanded

# Use in token creation to expand scopes before encoding
```

### Per-Resource Scopes

```python
# e.g., "org:123:posts:write" = write posts in organization 123
async def check_resource_scope(required: str, org_id: str, token_scopes: list[str]) -> bool:
    if required in token_scopes:
        return True
    return f"org:{org_id}:{required}" in token_scopes
```

---

## Resource-Level Authorization

```python
class ResourceAuthorizer:
    def __init__(self, model, owner_field: str = "author_id"):
        self.model = model
        self.owner_field = owner_field

    async def get_or_403(self, resource_id, current_user, session, *, allow_roles=None):
        resource = await session.get(self.model, resource_id)
        if not resource:
            raise HTTPException(status_code=404)
        is_owner = getattr(resource, self.owner_field) == current_user.id
        is_privileged = bool(allow_roles and {r.name for r in current_user.roles} & allow_roles)
        if not is_owner and not is_privileged:
            raise HTTPException(status_code=403)
        return resource

post_auth = ResourceAuthorizer(Post)

@router.put("/posts/{post_id}")
async def update_post(post_id: uuid.UUID, data: PostUpdate,
    user: User = Depends(require_permission("posts:write")),
    session: AsyncSession = Depends(get_session)):
    post = await post_auth.get_or_403(post_id, user, session, allow_roles={"admin"})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    await session.flush()
    return PostResponse.model_validate(post)
```

---

## API Key Management

```python
import hashlib, secrets
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def generate_api_key() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()

class ApiKey(TimestampMixin, Base):
    __tablename__ = "api_keys"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    hashed_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    user: Mapped[User] = relationship(back_populates="api_keys")

async def get_api_key_user(
    api_key: str | None = Security(api_key_header),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if not api_key:
        return None
    hashed = hashlib.sha256(api_key.encode()).hexdigest()
    stmt = (select(ApiKey).options(joinedload(ApiKey.user))
            .where(ApiKey.hashed_key == hashed, ApiKey.is_active == True))
    key_obj = (await session.execute(stmt)).scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=401, detail="Invalid API key")
    key_obj.last_used_at = datetime.now(timezone.utc)
    return key_obj.user

# Combined auth: accept either JWT or API key
async def get_authenticated_user(
    jwt_user: User | None = Depends(get_current_user_optional),
    api_key_user: User | None = Depends(get_api_key_user),
) -> User:
    user = jwt_user or api_key_user
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

### Key Rotation

```python
@router.post("/api-keys/rotate/{key_id}")
async def rotate_api_key(key_id: uuid.UUID, user: User = Depends(get_current_active_user),
                          session: AsyncSession = Depends(get_session)):
    old = await session.get(ApiKey, key_id)
    if not old or old.user_id != user.id:
        raise HTTPException(status_code=404)
    old.is_active = False
    raw, hashed = generate_api_key()
    session.add(ApiKey(name=old.name, hashed_key=hashed, user_id=user.id, scopes=old.scopes))
    await session.flush()
    return {"key": raw, "message": "Store securely. Will not be shown again."}
```

---

## Row-Level Security (PostgreSQL RLS)

PostgreSQL RLS enforces access at the database level — defense in depth:

```python
# Alembic migration
def upgrade() -> None:
    op.execute("ALTER TABLE posts ENABLE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY posts_user_isolation ON posts
        USING (author_id = current_setting('app.current_user_id')::uuid)""")
    op.execute("""CREATE POLICY posts_admin_access ON posts
        USING (current_setting('app.current_user_role') = 'admin')""")

# FastAPI dependency
async def get_rls_session(user: User = Depends(get_current_active_user)):
    async with async_session() as session:
        await session.execute(text(f"SET app.current_user_id = '{user.id}'"))
        await session.execute(text(f"SET app.current_user_role = '{user.role}'"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Trade-offs:** Defense in depth and works for any DB client. But harder to debug (silent row
filtering), performance impact (per-row policy evaluation), and complex testing.

---

## Security Headers

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

# CORS -- never use allow_origins=["*"] with allow_credentials=True
app.add_middleware(CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Cookie settings: httponly=True, secure=True, samesite="lax", max_age=900
```

---

## Key Takeaways

- RBAC: roles group permissions; `require_role` and `require_permission` factory dependencies.
- OAuth2 scopes are token-bound; `SecurityScopes` auto-populates from `Security()` calls.
- Resource-level auth (owner check + role override) is separate from RBAC — implement both.
- API keys: hash with SHA-256 before storing; never store raw keys in the database.
- Combined auth (JWT OR API key) uses two optional sub-dependencies merged in a parent.
- PostgreSQL RLS provides a second layer of enforcement at the database level.

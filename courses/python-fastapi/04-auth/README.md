# Module 04: Authentication & Authorization

## Overview

Auth in FastAPI is built on its dependency injection system. Unlike Express middleware
(passport.js) or NestJS guards, FastAPI declares auth as a dependency parameter -- making the
auth flow visible in the function signature and fully type-checked.

This module covers JWT-based stateless auth, OAuth2 flows, RBAC, fine-grained permissions,
API keys, social login, and cookie-based sessions.

---

## OAuth2 with Password/Bearer Flow

```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Tells Swagger the token URL; extracts Authorization: Bearer <token> from requests
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
```

| Express/Passport | FastAPI |
|-----------------|---------|
| `passport.use(new JwtStrategy(...))` | `OAuth2PasswordBearer(tokenUrl=...)` |
| `passport.authenticate('jwt')` middleware | `Depends(get_current_user)` parameter |
| `req.user` | Typed function parameter |

### Token Endpoint

```python
@router.post("/auth/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    """OAuth2PasswordRequestForm expects username, password as form fields (not JSON)."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401, detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": create_access_token(data={"sub": str(user.id), "scopes": form_data.scopes}),
        "refresh_token": create_refresh_token(data={"sub": str(user.id)}),
        "token_type": "bearer",
    }

async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user
```

---

## JWT Handling with python-jose

```bash
pip install "python-jose[cryptography]" passlib[bcrypt]
```

### Token Creation and Verification

```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = "your-secret-key-from-env"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    scopes: list[str] = []
    type: str = "access"

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> TokenPayload:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return TokenPayload(**payload)
```

### Token Refresh with Rotation

```python
@router.post("/auth/token/refresh")
async def refresh_token(refresh_token: str, session: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.type != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    # Check revocation (DB or Redis)
    if await is_token_revoked(session, refresh_token):
        await revoke_all_user_tokens(session, payload.sub)  # Potential theft
        raise HTTPException(status_code=401, detail="Token revoked")

    await revoke_token(session, refresh_token)  # Revoke old
    return {
        "access_token": create_access_token(data={"sub": payload.sub}),
        "refresh_token": create_refresh_token(data={"sub": payload.sub}),
        "token_type": "bearer",
    }
```

---

## Dependency-Based Auth

### The `get_current_user` Chain

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import SecurityScopes

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={
        "users:read": "Read user info", "users:write": "Modify users",
        "posts:read": "Read posts", "posts:write": "Modify posts",
        "admin": "Full admin access",
    },
)

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    authenticate_value = f'Bearer scope="{security_scopes.scope_str}"' if security_scopes.scopes else "Bearer"
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials",
                            headers={"WWW-Authenticate": authenticate_value})
    user = await session.get(User, payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    for scope in security_scopes.scopes:
        if scope not in payload.scopes:
            raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")
    return user

async def get_current_active_user(
    current_user: User = Security(get_current_user, scopes=[]),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return current_user
```

### Using Auth in Routes

```python
@router.get("/users/me")
async def read_current_user(user: User = Depends(get_current_active_user)):
    return UserResponse.model_validate(user)

@router.get("/admin/users")
async def admin_list_users(
    user: User = Security(get_current_active_user, scopes=["admin"]),
    session: AsyncSession = Depends(get_session),
):
    return [UserResponse.model_validate(u) for u in (await session.execute(select(User))).scalars()]

@router.put("/posts/{post_id}")
async def update_post(
    post_id: uuid.UUID, data: PostUpdate,
    user: User = Security(get_current_active_user, scopes=["posts:write"]),
    session: AsyncSession = Depends(get_session),
):
    post = await session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404)
    if post.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not your post")
    ...
```

---

## Role-Based Access Control (RBAC)

### Database Model

```python
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

### RBAC Dependencies

```python
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

def require_permission(*permission_names: str):
    async def _check(
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        stmt = (select(User).options(selectinload(User.roles).selectinload(Role.permissions))
                .where(User.id == current_user.id))
        user = (await session.execute(stmt)).scalar_one()
        user_perms = {p.name for r in user.roles for p in r.permissions}
        missing = set(permission_names) - user_perms
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing: {', '.join(missing)}")
        return user
    return _check

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: uuid.UUID, user: User = Depends(require_role("admin"))):
    ...
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

## Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

For higher security (banking, healthcare), use argon2id:
`CryptContext(schemes=["argon2"], argon2__memory_cost=65536, argon2__time_cost=3, argon2__parallelism=4)`

---

## Social Auth (OAuth2 Authorization Code Flow)

```python
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET = "...", "..."
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"

@router.get("/auth/google/login")
async def google_login():
    params = {"client_id": GOOGLE_CLIENT_ID, "redirect_uri": GOOGLE_REDIRECT_URI,
              "response_type": "code", "scope": "openid email profile", "access_type": "offline"}
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

@router.get("/auth/google/callback")
async def google_callback(code: str, session: AsyncSession = Depends(get_session)):
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        tokens = (await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code, "grant_type": "authorization_code", "redirect_uri": GOOGLE_REDIRECT_URI,
        })).json()
        # Get user info
        userinfo = (await client.get("https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"})).json()

    # Find or create user
    user = (await session.execute(select(User).where(User.email == userinfo["email"]))).scalar_one_or_none()
    if not user:
        user = User(email=userinfo["email"], name=userinfo.get("name", ""), provider="google",
                     provider_id=userinfo["id"])
        session.add(user)
        await session.flush()

    return {"access_token": create_access_token(data={"sub": str(user.id)}),
            "refresh_token": create_refresh_token(data={"sub": str(user.id)}), "token_type": "bearer"}
```

---

## CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://app.example.com"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"], max_age=3600,
)
```

**Common mistake:** `allow_origins=["*"]` with `allow_credentials=True` is invalid per the
CORS spec. The browser rejects it. List specific origins when using credentials.

---

## Cookie-Based Auth

```python
@router.post("/auth/login")
async def login_cookie(form_data: OAuth2PasswordRequestForm = Depends(),
                        response: Response = None, session: AsyncSession = Depends(get_session)):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401)
    response.set_cookie(key="access_token", value=create_access_token(data={"sub": str(user.id)}),
        httponly=True, secure=True, samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, domain=".example.com")
    return {"message": "Login successful"}

async def get_current_user_from_cookie(
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not access_token:
        raise HTTPException(status_code=401)
    payload = decode_token(access_token)
    user = await session.get(User, payload.sub)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

---

## Interview Questions

### Conceptual

1. **Authentication vs authorization in FastAPI?**

   Authentication = "who are you?" (JWT/API key/session). Authorization = "what can you do?"
   (scopes/roles/permissions). FastAPI uses `Security` dependencies for auth, layered
   dependencies for authz: `OAuth2PasswordBearer` -> `get_current_user` ->
   `get_current_active_user` -> `require_role("admin")`.

2. **Why short-lived access tokens + refresh tokens?**

   Short access tokens (15 min) limit damage if stolen; stateless (no DB lookup). Refresh
   tokens are long-lived but require DB lookup for revocation. Separates fast path (signature
   check) from secure path (revocation check). Reuse detection: if a refresh token is used
   twice, revoke all tokens for that user.

3. **OAuth2 Password flow vs Authorization Code flow?**

   Password: client sends credentials directly. First-party clients only. Authorization Code:
   redirect to provider, exchange code for tokens server-side. For third-party/social login.
   Client never sees user credentials.

4. **How to revoke stateless JWTs?**

   Blocklist in Redis (JTI with TTL); short expiration + refresh rotation; token versioning
   (`security_stamp` on User model, compare on every validation).

### Practical

5. **Implement a dependency accepting both JWT and API key.** Make both sub-dependencies
   return `None` on failure, combine in parent that raises only if both fail. See
   `get_authenticated_user` above.

6. **RBAC with role inheritance.** Add `parent_id` FK on Role. Recursively collect
   permissions from role and all ancestors via `all_permissions()` method.

7. **Rate-limit login attempts.** Use Redis INCR with TTL per IP key and per username key.
   IP limit: 20/15min. User limit: 5/15min.

### System Design

8. **Multi-tenant SaaS auth.** `OrganizationMembership(user_id, org_id, role)`. JWT has
   `sub=user_id` only. `X-Organization-ID` header per request. Auth dependency validates JWT,
   loads membership for specified org, checks org-specific role/permissions.

9. **"Log out everywhere."** Store `security_stamp` on User. Include in JWT. On validation,
   compare stamps. Regenerate stamp = all tokens invalid. Trade-off: DB read per request
   (cache in Redis with short TTL).

10. **localStorage vs httpOnly cookies for SPA tokens.** localStorage: vulnerable to XSS,
    simple, works cross-origin. httpOnly cookies: immune to XSS, needs CSRF protection
    (SameSite=Lax), complex for cross-origin. Recommendation: cookies for web, Authorization
    header for mobile. Support both in backend.

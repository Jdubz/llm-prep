# Module 04 Deep Dive: Advanced Auth Patterns

## OIDC Integration with Keycloak/Auth0

OpenID Connect (OIDC) is an identity layer on top of OAuth2. Instead of building your own user
management, you delegate authentication to an identity provider (IdP) and receive standardized
identity tokens.

### Generic OIDC Verifier

```python
import httpx
from jose import jwt

class OIDCVerifier:
    def __init__(self, issuer: str, jwks_url: str, client_id: str):
        self.issuer = issuer
        self.jwks_url = jwks_url
        self.client_id = client_id
        self._jwks_cache: dict | None = None

    async def _get_jwks(self) -> dict:
        if self._jwks_cache is None:
            async with httpx.AsyncClient() as client:
                self._jwks_cache = (await client.get(self.jwks_url)).json()
        return self._jwks_cache

    async def verify_token(self, token: str) -> dict:
        jwks = await self._get_jwks()
        kid = jwt.get_unverified_header(token).get("kid")
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key is None:
            self._jwks_cache = None  # Key rotation; clear and retry
            jwks = await self._get_jwks()
            key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key is None:
            raise ValueError("No matching key found")
        return jwt.decode(token, key, algorithms=["RS256"],
                          audience=self.client_id, issuer=self.issuer)
```

### Keycloak / Auth0 Configuration

```python
# Keycloak
keycloak_verifier = OIDCVerifier(
    issuer="https://keycloak.example.com/realms/my-app",
    jwks_url="https://keycloak.example.com/realms/my-app/protocol/openid-connect/certs",
    client_id="fastapi-backend",
)

# Auth0
auth0_verifier = OIDCVerifier(
    issuer="https://your-tenant.auth0.com/",
    jwks_url="https://your-tenant.auth0.com/.well-known/jwks.json",
    client_id="your-client-id",
)
```

### FastAPI Dependency

```python
async def get_oidc_user(token: str = Depends(oauth2_scheme),
                         session: AsyncSession = Depends(get_session)) -> User:
    try:
        payload = await oidc_verifier.verify_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid OIDC token")

    sub = payload["sub"]
    stmt = select(User).where(User.provider_id == sub, User.provider == "keycloak")
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        user = User(email=payload.get("email"), name=payload.get("name", ""),
                     provider="keycloak", provider_id=sub)
        session.add(user)
        await session.flush()
    return user
```

### OIDC Discovery

Both Keycloak and Auth0 expose `{issuer}/.well-known/openid-configuration` that provides all
endpoints (authorization, token, userinfo, jwks_uri, scopes_supported).

---

## Mutual TLS (mTLS)

For service-to-service authentication where both sides present certificates:

```python
async def get_mtls_identity(request: Request) -> str:
    """Extract client identity from mTLS cert (forwarded by reverse proxy)."""
    client_cert_dn = request.headers.get("X-Client-Cert-DN")
    if not client_cert_dn:
        raise HTTPException(status_code=401, detail="Client certificate required")
    parts = dict(item.split("=", 1) for item in client_cert_dn.split(",") if "=" in item)
    service_name = parts.get("CN")
    if not service_name:
        raise HTTPException(status_code=401, detail="Invalid certificate")
    return service_name

ALLOWED_SERVICES = {
    "payment-service": ["orders:read", "orders:write"],
    "notification-service": ["users:read"],
}

async def authorize_service(service: str = Depends(get_mtls_identity)):
    perms = ALLOWED_SERVICES.get(service)
    if perms is None:
        raise HTTPException(status_code=403, detail=f"Unknown service: {service}")
    return {"service": service, "permissions": perms}
```

---

## Custom Authentication Backends

When you need multiple auth methods (JWT, API key, cookie, mTLS) with a unified interface:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AuthResult:
    user_id: str
    auth_method: str
    scopes: list[str]

class AuthBackend(ABC):
    @abstractmethod
    async def authenticate(self, request: Request) -> AuthResult | None: ...

class JWTBackend(AuthBackend):
    async def authenticate(self, request: Request) -> AuthResult | None:
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return None
        try:
            payload = decode_token(auth.split(" ", 1)[1])
            return AuthResult(user_id=payload.sub, auth_method="jwt", scopes=payload.scopes)
        except Exception:
            return None

class APIKeyBackend(AuthBackend):
    async def authenticate(self, request: Request) -> AuthResult | None:
        key = request.headers.get("X-API-Key")
        if not key:
            return None
        # ... lookup and validate
        return AuthResult(user_id=str(key_obj.user_id), auth_method="api_key", scopes=key_obj.scopes)

class CompositeAuthenticator:
    def __init__(self, backends: list[AuthBackend]):
        self.backends = backends

    async def authenticate(self, request: Request) -> AuthResult:
        for backend in self.backends:
            result = await backend.authenticate(request)
            if result:
                return result
        raise HTTPException(status_code=401, detail="Authentication required")

authenticator = CompositeAuthenticator([JWTBackend(), APIKeyBackend()])

async def get_auth_result(request: Request) -> AuthResult:
    return await authenticator.authenticate(request)
```

---

## Row-Level Security

PostgreSQL RLS enforces access at the database level -- defense in depth:

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

## Audit Logging Patterns

### SQLAlchemy Event-Based Audit

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(100))
    record_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(10))  # INSERT, UPDATE, DELETE
    changes: Mapped[dict] = mapped_column(JSON, default={})
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

@event.listens_for(AsyncSession, "before_flush")
def audit_flush(session, flush_context, instances):
    for obj in session.new:
        if hasattr(obj, "__tablename__") and obj.__tablename__ != "audit_logs":
            session.add(AuditLog(table_name=obj.__tablename__,
                record_id=str(getattr(obj, "id", "?")), action="INSERT",
                changes=_serialize(obj), user_id=session.info.get("current_user_id")))

    for obj in session.dirty:
        if hasattr(obj, "__tablename__") and obj.__tablename__ != "audit_logs":
            changes = {}
            for attr in inspect(obj).attrs:
                hist = attr.history
                if hist.has_changes():
                    changes[attr.key] = {"old": hist.deleted[0] if hist.deleted else None,
                                         "new": hist.added[0] if hist.added else None}
            if changes:
                session.add(AuditLog(table_name=obj.__tablename__,
                    record_id=str(getattr(obj, "id", "?")), action="UPDATE",
                    changes=changes, user_id=session.info.get("current_user_id")))

    for obj in session.deleted:
        if hasattr(obj, "__tablename__") and obj.__tablename__ != "audit_logs":
            session.add(AuditLog(table_name=obj.__tablename__,
                record_id=str(getattr(obj, "id", "?")), action="DELETE",
                changes=_serialize(obj), user_id=session.info.get("current_user_id")))
```

---

## OAuth2 Scopes Deep Dive

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

## Token Revocation Strategies

### Strategy 1: Redis Blocklist

```python
import redis.asyncio as redis
token_blocklist = redis.from_url("redis://localhost")

async def revoke_token(token: str, payload: TokenPayload):
    remaining = int((payload.exp - datetime.now(timezone.utc)).total_seconds())
    if remaining > 0:
        await token_blocklist.setex(f"revoked:{token}", remaining, "1")

async def is_token_revoked(token: str) -> bool:
    return await token_blocklist.exists(f"revoked:{token}") > 0
```

### Strategy 2: Token Family Tracking

Track refresh token families to detect theft. Each family has a chain of tokens. If a token
is used twice (reuse = theft), revoke the entire family:

```python
class RefreshTokenFamily(Base):
    __tablename__ = "refresh_token_families"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    is_revoked: Mapped[bool] = mapped_column(default=False)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("refresh_token_families.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    is_used: Mapped[bool] = mapped_column(default=False)

async def rotate_refresh_token(old_token: str, session: AsyncSession):
    old_hash = hashlib.sha256(old_token.encode()).hexdigest()
    old_record = (await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == old_hash)
    )).scalar_one_or_none()
    if not old_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if old_record.is_used:
        # Reuse detected -- revoke entire family (potential theft)
        family = await session.get(RefreshTokenFamily, old_record.family_id)
        family.is_revoked = True
        raise HTTPException(status_code=401, detail="Token reuse detected. Sessions revoked.")
    old_record.is_used = True
    # Issue new token in same family
    new_raw = secrets.token_urlsafe(32)
    session.add(RefreshToken(family_id=old_record.family_id,
                              token_hash=hashlib.sha256(new_raw.encode()).hexdigest()))
    await session.flush()
    return new_raw
```

---

## Session Management Alternatives

### Server-Side Sessions with Redis

```python
import redis.asyncio as redis
import json

session_store = redis.from_url("redis://localhost")
SESSION_TTL = 86400  # 24 hours

async def create_session(user_id: str, metadata: dict) -> str:
    session_id = secrets.token_urlsafe(32)
    await session_store.setex(f"session:{session_id}", SESSION_TTL,
        json.dumps({"user_id": user_id, **metadata}))
    return session_id

async def get_session_data(session_id: str) -> dict | None:
    data = await session_store.get(f"session:{session_id}")
    if not data:
        return None
    await session_store.expire(f"session:{session_id}", SESSION_TTL)  # Sliding expiration
    return json.loads(data)

async def destroy_session(session_id: str):
    await session_store.delete(f"session:{session_id}")

async def destroy_all_user_sessions(user_id: str):
    sids = await session_store.smembers(f"user_sessions:{user_id}")
    if sids:
        await session_store.delete(*[f"session:{s.decode()}" for s in sids],
                                    f"user_sessions:{user_id}")
```

### JWT vs Server-Side Sessions

| Aspect | JWT | Server-Side Session |
|--------|-----|-------------------|
| Storage | Client | Server (Redis/DB) |
| Revocation | Hard (blocklist) | Instant (delete key) |
| Scalability | Excellent (stateless) | Requires shared store |
| Offline validation | Yes | No |
| Cross-service auth | Easy (verify signature) | Hard (shared store) |
| Best for | APIs, microservices | Web apps needing instant revocation |

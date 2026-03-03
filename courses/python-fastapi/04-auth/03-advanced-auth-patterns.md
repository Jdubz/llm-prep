# 03 – Advanced Auth Patterns

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

## Server-Side Sessions with Redis

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

---

## Interview Questions

### Conceptual

**1. Authentication vs authorization in FastAPI?**

Authentication = "who are you?" (JWT/API key/session). Authorization = "what can you do?"
(scopes/roles/permissions). FastAPI uses `Security` dependencies for auth, layered
dependencies for authz: `OAuth2PasswordBearer` → `get_current_user` →
`get_current_active_user` → `require_role("admin")`.

**2. Why short-lived access tokens + refresh tokens?**

Short access tokens (15 min) limit damage if stolen; stateless (no DB lookup). Refresh
tokens are long-lived but require DB lookup for revocation. Separates fast path (signature
check) from secure path (revocation check). Reuse detection: if a refresh token is used
twice, revoke all tokens for that user.

**3. OAuth2 Password flow vs Authorization Code flow?**

Password: client sends credentials directly. First-party clients only. Authorization Code:
redirect to provider, exchange code for tokens server-side. For third-party/social login.
Client never sees user credentials.

**4. How to revoke stateless JWTs?**

Blocklist in Redis (JTI with TTL); short expiration + refresh rotation; token versioning
(`security_stamp` on User model, compare on every validation).

### Practical

**5. Implement a dependency accepting both JWT and API key.** Make both sub-dependencies
return `None` on failure, combine in parent that raises only if both fail. See
`get_authenticated_user` above.

**6. RBAC with role inheritance.** Add `parent_id` FK on Role. Recursively collect
permissions from role and all ancestors via `all_permissions()` method.

**7. Rate-limit login attempts.** Use Redis INCR with TTL per IP key and per username key.
IP limit: 20/15min. User limit: 5/15min.

### System Design

**8. Multi-tenant SaaS auth.** `OrganizationMembership(user_id, org_id, role)`. JWT has
`sub=user_id` only. `X-Organization-ID` header per request. Auth dependency validates JWT,
loads membership for specified org, checks org-specific role/permissions.

**9. "Log out everywhere."** Store `security_stamp` on User. Include in JWT. On validation,
compare stamps. Regenerate stamp = all tokens invalid. Trade-off: DB read per request
(cache in Redis with short TTL).

**10. localStorage vs httpOnly cookies for SPA tokens.** localStorage: vulnerable to XSS,
simple, works cross-origin. httpOnly cookies: immune to XSS, needs CSRF protection
(SameSite=Lax), complex for cross-origin. Recommendation: cookies for web, Authorization
header for mobile. Support both in backend.

---

## Key Takeaways

- OIDC delegates identity management to an IdP; verify tokens against the IdP's JWKS endpoint.
- mTLS is the gold standard for service-to-service authentication in production microservices.
- Token family tracking detects refresh token theft and revokes all sessions on reuse.
- Redis blocklist enables near-instant JWT revocation at the cost of a Redis lookup per request.
- Audit logs should be written atomically with the transaction they record, using SQLAlchemy events.
- JWT is better for APIs/microservices; server-side sessions are better for web apps needing instant logout.

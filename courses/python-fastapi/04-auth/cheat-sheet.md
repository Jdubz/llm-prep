# Module 04 Cheat Sheet: Authentication & Authorization

## JWT Flow Diagram

```
Client                     FastAPI                    Database
  |-- POST /auth/token -->|-- lookup user ---------->|
  |   (user, pass)        |-- verify_password        |
  |<-- {access, refresh} -|-- create tokens          |
  |                        |                          |
  |-- GET /resource ------>|-- decode_token(at)       |
  |   Bearer <access>     |-- session.get(User, sub)>|
  |<-- 200 + data --------|<-- user ------------------|
  |                        |                          |
  |-- POST /refresh ------>|-- decode_token(rt)       |
  |   {refresh_token}     |-- check revocation ------>|
  |<-- {new access,       |-- revoke old, issue new  |
  |     new refresh}       |                          |
```

## FastAPI Auth Dependency Template

```python
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Layer 1: Extract and validate token, return User
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Layer 2: Ensure user is active
async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user

# Layer 3: Role check (factory pattern)
def require_role(*roles: str):
    async def checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return checker

# Usage
@router.get("/admin/dashboard")
async def admin_dashboard(user: User = Depends(require_role("admin", "superadmin"))):
    ...
```

## RBAC Pattern Template

```python
# Tables: user_roles (user_id, role_id), role_permissions (role_id, permission_id)
# Models: Role(id, name, permissions via M2M), Permission(id, name)

def require_permission(*perms: str):
    async def checker(user: User = Depends(get_current_active_user),
                      session: AsyncSession = Depends(get_session)) -> User:
        stmt = (select(User)
                .options(selectinload(User.roles).selectinload(Role.permissions))
                .where(User.id == user.id))
        user = (await session.execute(stmt)).scalar_one()
        user_perms = {p.name for r in user.roles for p in r.permissions}
        if not set(perms).issubset(user_perms):
            raise HTTPException(status_code=403, detail="Missing permissions")
        return user
    return checker

@router.post("/posts")
async def create_post(user: User = Depends(require_permission("posts:write"))): ...
```

## Password Hashing Setup

```python
from passlib.context import CryptContext

# bcrypt (standard)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# argon2id (higher security)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto",
    argon2__memory_cost=65536, argon2__time_cost=3, argon2__parallelism=4)

# Hash and verify
hashed = pwd_context.hash("plaintext_password")
is_valid = pwd_context.verify("plaintext_password", hashed)
```

## OAuth2 Scopes Reference

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

# Require scopes on endpoints using Security()
from fastapi import Security

@router.get("/users")
async def list_users(
    user: User = Security(get_current_active_user, scopes=["users:read"]),
):
    ...

@router.delete("/users/{id}")
async def delete_user(
    user: User = Security(get_current_active_user, scopes=["admin"]),
):
    ...

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
```

## Security Headers Checklist

```python
# Middleware for security headers
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

## Quick Reference: Auth Method Selection

| Scenario | Auth Method | Token Storage |
|----------|------------|---------------|
| SPA + API (same domain) | JWT in httpOnly cookie | Cookie |
| SPA + API (cross-domain) | JWT in Authorization header | Memory (not localStorage) |
| Mobile app | JWT in Authorization header | Secure storage (Keychain/Keystore) |
| Server-to-server | mTLS or API key | Certificate/env var |
| Third-party integration | OAuth2 Authorization Code | Server-side session |
| Microservices (internal) | mTLS or signed JWT | Certificate/service mesh |
| CLI tool | OAuth2 Device Code or API key | OS credential store |

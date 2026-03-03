# 01 – Authentication Basics

## Overview

Auth in FastAPI is built on its dependency injection system. Unlike Express middleware
(passport.js) or NestJS guards, FastAPI declares auth as a dependency parameter — making the
auth flow visible in the function signature and fully type-checked.

This module covers JWT-based stateless auth, password hashing, the login flow, and FastAPI's
built-in security utilities.

| Express/Passport | FastAPI |
|-----------------|---------|
| `passport.use(new JwtStrategy(...))` | `OAuth2PasswordBearer(tokenUrl=...)` |
| `passport.authenticate('jwt')` middleware | `Depends(get_current_user)` parameter |
| `req.user` | Typed function parameter |

---

## OAuth2 with Password/Bearer Flow

```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# Tells Swagger the token URL; extracts Authorization: Bearer <token> from requests
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
```

### JWT Flow

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
    to_encode.update({
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> TokenPayload:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return TokenPayload(**payload)
```

---

## Dependency-Based Auth

### The `get_current_user` Chain

Layer your dependencies for progressively stricter checks:

```python
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

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

# Usage
@router.get("/users/me")
async def read_current_user(user: User = Depends(get_current_active_user)):
    return UserResponse.model_validate(user)
```

### OAuth2 Scopes

```python
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
```

---

## Password Hashing

```python
from passlib.context import CryptContext

# bcrypt (standard)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# argon2id (higher security -- banking, healthcare)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto",
    argon2__memory_cost=65536, argon2__time_cost=3, argon2__parallelism=4)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

---

## Token Refresh with Rotation

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

## Auth Method Selection Reference

| Scenario | Auth Method | Token Storage |
|----------|------------|---------------|
| SPA + API (same domain) | JWT in httpOnly cookie | Cookie |
| SPA + API (cross-domain) | JWT in Authorization header | Memory (not localStorage) |
| Mobile app | JWT in Authorization header | Secure storage (Keychain/Keystore) |
| Server-to-server | mTLS or API key | Certificate/env var |
| Third-party integration | OAuth2 Authorization Code | Server-side session |
| Microservices (internal) | mTLS or signed JWT | Certificate/service mesh |
| CLI tool | OAuth2 Device Code or API key | OS credential store |

---

## Key Takeaways

- FastAPI's DI system makes auth explicit, typed, and testable — declare it in function signatures.
- Layer dependencies: `get_current_user` → `get_current_active_user` → `require_role(...)`.
- Use `Security()` instead of `Depends()` when requiring OAuth2 scopes.
- Short-lived access tokens (15 min) + longer refresh tokens (7 days) is the standard pattern.
- `bcrypt` is standard; use `argon2id` for higher-security applications.
- Never use `allow_origins=["*"]` with `allow_credentials=True` in CORS config.

"""
Module 04: Authentication & Authorization -- Complete Examples
=============================================================
Runnable auth patterns using only stdlib + FastAPI/Pydantic.
No external deps (no python-jose, no passlib, no bcrypt).

Run:  uvicorn examples:app --reload
Docs: http://127.0.0.1:8000/docs
"""
import base64, hashlib, hmac, json, secrets, time
from typing import Optional
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

# =============================================================================
# 1. JWT CREATION & VERIFICATION (manual HS256 -- what python-jose does inside)
# =============================================================================
SECRET_KEY = "super-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding (JWT spec)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64url_decode(s: str) -> bytes:
    """Base64url decode, re-adding padding as needed."""
    s += "=" * (4 - len(s) % 4) if len(s) % 4 else ""
    return base64.urlsafe_b64decode(s)

def create_jwt(payload: dict, secret: str = SECRET_KEY) -> str:
    """Create a JWT: header.payload.signature (each base64url-encoded)."""
    header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"

def decode_jwt(token: str, secret: str = SECRET_KEY) -> dict:
    """Decode and verify a JWT. Raises ValueError on bad signature or expiry."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    header_b64, payload_b64, sig_b64 = parts
    expected = hmac.new(secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise ValueError("Invalid token signature")
    payload = json.loads(_b64url_decode(payload_b64))
    if "exp" in payload and payload["exp"] < time.time():
        raise ValueError("Token has expired")
    return payload

# =============================================================================
# 2. PASSWORD HASHING (PBKDF2 -- stdlib bcrypt-like pattern)
# =============================================================================
def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Hash with random salt via PBKDF2-HMAC-SHA256. Returns 'salt_hex$hash_hex'."""
    if salt is None:
        salt = secrets.token_bytes(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations=100_000)
    return f"{salt.hex()}${pw_hash.hex()}"

def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored salt$hash string (constant-time)."""
    salt_hex, _ = stored.split("$")
    return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex)), stored)

# =============================================================================
# 3. IN-MEMORY USER STORE (replaces a real database)
# =============================================================================
class UserInDB(BaseModel):
    id: str
    username: str
    email: str
    hashed_password: str
    roles: list[str] = ["user"]
    is_active: bool = True
    api_keys: list[str] = []  # hashed keys

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    roles: list[str]

_users_db: dict[str, UserInDB] = {}
_revoked_tokens: set[str] = set()
_sessions: dict[str, dict] = {}  # session_id -> session data

def _get_user_by_username(username: str) -> Optional[UserInDB]:
    return next((u for u in _users_db.values() if u.username == username), None)

# =============================================================================
# 4. TOKEN CREATION HELPERS
# =============================================================================
def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    payload = {**data, "exp": time.time() + expires_minutes * 60, "type": "access", "jti": secrets.token_hex(8)}
    return create_jwt(payload)

def create_refresh_token(data: dict, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS) -> str:
    payload = {**data, "exp": time.time() + expires_days * 86400, "type": "refresh", "jti": secrets.token_hex(8)}
    return create_jwt(payload)

# =============================================================================
# 5. OAUTH2 PASSWORD BEARER DEPENDENCY CHAIN
#    OAuth2PasswordBearer -> decode JWT -> load user -> check role
# =============================================================================
app = FastAPI(title="Auth Examples", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Core auth dependency: extract bearer token, decode JWT, return user."""
    try:
        payload = decode_jwt(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e), headers={"WWW-Authenticate": "Bearer"})
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Expected access token")
    user = _users_db.get(payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user

# =============================================================================
# 6. ROLE-BASED ACCESS CONTROL WITH PERMISSION CHECKING
# =============================================================================
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"users:read", "users:write", "users:delete", "posts:read", "posts:write", "posts:delete"},
    "user":  {"posts:read", "posts:write", "users:read"},
    "viewer": {"posts:read", "users:read"},
}

def require_role(*allowed_roles: str):
    """Dependency factory: user must have at least one of the listed roles."""
    async def _check(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if not set(current_user.roles).intersection(allowed_roles):
            raise HTTPException(status_code=403, detail=f"Requires one of: {', '.join(allowed_roles)}")
        return current_user
    return _check

def require_permission(*permissions: str):
    """Dependency factory: user's roles must collectively grant all listed permissions."""
    async def _check(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        user_perms: set[str] = set()
        for role in current_user.roles:
            user_perms.update(ROLE_PERMISSIONS.get(role, set()))
        missing = set(permissions) - user_perms
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing permissions: {', '.join(missing)}")
        return current_user
    return _check

# =============================================================================
# 7. API KEY AUTHENTICATION
# =============================================================================
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, sha256_hash). Show raw once, store only hash."""
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()

async def get_api_key_user(api_key: Optional[str] = Depends(api_key_header)) -> Optional[UserInDB]:
    """Validate X-API-Key header. Returns None when no key (allows JWT fallback)."""
    if not api_key:
        return None
    hashed = hashlib.sha256(api_key.encode()).hexdigest()
    for user in _users_db.values():
        if hashed in user.api_keys:
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Inactive user")
            return user
    raise HTTPException(status_code=401, detail="Invalid API key")

# =============================================================================
# 8. COOKIE-BASED SESSION PATTERN
# =============================================================================
def create_session(user_id: str) -> str:
    sid = secrets.token_urlsafe(32)
    _sessions[sid] = {"user_id": user_id, "created_at": time.time(), "expires_at": time.time() + 3600}
    return sid

async def get_user_from_cookie(session_id: Optional[str] = Cookie(default=None, alias="session_id")) -> UserInDB:
    """Extract user from a session cookie (httpOnly, server-side session store)."""
    if not session_id or session_id not in _sessions:
        raise HTTPException(status_code=401, detail="No valid session")
    session = _sessions[session_id]
    if session["expires_at"] < time.time():
        del _sessions[session_id]
        raise HTTPException(status_code=401, detail="Session expired")
    user = _users_db.get(session["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# =============================================================================
# 9. ROUTES -- Complete Auth Flow: register -> login -> protected -> refresh
# =============================================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

@app.post("/auth/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest):
    """Register a new user with hashed password."""
    if _get_user_by_username(data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    uid = secrets.token_hex(8)
    user = UserInDB(id=uid, username=data.username, email=data.email,
                    hashed_password=hash_password(data.password))
    _users_db[uid] = user
    return UserResponse(id=user.id, username=user.username, email=user.email, roles=user.roles)

@app.post("/auth/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 password login. Expects form fields: username, password (not JSON)."""
    user = _get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(
        access_token=create_access_token({"sub": user.id, "roles": user.roles}),
        refresh_token=create_refresh_token({"sub": user.id}),
    )

class RefreshRequest(BaseModel):
    refresh_token: str

@app.post("/auth/token/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest):
    """Token rotation: exchange refresh token for new access+refresh pair."""
    try:
        payload = decode_jwt(data.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {e}")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    jti = payload.get("jti", "")
    if jti in _revoked_tokens:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    _revoked_tokens.add(jti)  # revoke old token
    user = _users_db.get(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token({"sub": user.id, "roles": user.roles}),
        refresh_token=create_refresh_token({"sub": user.id}),
    )

# --- Protected routes ---

@app.get("/users/me", response_model=UserResponse)
async def read_current_user(user: UserInDB = Depends(get_current_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email, roles=user.roles)

@app.get("/admin/users", response_model=list[UserResponse])
async def admin_list_users(user: UserInDB = Depends(require_role("admin"))):
    return [UserResponse(id=u.id, username=u.username, email=u.email, roles=u.roles)
            for u in _users_db.values()]

@app.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin: UserInDB = Depends(require_permission("users:delete"))):
    if user_id not in _users_db:
        raise HTTPException(status_code=404, detail="User not found")
    del _users_db[user_id]
    return {"detail": "User deleted"}

# --- API key routes ---

@app.post("/api-keys")
async def create_api_key_endpoint(user: UserInDB = Depends(get_current_user)):
    raw, hashed = generate_api_key()
    user.api_keys.append(hashed)
    return {"key": raw, "message": "Store securely. Will not be shown again."}

@app.get("/api-keys/test")
async def test_api_key_endpoint(user: Optional[UserInDB] = Depends(get_api_key_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Provide X-API-Key header")
    return {"message": f"Hello {user.username}, authenticated via API key"}

# --- Cookie session routes ---

@app.post("/auth/login/cookie")
async def login_cookie(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    user = _get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    response.set_cookie(key="session_id", value=create_session(user.id),
                        httponly=True, secure=True, samesite="lax", max_age=3600)
    return {"message": "Login successful"}

@app.get("/cookie/me", response_model=UserResponse)
async def read_user_from_cookie(user: UserInDB = Depends(get_user_from_cookie)):
    return UserResponse(id=user.id, username=user.username, email=user.email, roles=user.roles)

@app.post("/auth/logout/cookie")
async def logout_cookie(response: Response,
                        session_id: Optional[str] = Cookie(default=None, alias="session_id")):
    if session_id and session_id in _sessions:
        del _sessions[session_id]
    response.delete_cookie("session_id")
    return {"message": "Logged out"}

# =============================================================================
# 10. SELF-TESTS (run with: python examples.py)
# =============================================================================
def test_jwt_roundtrip():
    payload = {"sub": "user123", "roles": ["admin"], "exp": time.time() + 300}
    decoded = decode_jwt(create_jwt(payload))
    assert decoded["sub"] == "user123" and decoded["roles"] == ["admin"]

def test_jwt_expiration():
    token = create_jwt({"sub": "u", "exp": time.time() - 10})
    try:
        decode_jwt(token)
        assert False, "Should have raised"
    except ValueError as e:
        assert "expired" in str(e).lower()

def test_jwt_tamper_detection():
    token = create_jwt({"sub": "user123", "exp": time.time() + 300})
    parts = token.split(".")
    fake = _b64url_encode(json.dumps({"sub": "admin", "exp": time.time() + 300}).encode())
    try:
        decode_jwt(f"{parts[0]}.{fake}.{parts[2]}")
        assert False, "Should have raised"
    except ValueError as e:
        assert "signature" in str(e).lower()

def test_password_hashing():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)

def test_api_key_generation():
    raw, hashed = generate_api_key()
    assert hashlib.sha256(raw.encode()).hexdigest() == hashed

def test_role_permissions():
    assert "users:delete" in ROLE_PERMISSIONS["admin"]
    assert "users:delete" not in ROLE_PERMISSIONS["user"]
    assert "posts:write" not in ROLE_PERMISSIONS["viewer"]

if __name__ == "__main__":
    tests = [("JWT Roundtrip", test_jwt_roundtrip), ("JWT Expiration", test_jwt_expiration),
             ("JWT Tamper Detection", test_jwt_tamper_detection), ("Password Hashing", test_password_hashing),
             ("API Key Generation", test_api_key_generation), ("Role Permissions", test_role_permissions)]
    print("Auth Examples -- Running Tests\n" + "=" * 40)
    for name, fn in tests:
        fn()
        print(f"  PASSED: {name}")
    print(f"\nAll {len(tests)} tests passed.")
    print("Run API: uvicorn examples:app --reload")

"""
Module 04: Authentication & Authorization -- Exercises
======================================================
Complete each exercise by replacing TODO comments with working code.
Only stdlib (hmac, hashlib, json, base64, time, secrets) + FastAPI/Pydantic.

Run tests:  python exercises.py
Run API:    uvicorn exercises:app --reload
"""
import base64, hashlib, hmac, json, secrets, time
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

# =============================================================================
# SHARED UTILITIES (provided -- do not modify)
# =============================================================================
SECRET_KEY = "exercise-secret-key-do-not-use-in-prod"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding (per JWT spec, RFC 7515)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _b64url_decode(s: str) -> bytes:
    """Base64url decode, re-adding padding as needed."""
    s += "=" * (4 - len(s) % 4) if len(s) % 4 else ""
    return base64.urlsafe_b64decode(s)

# --- In-memory user store ---
class UserInDB(BaseModel):
    id: str
    username: str
    email: str
    hashed_password: str
    roles: list[str] = ["user"]
    is_active: bool = True
    api_key_hashes: list[str] = []

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

# Pre-seed test users (admin + viewer)
def _seed(uid, name, email, pw, roles):
    s = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), s, 100_000)
    _users_db[uid] = UserInDB(id=uid, username=name, email=email,
                               hashed_password=f"{s.hex()}${h.hex()}", roles=roles)
_seed("admin-001", "admin", "admin@example.com", "adminpass", ["admin", "user"])
_seed("viewer-001", "viewer", "viewer@example.com", "viewerpass", ["viewer"])

def _get_user_by_username(username: str) -> Optional[UserInDB]:
    return next((u for u in _users_db.values() if u.username == username), None)

def verify_password(password: str, stored: str) -> bool:
    salt_hex, _ = stored.split("$")
    salt = bytes.fromhex(salt_hex)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return hmac.compare_digest(f"{salt_hex}${pw_hash.hex()}", stored)

# =============================================================================
# EXERCISE 1: Implement JWT Token Creation with Expiration
# =============================================================================
# READ FIRST: 01-authentication-basics.md -> "JWT Handling with python-jose"
#   and "Token Refresh with Rotation"
# ALSO SEE:  examples.py -> Section 1 ("JWT CREATION & VERIFICATION") and
#   Section 4 ("TOKEN CREATION HELPERS") for working implementations.
#
# WHY MANUAL JWT? The MD file teaches python-jose (the production approach),
# but this exercise builds JWT from scratch so you understand what libraries
# do internally. Production code should use python-jose or PyJWT.
#
# JWT STRUCTURE (RFC 7519):
#   A JWT is three base64url-encoded parts separated by dots:
#     header.payload.signature
#
#   1. HEADER: JSON object identifying the algorithm and token type:
#        {"alg": "HS256", "typ": "JWT"}
#      Encode with json.dumps(header, separators=(",", ":")) for compact JSON
#      (no spaces), then _b64url_encode() the resulting bytes.
#
#   2. PAYLOAD: JSON object with your claims (sub, exp, roles, etc.).
#      Encode the same way as the header.
#
#   3. SIGNATURE: HMAC-SHA256 of the signing input.
#      signing_input = f"{header_b64}.{payload_b64}"
#      sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
#      Then _b64url_encode() the raw signature bytes.
#
#   Final token = f"{header_b64}.{payload_b64}.{sig_b64}"
#
# IMPORTS NEEDED (already at the top of this file):
#   import hmac, hashlib, json, base64, time, secrets
#
# HELPER FUNCTIONS (provided above -- do not modify):
#   _b64url_encode(data: bytes) -> str
#   _b64url_decode(s: str) -> bytes
# =============================================================================

def create_jwt(payload: dict, secret: str = SECRET_KEY) -> str:
    """Create a JWT (HMAC-SHA256). header.payload.signature, each base64url-encoded.
    Steps: build header {"alg":"HS256","typ":"JWT"}, b64url-encode header+payload JSON
    (compact separators), HMAC-sign, return 3-part dot-separated string."""
    # TODO: Implement JWT creation
    # Step 1: Build the header dict and encode it:
    #   header = {"alg": "HS256", "typ": "JWT"}
    #   header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    # Step 2: Encode the payload dict the same way:
    #   payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    # Step 3: Create signing input and compute HMAC-SHA256:
    #   signing_input = f"{header_b64}.{payload_b64}"
    #   sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    # Step 4: Return the three dot-separated parts:
    #   return f"{signing_input}.{_b64url_encode(sig)}"
    raise NotImplementedError("Complete Exercise 1")

def decode_jwt(token: str, secret: str = SECRET_KEY) -> dict:
    """Decode and verify JWT. Split on ".", recompute HMAC, compare with
    hmac.compare_digest, decode payload, check "exp" claim. Raise ValueError
    on bad signature ("Invalid token signature") or expiry ("Token has expired")."""
    # TODO: Implement JWT verification
    # Step 1: Split token on "." -- expect exactly 3 parts (header, payload, signature)
    # Step 2: Recompute the expected signature:
    #   expected = hmac.new(secret.encode(),
    #       f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    # Step 3: Compare with the provided signature (use hmac.compare_digest for
    #   constant-time comparison to prevent timing attacks):
    #   if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
    #       raise ValueError("Invalid token signature")
    # Step 4: Decode the payload JSON:
    #   payload = json.loads(_b64url_decode(payload_b64))
    # Step 5: Check expiration:
    #   if "exp" in payload and payload["exp"] < time.time():
    #       raise ValueError("Token has expired")
    # Step 6: Return the payload dict
    raise NotImplementedError("Complete Exercise 1")

def create_access_token(data: dict) -> str:
    """Short-lived token. Merge data with exp (ACCESS_TOKEN_EXPIRE_MINUTES*60 from now),
    type="access", jti=secrets.token_hex(8). Call create_jwt()."""
    # TODO: Build payload and call create_jwt()
    # Merge the input data with these additional claims:
    #   payload = {**data,
    #       "exp": time.time() + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    #       "type": "access",
    #       "jti": secrets.token_hex(8)}
    # Then: return create_jwt(payload)
    raise NotImplementedError("Complete Exercise 1")

def create_refresh_token(data: dict) -> str:
    """Long-lived token. Merge data with exp (REFRESH_TOKEN_EXPIRE_DAYS*86400 from now),
    type="refresh", jti=secrets.token_hex(8). Call create_jwt()."""
    # TODO: Build payload and call create_jwt()
    # Same pattern as create_access_token, but with:
    #   "exp": time.time() + REFRESH_TOKEN_EXPIRE_DAYS * 86400
    #   "type": "refresh"
    # The refresh token should live much longer (days vs minutes).
    raise NotImplementedError("Complete Exercise 1")

# =============================================================================
# EXERCISE 2: Build the Auth Dependency Chain (3 layers)
# =============================================================================
# READ FIRST: 01-authentication-basics.md -> "Dependency-Based Auth" and
#   "The get_current_user Chain"
# ALSO SEE:  examples.py -> Section 5 ("OAUTH2 PASSWORD BEARER DEPENDENCY CHAIN")
#   for a working single-layer implementation.
#
# HOW THE DEPENDENCY CHAIN WORKS:
#   FastAPI's Depends() wires functions together so each layer automatically
#   receives the output of the previous layer. The chain looks like this:
#
#     Request
#       -> oauth2_scheme (extracts Bearer token from Authorization header)
#       -> get_current_user(token) [Layer 1: decode JWT, find user]
#       -> get_active_user(user) [Layer 2: check is_active]
#       -> require_role("admin")(user) [Layer 3: check roles]
#
#   When you write a route like:
#     @app.get("/admin")
#     async def admin(user: UserInDB = Depends(require_role("admin"))):
#   FastAPI automatically calls the full chain: extract token -> decode ->
#   find user -> check active -> check role, injecting each result into
#   the next function.
#
# LAYER 1 PATTERN (get_current_user):
#   - Receives token: str from Depends(oauth2_scheme)
#   - Wraps decode_jwt(token) in try/except ValueError
#   - On ValueError: raise HTTPException(status_code=401, detail=str(e),
#       headers={"WWW-Authenticate": "Bearer"})
#   - Check payload.get("type") == "access" (reject refresh tokens)
#   - Look up user: _users_db.get(payload.get("sub"))
#   - User not found: raise HTTPException(status_code=401, detail="User not found")
#
# LAYER 2 PATTERN (get_active_user):
#   - Receives current_user from Depends(get_current_user)
#   - If not current_user.is_active: raise HTTPException(status_code=403,
#       detail="Inactive user")
#   - Otherwise return current_user
#
# LAYER 3 PATTERN (require_role -- dependency factory):
#   require_role is a function that RETURNS a dependency function.
#   def require_role(*allowed_roles):
#       async def _check(user: UserInDB = Depends(get_active_user)) -> UserInDB:
#           if not set(user.roles).intersection(allowed_roles):
#               raise HTTPException(status_code=403, ...)
#           return user
#       return _check
# =============================================================================
app = FastAPI(title="Auth Exercises", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Layer 1: Decode JWT, verify type=="access", look up user by payload["sub"].
    Catch ValueError -> 401. User not found -> 401."""
    # TODO: Implement token validation and user lookup
    # 1. try: payload = decode_jwt(token)
    #    except ValueError as e: raise HTTPException(status_code=401, detail=str(e),
    #        headers={"WWW-Authenticate": "Bearer"})
    # 2. if payload.get("type") != "access": raise HTTPException(401, "Expected access token")
    # 3. user = _users_db.get(payload.get("sub"))
    # 4. if user is None: raise HTTPException(401, "User not found")
    # 5. return user
    raise NotImplementedError("Complete Exercise 2")

async def get_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Layer 2: Reject inactive users (403 "Inactive user")."""
    # TODO: Check is_active
    # if not current_user.is_active:
    #     raise HTTPException(status_code=403, detail="Inactive user")
    # return current_user
    raise NotImplementedError("Complete Exercise 2")

def require_role(*allowed_roles: str):
    """Layer 3 (factory): inner async dep on get_active_user, check set intersection
    of user.roles & allowed_roles, raise 403 if empty, return user."""
    # TODO: Define and return inner dependency function
    # Define an inner async function that takes user from Depends(get_active_user):
    #   async def _check(user: UserInDB = Depends(get_active_user)) -> UserInDB:
    #       if not set(user.roles).intersection(allowed_roles):
    #           raise HTTPException(status_code=403,
    #               detail=f"Requires one of: {', '.join(allowed_roles)}")
    #       return user
    #   return _check
    raise NotImplementedError("Complete Exercise 2")

# =============================================================================
# EXERCISE 3: Add Role-Based Route Protection
# =============================================================================
# READ FIRST: 02-authorization-and-rbac.md -> "Permission Check Dependency"
#   and "Role Check Dependency (Factory Pattern)"
# ALSO SEE:  examples.py -> Section 6 ("ROLE-BASED ACCESS CONTROL WITH
#   PERMISSION CHECKING") for a working require_permission implementation.
#
# THE ROLE-TO-PERMISSION MAPPING PATTERN:
#   Each role maps to a set of permission strings. A user may have multiple
#   roles, and their effective permissions are the UNION of all role permissions.
#
#   ROLE_PERMISSIONS = {
#       "admin":  {"users:read", "users:write", "users:delete", "posts:read", "posts:write"},
#       "user":   {"posts:read", "posts:write", "users:read"},
#       "viewer": {"posts:read", "users:read"},
#   }
#
#   To check: collect all permissions from each of the user's roles, then
#   compute missing = required_permissions - granted_permissions. If any are
#   missing, deny access with 403.
#
# IMPLEMENTATION PATTERN (same factory pattern as require_role):
#   def require_permission(*permissions):
#       async def _check(user: UserInDB = Depends(get_active_user)) -> UserInDB:
#           granted: set[str] = set()
#           for role in user.roles:
#               granted.update(ROLE_PERMISSIONS.get(role, set()))
#           missing = set(permissions) - granted
#           if missing:
#               raise HTTPException(status_code=403,
#                   detail=f"Missing permissions: {', '.join(missing)}")
#           return user
#       return _check
# =============================================================================
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"users:read", "users:write", "users:delete", "posts:read", "posts:write"},
    "user":  {"posts:read", "posts:write", "users:read"},
    "viewer": {"posts:read", "users:read"},
}

def require_permission(*permissions: str):
    """Dependency factory: collect perms from user's roles via ROLE_PERMISSIONS,
    compute missing = required - granted, raise 403 if any missing."""
    # TODO: Define inner async function, collect perms, check, return user
    # 1. Define inner async function with Depends(get_active_user):
    #    async def _check(user: UserInDB = Depends(get_active_user)) -> UserInDB:
    # 2. Collect granted permissions from all of the user's roles:
    #    granted: set[str] = set()
    #    for role in user.roles:
    #        granted.update(ROLE_PERMISSIONS.get(role, set()))
    # 3. Compute what's missing:
    #    missing = set(permissions) - granted
    # 4. If any missing, raise 403:
    #    if missing:
    #        raise HTTPException(status_code=403,
    #            detail=f"Missing permissions: {', '.join(missing)}")
    # 5. Return the user
    # 6. Return the inner function from require_permission
    raise NotImplementedError("Complete Exercise 3")

# --- Routes (work once Exercises 1-3 are done) ---

@app.post("/auth/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = _get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return TokenResponse(
        access_token=create_access_token({"sub": user.id, "roles": user.roles}),
        refresh_token=create_refresh_token({"sub": user.id}))

@app.get("/users/me", response_model=UserResponse)
async def read_me(user: UserInDB = Depends(get_active_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email, roles=user.roles)

@app.get("/admin/users", response_model=list[UserResponse])
async def list_all_users(user: UserInDB = Depends(require_role("admin"))):
    return [UserResponse(id=u.id, username=u.username, email=u.email, roles=u.roles)
            for u in _users_db.values()]

@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin: UserInDB = Depends(require_permission("users:delete"))):
    if user_id not in _users_db:
        raise HTTPException(status_code=404, detail="User not found")
    del _users_db[user_id]
    return {"detail": "User deleted"}

@app.get("/posts")
async def list_posts(user: UserInDB = Depends(require_permission("posts:read"))):
    return {"posts": [], "viewer": user.username}

# =============================================================================
# EXERCISE 4: Implement API Key Validation with Hashing
# =============================================================================
# READ FIRST: 02-authorization-and-rbac.md -> "API Key Management"
# ALSO SEE:  examples.py -> Section 7 ("API KEY AUTHENTICATION") for working
#   generate_api_key and get_api_key_user implementations.
#
# KEY CONCEPT: Never store raw API keys in the database. Store only the
# SHA-256 hash. When a request arrives with an API key, hash it and compare
# the hash against stored hashes. This way, even if the DB is compromised,
# the raw keys are not exposed.
#
# generate_api_key() pattern:
#   raw = secrets.token_urlsafe(32)     # cryptographically random key
#   hashed = hashlib.sha256(raw.encode()).hexdigest()  # 64-char hex digest
#   return (raw, hashed)
#
# get_api_key_user() pattern:
#   - If api_key is None (no header), return None (allows JWT fallback)
#   - Hash the provided key: hashlib.sha256(api_key.encode()).hexdigest()
#   - Search _users_db for a user whose api_key_hashes list contains the hash
#   - If found and active: return user
#   - If found but inactive: raise HTTPException(403, "Inactive user")
#   - If not found: raise HTTPException(401, "Invalid API key")
# =============================================================================
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def generate_api_key() -> tuple[str, str]:
    """Generate (raw_key, sha256_hash). Use secrets.token_urlsafe(32) + hashlib.sha256."""
    # TODO: Generate and return (raw_key, hashed_key)
    # raw = secrets.token_urlsafe(32)
    # hashed = hashlib.sha256(raw.encode()).hexdigest()
    # return (raw, hashed)
    raise NotImplementedError("Complete Exercise 4")

async def get_api_key_user(api_key: Optional[str] = Depends(api_key_header)) -> Optional[UserInDB]:
    """Validate X-API-Key: None->None, hash with SHA-256, search _users_db for
    matching api_key_hashes. Found+active->user, found+inactive->403, missing->401."""
    # TODO: Validate API key
    # 1. if not api_key: return None
    # 2. hashed = hashlib.sha256(api_key.encode()).hexdigest()
    # 3. for user in _users_db.values():
    #        if hashed in user.api_key_hashes:
    #            if not user.is_active:
    #                raise HTTPException(status_code=403, detail="Inactive user")
    #            return user
    # 4. raise HTTPException(status_code=401, detail="Invalid API key")
    raise NotImplementedError("Complete Exercise 4")

@app.post("/api-keys")
async def create_api_key(user: UserInDB = Depends(get_active_user)):
    raw, hashed = generate_api_key()
    user.api_key_hashes.append(hashed)
    return {"key": raw, "message": "Store securely. Will not be shown again."}

@app.get("/api-keys/test")
async def test_api_key(user: Optional[UserInDB] = Depends(get_api_key_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Provide X-API-Key header")
    return {"message": f"Authenticated as {user.username} via API key"}

# =============================================================================
# EXERCISE 5: Create a Token Refresh Endpoint
# =============================================================================
# READ FIRST: 01-authentication-basics.md -> "Token Refresh with Rotation"
#   and 03-advanced-auth-patterns.md -> "Token Revocation Strategies"
# ALSO SEE:  examples.py -> Section 9 (the "/auth/token/refresh" route) for
#   a working token refresh implementation.
#
# TOKEN ROTATION FLOW:
#   1. Decode the refresh token with decode_jwt() -- catch ValueError -> 401
#   2. Verify payload type == "refresh" (not an access token) -- else 401
#   3. Extract the JTI (JWT ID) from the payload
#   4. Check if JTI is in _revoked_tokens -- if so, raise 401 "Token has been revoked"
#   5. Add the JTI to _revoked_tokens (revoke the old refresh token)
#   6. Look up the user by payload["sub"] in _users_db -- not found -> 401
#   7. Issue a new token pair:
#      return TokenResponse(
#          access_token=create_access_token({"sub": user.id, "roles": user.roles}),
#          refresh_token=create_refresh_token({"sub": user.id}))
#
# WHY ROTATION? If an attacker steals a refresh token and uses it, the
# legitimate user's next refresh attempt will find the token revoked,
# signaling potential theft.
# =============================================================================
class RefreshRequest(BaseModel):
    refresh_token: str

@app.post("/auth/token/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest):
    """Token rotation: decode refresh token, verify type=="refresh", check jti not
    in _revoked_tokens, revoke old jti, look up user, return new token pair."""
    # TODO: Implement token refresh with rotation
    # 1. try: payload = decode_jwt(data.refresh_token)
    #    except ValueError as e: raise HTTPException(status_code=401,
    #        detail=f"Invalid refresh token: {e}")
    # 2. if payload.get("type") != "refresh":
    #        raise HTTPException(status_code=401, detail="Not a refresh token")
    # 3. jti = payload.get("jti", "")
    # 4. if jti in _revoked_tokens:
    #        raise HTTPException(status_code=401, detail="Token has been revoked")
    # 5. _revoked_tokens.add(jti)
    # 6. user = _users_db.get(payload["sub"])
    #    if not user: raise HTTPException(status_code=401, detail="User not found")
    # 7. return TokenResponse(
    #        access_token=create_access_token({"sub": user.id, "roles": user.roles}),
    #        refresh_token=create_refresh_token({"sub": user.id}))
    raise NotImplementedError("Complete Exercise 5")

# =============================================================================
# TESTS (run with: python exercises.py)
# =============================================================================
def _run_test(name, fn):
    try:
        fn()
        print(f"  PASSED: {name}")
        return True
    except NotImplementedError:
        print(f"  SKIPPED: {name}")
        return None
    except (AssertionError, Exception) as e:
        print(f"  FAILED: {name} -- {e}")
        return False

def test_ex1_create_jwt():
    token = create_jwt({"sub": "user123", "exp": time.time() + 300})
    parts = token.split(".")
    assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}"
    header = json.loads(_b64url_decode(parts[0]))
    assert header == {"alg": "HS256", "typ": "JWT"}

def test_ex1_decode_jwt():
    payload = {"sub": "test-user", "role": "admin", "exp": time.time() + 300}
    decoded = decode_jwt(create_jwt(payload))
    assert decoded["sub"] == "test-user" and decoded["role"] == "admin"

def test_ex1_expired_token():
    try:
        decode_jwt(create_jwt({"sub": "u", "exp": time.time() - 10}))
        assert False, "Should reject expired token"
    except ValueError as e:
        assert "expire" in str(e).lower()

def test_ex1_tampered_token():
    token = create_jwt({"sub": "user", "exp": time.time() + 300})
    parts = token.split(".")
    fake = _b64url_encode(json.dumps({"sub": "admin", "exp": time.time() + 300}).encode())
    try:
        decode_jwt(f"{parts[0]}.{fake}.{parts[2]}")
        assert False, "Should reject tampered token"
    except ValueError as e:
        assert "signature" in str(e).lower()

def test_ex1_access_token():
    payload = decode_jwt(create_access_token({"sub": "u1", "roles": ["user"]}))
    assert payload["type"] == "access" and payload["sub"] == "u1" and "jti" in payload

def test_ex1_refresh_token():
    r = decode_jwt(create_refresh_token({"sub": "u1"}))
    a = decode_jwt(create_access_token({"sub": "u1"}))
    assert r["type"] == "refresh" and r["exp"] > a["exp"]

def test_ex4_generate_api_key():
    raw, hashed = generate_api_key()
    assert len(raw) > 20 and len(hashed) == 64
    assert hashlib.sha256(raw.encode()).hexdigest() == hashed

def test_ex4_unique_keys():
    assert len({generate_api_key()[0] for _ in range(10)}) == 10

if __name__ == "__main__":
    print("Auth Exercises -- Validation Tests\n" + "=" * 50)
    groups = {
        "Exercise 1 (JWT)": [
            ("Create JWT format", test_ex1_create_jwt),
            ("Decode roundtrip", test_ex1_decode_jwt),
            ("Reject expired", test_ex1_expired_token),
            ("Reject tampered", test_ex1_tampered_token),
            ("Access token fields", test_ex1_access_token),
            ("Refresh token fields", test_ex1_refresh_token),
        ],
        "Exercise 4 (API Keys)": [
            ("Generate key pair", test_ex4_generate_api_key),
            ("Keys are unique", test_ex4_unique_keys),
        ],
    }
    passed = skipped = failed = 0
    for section, tests in groups.items():
        print(f"\n--- {section} ---")
        for name, fn in tests:
            r = _run_test(name, fn)
            if r is True: passed += 1
            elif r is None: skipped += 1
            else: failed += 1

    print(f"\n--- Exercises 2, 3, 5 (API-based) ---")
    print("  Start server: uvicorn exercises:app --reload")
    print("  POST /auth/token  username=admin password=adminpass")
    print("  Authorize in Swagger, then test protected routes.")
    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

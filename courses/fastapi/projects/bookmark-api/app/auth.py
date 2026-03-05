"""
Authentication utilities -- JWT creation/verification and password hashing.

Uses only the standard library (hmac, hashlib, base64, json) so there is
no dependency on python-jose or passlib.

Covers course concepts from:
- Module 04: Dependencies, security
- Module 06: Async dependencies
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models import UserInDB
from app.storage import storage

# ---------------------------------------------------------------------------
# Configuration -- in a real app these would come from environment / settings
# ---------------------------------------------------------------------------

SECRET_KEY = "super-secret-dev-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRY_SECONDS = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Password hashing (stdlib only -- sha256 + salt)
# ---------------------------------------------------------------------------

_SALT = "bookmark-api-static-salt"


def hash_password(plain: str) -> str:
    """Return a hex-digest hash of *plain* with a static salt."""
    return hashlib.sha256(f"{_SALT}{plain}".encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time comparison of a plaintext password against its hash."""
    return hmac.compare_digest(hash_password(plain), hashed)


# ---------------------------------------------------------------------------
# JWT helpers (stdlib only)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_token(user_id: str) -> str:
    """Create a simple HS256 JWT containing *user_id* as the ``sub`` claim."""
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
        "iat": int(time.time()),
    }

    segments = [
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _b64url_encode(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = f"{segments[0]}.{segments[1]}"
    signature = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    segments.append(_b64url_encode(signature))
    return ".".join(segments)


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify an HS256 JWT.  Returns the payload dict or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        signing_input = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(parts[1]))

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> UserInDB:
    """Dependency that extracts and validates the JWT, then returns the user."""
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await storage.get_user_by_id(payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

"""
User registration and login routes.

Covers course concepts from:
- Module 01: Path operations, status codes
- Module 02: Request body validation with Pydantic
- Module 04: Security / authentication flow
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.auth import create_token, hash_password, verify_password
from app.models import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserInDB,
    UserResponse,
)
from app.storage import storage

router = APIRouter(tags=["users"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
async def register(body: UserCreate) -> UserResponse:
    # Check for duplicate username
    existing = await storage.get_user_by_username(body.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Check for duplicate email
    existing_email = await storage.get_user_by_email(body.email)
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = UserInDB(
        id=str(uuid.uuid4()),
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
    )
    await storage.add_user(user)
    return UserResponse(id=user.id, email=user.email, username=user.username)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT",
)
async def login(body: LoginRequest) -> TokenResponse:
    user = await storage.get_user_by_username(body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_token(user.id)
    return TokenResponse(access_token=token)

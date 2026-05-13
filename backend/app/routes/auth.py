"""
Authentication API Router - Handles user authentication endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Body, Request
from typing import Optional

from app.models.auth_models import (
    UserCreate, UserLogin, AuthResponse, UserResponse, UserPasswordChange, UserPasswordChangeResponse
)
from app.services.auth_service import get_auth_service, AuthService
from app.services.verification_service import verification_service
from app.services.settings_service import settings_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and verify user ID from Authorization header.
    
    Args:
        authorization: Authorization header value (Bearer token)
        
    Returns:
        User ID from the token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        auth_service = get_auth_service()
        token_data = auth_service.verify_token_data(token)
        return token_data.user_id
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/send-code", response_model=bool)
async def send_verification_code(
    data: dict = Body(...),
):
    """
    Send verification code (email or phone)
    """
    target = data.get("target")
    type = data.get("type")
    
    if not target or not type:
        raise HTTPException(status_code=400, detail="Target and type are required")
        
    if type == "email" and not settings_service.is_email_verify_enabled():
        raise HTTPException(status_code=400, detail="Email verification is disabled")
        
    if type == "phone" and not settings_service.is_phone_verify_enabled():
        raise HTTPException(status_code=400, detail="Phone verification is disabled")
        
    try:
        verification_service.send_code(target, type)
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    """
    Register a new user.
    
    Args:
        user_data: User registration data (username, email, password)
        
    Returns:
        AuthResponse with user info and JWT token
    """
    try:
        auth_service = get_auth_service()
        return auth_service.register(user_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(login_data: UserLogin, request: Request):
    """
    Authenticate a user and return a JWT token.

    Args:
        login_data: User login credentials (username, password)

    Returns:
        AuthResponse with user info and JWT token
    """
    try:
        auth_service = get_auth_service()
        ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP", request.client.host if request.client else None))
        device_info = request.headers.get("User-Agent", "")
        return auth_service.login(login_data, ip_address=ip_address, device_info=device_info)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/logout")
async def logout(user_id: str = Depends(get_current_user_id)):
    """
    Logout the current user.
    
    Note: Since we're using stateless JWT tokens, logout is handled client-side
    by removing the token. This endpoint is provided for API completeness.
    
    Returns:
        Success message
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get the current authenticated user's information.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        UserResponse with user info
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        auth_service = get_auth_service()
        return auth_service.get_current_user(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


@router.get("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify if the current token is valid.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        Token validity status
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]

    try:
        auth_service = get_auth_service()
        token_data = auth_service.verify_token_data(token)
        return {
            "valid": True,
            "user_id": token_data.user_id,
            "username": token_data.username
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ==================== Password Management ====================

@router.put("/password", response_model=UserPasswordChangeResponse)
async def change_password(
    password_change: UserPasswordChange,
    authorization: Optional[str] = Header(None),
    request: Request = None
):
    """
    User change their own password.

    Args:
        password_change: Password change data (old_password, new_password)
        authorization: Authorization header with Bearer token

    Returns:
        UserPasswordChangeResponse with success status and message
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]

    try:
        auth_service = get_auth_service()
        # Get user ID from token
        token_data = auth_service.verify_token_data(token)
        user_id = token_data.user_id

        # Change password
        ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-IP", request.client.host if request.client else None)) if request else None
        device_info = request.headers.get("User-Agent", "") if request else ""
        success, message = auth_service.change_password(
            user_id=user_id,
            old_password=password_change.old_password,
            new_password=password_change.new_password,
            ip_address=ip_address,
            device_info=device_info
        )

        if not success:
            raise HTTPException(status_code=400, detail=message)

        return UserPasswordChangeResponse(
            success=True,
            message="Password changed successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

"""
Authentication Middleware - JWT token verification and user extraction
"""
from fastapi import Header, HTTPException, Depends
from typing import Optional

from app.services.auth_service import get_auth_service
from app.models.auth_models import TokenData


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and verify user ID from Authorization header.
    
    This dependency can be used in route handlers to get the current user's ID.
    
    Args:
        authorization: Authorization header value (Bearer token)
        
    Returns:
        User ID from the token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    if not token:
        raise HTTPException(
            status_code=401, 
            detail="Token is empty",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        auth_service = get_auth_service()
        token_data = auth_service.verify_token(token)
        return token_data.user_id
    except ValueError as e:
        raise HTTPException(
            status_code=401, 
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_token_data(authorization: Optional[str] = Header(None)) -> TokenData:
    """
    Extract and verify token data from Authorization header.
    
    This dependency returns the full TokenData including username.
    
    Args:
        authorization: Authorization header value (Bearer token)
        
    Returns:
        TokenData from the token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization[7:]
    
    if not token:
        raise HTTPException(
            status_code=401, 
            detail="Token is empty",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        auth_service = get_auth_service()
        return auth_service.verify_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=401, 
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


def require_auth(user_id: str = Depends(get_current_user_id)) -> str:
    """
    Dependency that requires authentication.
    
    Use this as a dependency in route handlers that require authentication.
    
    Args:
        user_id: User ID from get_current_user_id dependency
        
    Returns:
        User ID
    """
    return user_id


async def optional_auth(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Optional authentication - returns user_id if authenticated, None otherwise.
    
    Use this for routes that work with or without authentication.
    
    Args:
        authorization: Authorization header value (Bearer token)
        
    Returns:
        User ID if authenticated, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]
    
    if not token:
        return None
    
    try:
        auth_service = get_auth_service()
        token_data = auth_service.verify_token(token)
        return token_data.user_id
    except ValueError:
        return None

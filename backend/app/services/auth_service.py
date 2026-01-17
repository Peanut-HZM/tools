"""
Authentication Service - Handles user authentication and JWT token management
"""
import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.models.auth_models import (
    UserCreate, UserLogin, UserInDB, TokenData, AuthResponse, UserResponse
)

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours default

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User data storage path
USERS_DATA_PATH = os.environ.get("USERS_DATA_PATH", "./data/users")


class AuthService:
    """Service for user authentication operations"""
    
    def __init__(self):
        """Initialize AuthService"""
        self.users_file = Path(USERS_DATA_PATH) / "users.json"
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists"""
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.users_file.exists():
            self._save_users({})
    
    def _load_users(self) -> dict:
        """Load users from JSON file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
        return {}
    
    def _save_users(self, users: dict) -> bool:
        """Save users to JSON file"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            return False
    
    def _get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        users = self._load_users()
        for user_id, user_data in users.items():
            if user_data.get("username") == username:
                return UserInDB(
                    user_id=user_id,
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=user_data["hashed_password"],
                    created_at=datetime.fromisoformat(user_data["created_at"])
                )
        return None
    
    def _get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        users = self._load_users()
        user_data = users.get(user_id)
        if user_data:
            return UserInDB(
                user_id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=user_data["hashed_password"],
                created_at=datetime.fromisoformat(user_data["created_at"])
            )
        return None
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        # Truncate password to 72 bytes (bcrypt limit)
        truncated_password = plain_password[:72]
        return pwd_context.verify(truncated_password, hashed_password)
    
    def _hash_password(self, password: str) -> str:
        """Hash a password"""
        # Truncate password to 72 bytes (bcrypt limit)
        truncated_password = password[:72]
        return pwd_context.hash(truncated_password)
    
    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def register(self, user_data: UserCreate) -> AuthResponse:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            
        Returns:
            AuthResponse with user info and token
            
        Raises:
            ValueError: If username or email already exists
        """
        users = self._load_users()
        
        # Check if username already exists
        for user in users.values():
            if user.get("username") == user_data.username:
                raise ValueError("Username already exists")
            if user.get("email") == user_data.email:
                raise ValueError("Email already exists")
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = self._hash_password(user_data.password)
        created_at = datetime.utcnow()
        
        users[user_id] = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hashed_password,
            "created_at": created_at.isoformat()
        }
        
        if not self._save_users(users):
            raise ValueError("Failed to save user data")
        
        # Create user directory for markdown files
        self._create_user_directory(user_id)
        
        # Generate token
        token = self._create_access_token(
            data={"sub": user_id, "username": user_data.username}
        )
        
        return AuthResponse(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            token=token
        )
    
    def login(self, login_data: UserLogin) -> AuthResponse:
        """
        Authenticate a user and return a token.
        
        Args:
            login_data: User login credentials
            
        Returns:
            AuthResponse with user info and token
            
        Raises:
            ValueError: If credentials are invalid
        """
        user = self._get_user_by_username(login_data.username)
        
        if not user:
            raise ValueError("Invalid username or password")
        
        if not self._verify_password(login_data.password, user.hashed_password):
            raise ValueError("Invalid username or password")
        
        # Generate token
        token = self._create_access_token(
            data={"sub": user.user_id, "username": user.username}
        )
        
        return AuthResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            token=token
        )
    
    def verify_token(self, token: str) -> TokenData:
        """
        Verify a JWT token and return the token data.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData with user info
            
        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            exp = payload.get("exp")
            
            if user_id is None:
                raise ValueError("Invalid token: missing user_id")
            
            return TokenData(
                user_id=user_id,
                username=username,
                exp=datetime.fromtimestamp(exp) if exp else None
            )
        except JWTError as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def get_current_user(self, token: str) -> UserResponse:
        """
        Get the current user from a token.
        
        Args:
            token: JWT token string
            
        Returns:
            UserResponse with user info
            
        Raises:
            ValueError: If token is invalid or user not found
        """
        token_data = self.verify_token(token)
        user = self._get_user_by_id(token_data.user_id)
        
        if not user:
            raise ValueError("User not found")
        
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            created_at=user.created_at
        )
    
    def _create_user_directory(self, user_id: str) -> None:
        """Create user's markdown files directory"""
        user_dir = Path(USERS_DATA_PATH) / user_id / "markdown-files"
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default config directory
        config_dir = user_dir / ".markdown-editor"
        config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_user_root_path(self, user_id: str) -> str:
        """Get the root path for a user's markdown files"""
        return str(Path(USERS_DATA_PATH) / user_id / "markdown-files")


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the AuthService singleton instance"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service

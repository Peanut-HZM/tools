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

from app.config.config import settings

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User data storage path
USERS_DATA_PATH = settings.USERS_DATA_PATH


import string
import random
from app.services.settings_service import settings_service
from app.services.verification_service import verification_service

# ... (imports)

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
                    role=user_data.get("role", "user"),
                    hashed_password=user_data["hashed_password"],
                    created_at=datetime.fromisoformat(user_data["created_at"])
                )
        return None

    def register(self, user_data: UserCreate) -> AuthResponse:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            
        Returns:
            AuthResponse with user info and token
            
        Raises:
            ValueError: If username/email exists or registration failed
        """
        # Check if registration is allowed
        if not settings_service.is_registration_allowed():
            raise ValueError("Registration is currently disabled by administrator")

        if self._get_user_by_username(user_data.username):
            raise ValueError("Username already exists")
        
        # Verify Email Code if enabled
        if settings_service.is_email_verify_enabled():
            if not user_data.email_code:
                raise ValueError("Email verification code is required")
            if not verification_service.verify_code(user_data.email, user_data.email_code):
                raise ValueError("Invalid or expired email verification code")
                
        # Verify Phone Code if enabled
        if settings_service.is_phone_verify_enabled():
            if not user_data.phone:
                raise ValueError("Phone number is required")
            if not user_data.phone_code:
                raise ValueError("Phone verification code is required")
            if not verification_service.verify_code(user_data.phone, user_data.phone_code):
                raise ValueError("Invalid or expired phone verification code")
        
        users = self._load_users()
        for u in users.values():
            if u["email"] == user_data.email:
                raise ValueError("Email already registered")
            if user_data.phone and u.get("phone") == user_data.phone:
                raise ValueError("Phone number already registered")
        
        user_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        hashed_password = self._hash_password(user_data.password)
        
        users[user_id] = {
            "username": user_data.username,
            "email": user_data.email,
            "phone": user_data.phone,
            "role": "user",  # Default role
            "hashed_password": hashed_password,
            "created_at": created_at.isoformat()
        }
        
        if not self._save_users(users):
            raise ValueError("Failed to save user data")
        
        # Create user directory for markdown files
        self._create_user_directory(user_id)
        
        # Generate token
        token = self._create_access_token(
            data={"sub": user_id, "username": user_data.username, "role": "user"}
        )
        
        return AuthResponse(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            role="user",
            token=token,
            phone=user_data.phone
        )

    def create_user_admin(self, username: str, email: str, role: str) -> str:
        """
        Create a new user by admin (bypasses registration check, random password)
        
        Returns:
            The generated password
        """
        if self._get_user_by_username(username):
            raise ValueError("Username already exists")
        
        users = self._load_users()
        for u in users.values():
            if u["email"] == email:
                raise ValueError("Email already registered")
        
        # Generate random password
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(12))
        
        user_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        hashed_password = self._hash_password(password)
        
        users[user_id] = {
            "username": username,
            "email": email,
            "role": role,
            "hashed_password": hashed_password,
            "created_at": created_at.isoformat()
        }
        
        if not self._save_users(users):
            raise ValueError("Failed to save user data")
            
        # Create user directory for markdown files
        self._create_user_directory(user_id)
        
        return password
    
    def _get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        users = self._load_users()
        user_data = users.get(user_id)
        if user_data:
            return UserInDB(
                user_id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                role=user_data.get("role", "user"),
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
            "role": "user",  # Default role
            "hashed_password": hashed_password,
            "created_at": created_at.isoformat()
        }
        
        if not self._save_users(users):
            raise ValueError("Failed to save user data")
        
        # Create user directory for markdown files
        self._create_user_directory(user_id)
        
        # Generate token
        token = self._create_access_token(
            data={"sub": user_id, "username": user_data.username, "role": "user"}
        )
        
        return AuthResponse(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            role="user",
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
            data={"sub": user.user_id, "username": user.username, "role": user.role}
        )
        
        return AuthResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            token=token
        )
    
    def get_all_users(self) -> list[UserResponse]:
        """Get all users (admin only)"""
        users = self._load_users()
        result = []
        for user_id, user_data in users.items():
            result.append(UserResponse(
                user_id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                role=user_data.get("role", "user"),
                created_at=datetime.fromisoformat(user_data["created_at"])
            ))
        return result
    
    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Update user role (admin only)"""
        users = self._load_users()
        if user_id in users:
            users[user_id]["role"] = new_role
            return self._save_users(users)
        return False
        
    def delete_user(self, user_id: str) -> bool:
        """Delete user (admin only)"""
        users = self._load_users()
        if user_id in users:
            del users[user_id]
            return self._save_users(users)
        return False

    def _create_user_directory(self, user_id: str) -> None:
        """Create user directory if it doesn't exist"""
        # This should call the file service or similar, but for now we'll import it or mock it
        # Actually, the file service creates it on init. We can just ensure the path exists.
        # But wait, auth service shouldn't really care about files. 
        # The previous code had `self._create_user_directory(user_id)` call but it was not defined in the snippet I read?
        # Let me check the Read output again.
        # Ah, I missed reading the _create_user_directory method in the previous Read call (it was cut off or not shown).
        # I will assume it exists or I need to add it if it was missing.
        # Let's check the end of the file.
        pass
    
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
            role: str = payload.get("role", "user")
            exp = payload.get("exp")
            
            if user_id is None:
                raise ValueError("Invalid token: missing user_id")
            
            return TokenData(
                user_id=user_id,
                username=username,
                role=role,
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
            role=user.role,
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

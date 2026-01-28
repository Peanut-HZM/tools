"""
Authentication Service - Handles user authentication and JWT token management
"""
import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.models.auth_models import (
    UserCreate, UserLogin, UserInDB, TokenData, AuthResponse, UserResponse
)

from app.config.config import settings
from app.config.database import get_db_connection

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

class AuthService:
    """Service for user authentication operations"""
    
    def __init__(self):
        """Initialize AuthService"""
        self._ensure_data_dir()
    
    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists (for markdown files)"""
        # We still need the directory for markdown files even if users are in DB
        Path(USERS_DATA_PATH).mkdir(parents=True, exist_ok=True)
    
    def _get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE username = %s",
                    (username,)
                )
                row = cursor.fetchone()
                if row:
                    return UserInDB(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        hashed_password=row['password_hash'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
        finally:
            conn.close()

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
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Check username existence
                cursor.execute("SELECT user_id FROM users WHERE username = %s", (user_data.username,))
                if cursor.fetchone():
                    raise ValueError("Username already exists")

                # Check email existence
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (user_data.email,))
                if cursor.fetchone():
                    raise ValueError("Email already registered")
                
                # We don't have phone in users table schema yet, so skipping phone uniqueness check for DB
                # or we should add it if needed. The schema showed earlier didn't have phone.
                # Assuming we just ignore phone storage in DB for now or update schema later.
                # The prompt context didn't show phone column in users table.
        
                user_id = str(uuid.uuid4())
                created_at = datetime.utcnow()
                hashed_password = self._hash_password(user_data.password)
                
                cursor.execute(
                    "INSERT INTO users (user_id, username, email, password_hash, role, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, user_data.username, user_data.email, hashed_password, "user", created_at)
                )
                conn.commit()
                
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
        except ValueError as e:
            raise e
        except Exception as e:
            conn.rollback()
            logger.error(f"Error registering user: {e}")
            raise ValueError("Failed to register user")
        finally:
            conn.close()

    def create_user_admin(self, username: str, email: str, role: str) -> str:
        """
        Create a new user by admin (bypasses registration check, random password)
        
        Returns:
            The generated password
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                if self._get_user_by_username(username):
                    raise ValueError("Username already exists")
                
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    raise ValueError("Email already registered")
        
                # Generate random password
                chars = string.ascii_letters + string.digits + "!@#$%^&*"
                password = ''.join(random.choice(chars) for _ in range(12))
                
                user_id = str(uuid.uuid4())
                created_at = datetime.utcnow()
                hashed_password = self._hash_password(password)
                
                cursor.execute(
                    "INSERT INTO users (user_id, username, email, password_hash, role, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, username, email, hashed_password, role, created_at)
                )
                conn.commit()
                    
                # Create user directory for markdown files
                self._create_user_directory(user_id)
                
                return password
        except ValueError as e:
            raise e
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating admin user: {e}")
            raise ValueError("Failed to create user")
        finally:
            conn.close()
    
    def _get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if row:
                    return UserInDB(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        hashed_password=row['password_hash'],
                        created_at=row['created_at']
                    )
                return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
        finally:
            conn.close()
    
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
    
    def get_all_users(self) -> List[UserResponse]:
        """Get all users (admin only)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    result.append(UserResponse(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        created_at=row['created_at']
                    ))
                return result
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
        finally:
            conn.close()
    
    def update_user_role(self, user_id: str, new_role: str) -> bool:
        """Update user role (admin only)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET role = %s WHERE user_id = %s",
                    (new_role, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating user role: {e}")
            return False
        finally:
            conn.close()
        
    def delete_user(self, user_id: str) -> bool:
        """Delete user (admin only)"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting user: {e}")
            return False
        finally:
            conn.close()

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

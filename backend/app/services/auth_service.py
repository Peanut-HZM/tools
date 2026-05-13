"""
Authentication Service - Handles user authentication and JWT token management
"""
import os
import json
import uuid
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from jose import JWTError, jwt

from app.models.auth_models import (
    UserCreate, UserLogin, UserInDB, TokenData, AuthResponse, UserResponse,
    AdminPasswordReset, AdminPasswordResetResponse, UserPasswordChange, UserPasswordChangeResponse
)
from app.config.database import get_db_connection
from app.config.config import settings
from app.utils.password_utils import validate_password_strength, generate_random_password, hash_password, verify_password
from fastapi import Request

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES

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

    def _log_audit(self, user_id: str, action_type: str, success: bool,
                   error_message: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   device_info: Optional[str] = None,
                   actor_user_id: Optional[str] = None) -> None:
        """记录密码审计日志"""
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO password_audit_logs
                       (id, user_id, action_type, success, error_message, ip_address, device_info, actor_user_id, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (str(uuid.uuid4()), user_id, action_type, success,
                     error_message, ip_address, device_info, actor_user_id, datetime.utcnow())
                )
                conn.commit()
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
        finally:
            conn.close()

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
        return verify_password(plain_password, hashed_password)

    def _hash_password(self, password: str) -> str:
        """Hash a password"""
        return hash_password(password)
    
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

    def hash_password(self, password: str) -> str:
        return hash_password(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    def create_token(self, user_id: str, username: str) -> str:
        return self._create_access_token(data={"sub": user_id, "username": username, "role": "user"})

    def validate_username(self, username: str) -> bool:
        if not username:
            return False
        if len(username) < 3 or len(username) > 50:
            return False
        return re.match(r"^[A-Za-z0-9_]+$", username) is not None

    def validate_email(self, email: str) -> bool:
        if not email:
            return False
        return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

    def validate_password(self, password: str) -> bool:
        if not password:
            return False
        return len(password) >= 6

    def login(self, login_data: UserLogin, ip_address: Optional[str] = None,
              device_info: Optional[str] = None) -> AuthResponse:
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
            self._log_audit(
                user_id="", action_type="login", success=False,
                error_message="用户不存在", ip_address=ip_address, device_info=device_info
            )
            raise ValueError("Invalid username or password")

        if not self._verify_password(login_data.password, user.hashed_password):
            self._log_audit(
                user_id=user.user_id, action_type="login", success=False,
                error_message="密码不正确", ip_address=ip_address, device_info=device_info
            )
            raise ValueError("Invalid username or password")

        # 登录成功
        self._log_audit(
            user_id=user.user_id, action_type="login", success=True,
            ip_address=ip_address, device_info=device_info
        )

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
        """Get all users (admin only) - deprecated, use get_users_paginated instead"""
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

    def get_users_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None
    ) -> dict:
        """
        Get paginated users with optional search and filter

        Args:
            page: Page number (1-indexed)
            page_size: Number of users per page
            search: Search keyword for username/email
            role: Filter by role

        Returns:
            dict with total, page, page_size, total_pages, users
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Build query conditions
                conditions = []
                params = []

                if search:
                    conditions.append("(username ILIKE %s OR email ILIKE %s)")
                    search_pattern = f"%{search}%"
                    params.extend([search_pattern, search_pattern])

                if role:
                    conditions.append("role = %s")
                    params.append(role)

                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

                # Get total count
                count_query = f"SELECT COUNT(*) FROM users{where_clause}"
                cursor.execute(count_query, params)
                total = cursor.fetchone()['count']

                # Get paginated users
                offset = (page - 1) * page_size
                query = f"""
                    SELECT * FROM users{where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, params + [page_size, offset])
                rows = cursor.fetchall()

                users = []
                for row in rows:
                    users.append(UserResponse(
                        user_id=row['user_id'],
                        username=row['username'],
                        email=row['email'],
                        role=row['role'],
                        created_at=row['created_at']
                    ))

                total_pages = (total + page_size - 1) // page_size

                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "users": users
                }
        except Exception as e:
            logger.error(f"Error getting paginated users: {e}")
            return {
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "users": []
            }
        finally:
            conn.close()

    def batch_delete_users(self, user_ids: List[str], current_user_id: str) -> dict:
        """
        Batch delete users

        Args:
            user_ids: List of user IDs to delete
            current_user_id: Current admin user ID (to prevent self-deletion)

        Returns:
            dict with success_count, failed_count, errors
        """
        conn = get_db_connection()
        success_count = 0
        failed_count = 0
        errors = []

        try:
            with conn.cursor() as cursor:
                for user_id in user_ids:
                    # Check if trying to delete self
                    if user_id == current_user_id:
                        failed_count += 1
                        errors.append(f"Cannot delete yourself")
                        continue

                    try:
                        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
                        if cursor.rowcount > 0:
                            success_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"User {user_id} not found")
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"Failed to delete user {user_id}: {str(e)}")

                conn.commit()

                return {
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "errors": errors
                }
        except Exception as e:
            conn.rollback()
            logger.error(f"Error batch deleting users: {e}")
            return {
                "success_count": 0,
                "failed_count": len(user_ids),
                "errors": [str(e)]
            }
        finally:
            conn.close()

    def batch_update_user_role(self, user_ids: List[str], new_role: str) -> dict:
        """
        Batch update user role

        Args:
            user_ids: List of user IDs to update
            new_role: New role to assign

        Returns:
            dict with success_count, failed_count, errors
        """
        conn = get_db_connection()
        success_count = 0
        failed_count = 0
        errors = []

        try:
            with conn.cursor() as cursor:
                for user_id in user_ids:
                    try:
                        cursor.execute(
                            "UPDATE users SET role = %s WHERE user_id = %s",
                            (new_role, user_id)
                        )
                        if cursor.rowcount > 0:
                            success_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"User {user_id} not found")
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"Failed to update user {user_id}: {str(e)}")

                conn.commit()

                return {
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "errors": errors
                }
        except Exception as e:
            conn.rollback()
            logger.error(f"Error batch updating user roles: {e}")
            return {
                "success_count": 0,
                "failed_count": len(user_ids),
                "errors": [str(e)]
            }
        finally:
            conn.close()

    def admin_reset_password(self, user_id: str, mode: str, new_password: Optional[str],
                             reset_by_user_id: str, ip_address: Optional[str] = None) -> tuple[bool, str, str]:
        """
        管理员重置用户密码

        Args:
            user_id: 目标用户 ID
            mode: "direct" 或 "random"
            new_password: 新密码（mode=direct 时必填）
            reset_by_user_id: 执行重置的管理员用户 ID
            ip_address: 请求 IP 地址

        Returns:
            (success, message, actual_password)
            - success: 是否成功
            - message: 错误信息（成功时为空）
            - actual_password: 实际设置的新密码
        """
        # 验证密码强度
        if mode == "direct":
            if not new_password:
                return False, "新密码不能为空", ""
            is_valid, error_msg = validate_password_strength(new_password)
            if not is_valid:
                return False, error_msg, ""
            actual_password = new_password
        else:  # mode == "random"
            actual_password = generate_random_password(12)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 检查用户是否存在
                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                if not cursor.fetchone():
                    return False, "用户不存在", ""

                # 更新密码
                hashed_password = self._hash_password(actual_password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (hashed_password, user_id)
                )

                # 记录审计日志
                self._log_audit(
                    user_id=user_id, action_type="admin_reset", success=True,
                    ip_address=ip_address, actor_user_id=reset_by_user_id
                )

                conn.commit()
                return True, "", actual_password

        except Exception as e:
            conn.rollback()
            logger.error(f"Error resetting password: {e}")
            return False, f"重置失败：{str(e)}", ""
        finally:
            conn.close()

    def change_password(self, user_id: str, old_password: str, new_password: str,
                        ip_address: Optional[str] = None,
                        device_info: Optional[str] = None) -> tuple[bool, str]:
        """
        用户修改密码

        Args:
            user_id: 用户 ID
            old_password: 当前密码
            new_password: 新密码

        Returns:
            (success, message)
        """
        # 验证新密码强度
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 获取用户
                cursor.execute(
                    "SELECT password_hash FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return False, "用户不存在"

                # 验证旧密码
                if not self._verify_password(old_password, row['password_hash']):
                    self._log_audit(
                        user_id=user_id, action_type="change_password", success=False,
                        error_message="当前密码不正确", ip_address=ip_address, device_info=device_info
                    )
                    return False, "当前密码不正确"

                # 检查新旧密码是否相同
                if self._verify_password(new_password, row['password_hash']):
                    self._log_audit(
                        user_id=user_id, action_type="change_password", success=False,
                        error_message="新密码与当前密码相同", ip_address=ip_address, device_info=device_info
                    )
                    return False, "新密码不能与当前密码相同"

                # 更新密码
                hashed_password = self._hash_password(new_password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (hashed_password, user_id)
                )

                conn.commit()

                self._log_audit(
                    user_id=user_id, action_type="change_password", success=True,
                    ip_address=ip_address, device_info=device_info
                )
                return True, "密码修改成功"

        except Exception as e:
            conn.rollback()
            logger.error(f"Error changing password: {e}")
            return False, f"修改失败：{str(e)}"
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

    def verify_token_data(self, token: str) -> TokenData:
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

    def verify_token(self, token: Optional[str]):
        if not token:
            return None
        try:
            token_data = self.verify_token_data(token)
            return {
                "user_id": token_data.user_id,
                "username": token_data.username,
                "role": token_data.role,
                "exp": token_data.exp
            }
        except ValueError:
            return None
    
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
        token_data = self.verify_token_data(token)
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

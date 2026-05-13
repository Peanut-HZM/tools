"""
JWT 工具函数
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.config.config import settings

# JWT 配置
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌

    Args:
        data: 要编码的数据（通常包含用户 ID）
        expires_delta: 令牌过期时间增量，如果不传则使用默认值

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    验证 JWT 令牌

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 payload，如果验证失败则返回 None
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_from_token(token: str) -> Optional[str]:
    """
    从 token 中获取用户 ID

    Args:
        token: JWT token 字符串

    Returns:
        用户 ID，如果验证失败则返回 None
    """
    payload = verify_token(token)
    if payload is None:
        return None

    user_id: str = payload.get("sub")
    return user_id


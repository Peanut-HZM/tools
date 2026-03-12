"""
API 依赖注入
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.models import get_db
import redis
import os

security = HTTPBearer(auto_error=False)


def get_redis_client() -> redis.Redis:
    """获取 Redis 客户端"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(redis_url, decode_responses=True)


from jose import jwt, JWTError
from app.config.config import settings


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """获取当前用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # 解析 JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id = payload.get("sub")
        username = payload.get("username")
        role = payload.get("role")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no user ID",
            )

        return {"id": user_id, "username": username, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

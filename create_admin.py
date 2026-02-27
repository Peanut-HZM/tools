#!/usr/bin/env python3
"""
创建管理员用户的脚本
"""

import sys

sys.path.insert(0, "/Users/huazhongmin/IdeaProjects/tools/backend")

from app.config.database import get_db_connection
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_admin_user():
    username = "admin"
    email = "admin@example.com"
    password = "admin123"
    role = "admin"

    hashed_password = pwd_context.hash(password)
    user_id = str(uuid.uuid4())

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 检查用户是否已存在
            cur.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                print(f"用户 {username} 已存在")
                # 更新为管理员
                cur.execute(
                    "UPDATE users SET role = %s WHERE username = %s", (role, username)
                )
                conn.commit()
                print(f"已将 {username} 更新为管理员")
                return

            # 创建新用户
            cur.execute(
                """
                INSERT INTO users (user_id, username, email, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """,
                (user_id, username, email, hashed_password, role),
            )
            conn.commit()
            print(f"成功创建管理员用户: {username}")
            print(f"密码: {password}")
    except Exception as e:
        print(f"错误: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    create_admin_user()

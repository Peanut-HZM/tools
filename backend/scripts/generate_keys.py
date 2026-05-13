"""
生成安全的随机密钥脚本

Usage:
    python scripts/generate_keys.py

输出可直接复制到 backend/.env 文件中
"""
import secrets


def generate_key(length: int = 32) -> str:
    """生成 URL-safe 的随机密钥"""
    return secrets.token_urlsafe(length)


def main():
    jwt_key = generate_key(32)
    db_key = generate_key(32)

    print("# 将以下内容复制到 backend/.env 文件中")
    print("# 注意：修改密钥后，已颁发的 JWT Token 将失效，用户需要重新登录")
    print()
    print(f"JWT_SECRET_KEY={jwt_key}")
    print(f"DB_ENCRYPTION_KEY={db_key}")


if __name__ == "__main__":
    main()

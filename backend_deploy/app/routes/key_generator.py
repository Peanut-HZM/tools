from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import secrets
import hashlib
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519
from cryptography.hazmat.backends import default_backend

router = APIRouter(prefix="/api/tools", tags=["key-generator"])


class KeyGenerateRequest(BaseModel):
    algorithm: str
    key_size: Optional[int] = None
    format: Optional[str] = "pem"  # pem, der, base64


# 支持的算法配置
ALGORITHMS = {
    "rsa": {
        "name": "RSA",
        "description": "非对称加密算法，广泛用于数字签名和加密",
        "key_sizes": [1024, 2048, 3072, 4096],
        "default_size": 2048,
        "type": "asymmetric"
    },
    "ecdsa-p256": {
        "name": "ECDSA P-256",
        "description": "椭圆曲线数字签名算法，使用P-256曲线",
        "key_sizes": [256],
        "default_size": 256,
        "type": "asymmetric"
    },
    "ecdsa-p384": {
        "name": "ECDSA P-384",
        "description": "椭圆曲线数字签名算法，使用P-384曲线",
        "key_sizes": [384],
        "default_size": 384,
        "type": "asymmetric"
    },
    "ecdsa-p521": {
        "name": "ECDSA P-521",
        "description": "椭圆曲线数字签名算法，使用P-521曲线",
        "key_sizes": [521],
        "default_size": 521,
        "type": "asymmetric"
    },
    "ed25519": {
        "name": "Ed25519",
        "description": "高性能椭圆曲线签名算法",
        "key_sizes": [256],
        "default_size": 256,
        "type": "asymmetric"
    },
    "aes": {
        "name": "AES",
        "description": "高级加密标准，对称加密算法",
        "key_sizes": [128, 192, 256],
        "default_size": 256,
        "type": "symmetric"
    },
    "hmac-sha256": {
        "name": "HMAC-SHA256",
        "description": "基于SHA-256的消息认证码",
        "key_sizes": [256, 512],
        "default_size": 256,
        "type": "symmetric"
    },
    "hmac-sha384": {
        "name": "HMAC-SHA384",
        "description": "基于SHA-384的消息认证码",
        "key_sizes": [384, 512],
        "default_size": 384,
        "type": "symmetric"
    },
    "hmac-sha512": {
        "name": "HMAC-SHA512",
        "description": "基于SHA-512的消息认证码",
        "key_sizes": [512, 1024],
        "default_size": 512,
        "type": "symmetric"
    },
    "random": {
        "name": "随机密钥",
        "description": "生成随机字节序列，可用于各种用途",
        "key_sizes": [128, 256, 512, 1024],
        "default_size": 256,
        "type": "symmetric"
    },
    "uuid": {
        "name": "UUID",
        "description": "通用唯一标识符",
        "key_sizes": [128],
        "default_size": 128,
        "type": "symmetric"
    },
    "api-key": {
        "name": "API Key",
        "description": "适合作为API密钥的随机字符串",
        "key_sizes": [32, 64, 128],
        "default_size": 64,
        "type": "symmetric"
    }
}


def generate_rsa_key(key_size: int):
    """生成RSA密钥对"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return {
        "private_key": private_pem,
        "public_key": public_pem
    }


def generate_ecdsa_key(curve_name: str):
    """生成ECDSA密钥对"""
    curves = {
        "p256": ec.SECP256R1(),
        "p384": ec.SECP384R1(),
        "p521": ec.SECP521R1()
    }
    
    curve = curves.get(curve_name)
    if not curve:
        raise ValueError(f"不支持的曲线: {curve_name}")
    
    private_key = ec.generate_private_key(curve, default_backend())
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return {
        "private_key": private_pem,
        "public_key": public_pem
    }


def generate_ed25519_key():
    """生成Ed25519密钥对"""
    private_key = ed25519.Ed25519PrivateKey.generate()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return {
        "private_key": private_pem,
        "public_key": public_pem
    }


def generate_symmetric_key(key_size: int):
    """生成对称密钥"""
    key_bytes = secrets.token_bytes(key_size // 8)
    return {
        "key_hex": key_bytes.hex(),
        "key_base64": base64.b64encode(key_bytes).decode('utf-8')
    }


def generate_uuid():
    """生成UUID"""
    import uuid
    new_uuid = uuid.uuid4()
    return {
        "uuid": str(new_uuid),
        "uuid_hex": new_uuid.hex
    }


def generate_api_key(length: int):
    """生成API密钥"""
    # 使用URL安全的字符
    key = secrets.token_urlsafe(length)
    return {
        "api_key": key[:length],
        "api_key_hex": secrets.token_hex(length // 2)
    }


@router.get("/key-algorithms")
async def get_algorithms():
    """获取支持的算法列表"""
    return {"algorithms": ALGORITHMS}


@router.post("/generate-key")
async def generate_key(request: KeyGenerateRequest):
    """生成密钥"""
    algorithm = request.algorithm.lower()
    
    if algorithm not in ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"不支持的算法: {algorithm}")
    
    algo_config = ALGORITHMS[algorithm]
    key_size = request.key_size or algo_config["default_size"]
    
    if key_size not in algo_config["key_sizes"]:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的密钥长度: {key_size}，支持的长度: {algo_config['key_sizes']}"
        )
    
    try:
        if algorithm == "rsa":
            result = generate_rsa_key(key_size)
        elif algorithm == "ecdsa-p256":
            result = generate_ecdsa_key("p256")
        elif algorithm == "ecdsa-p384":
            result = generate_ecdsa_key("p384")
        elif algorithm == "ecdsa-p521":
            result = generate_ecdsa_key("p521")
        elif algorithm == "ed25519":
            result = generate_ed25519_key()
        elif algorithm in ["aes", "hmac-sha256", "hmac-sha384", "hmac-sha512", "random"]:
            result = generate_symmetric_key(key_size)
        elif algorithm == "uuid":
            result = generate_uuid()
        elif algorithm == "api-key":
            result = generate_api_key(key_size)
        else:
            raise HTTPException(status_code=400, detail=f"算法 {algorithm} 暂未实现")
        
        return {
            "algorithm": algorithm,
            "algorithm_name": algo_config["name"],
            "key_size": key_size,
            "type": algo_config["type"],
            **result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成密钥失败: {str(e)}")

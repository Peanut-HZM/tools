"""ImageModelProvider 抽象接口 + 数据结构

参考 spec §4.1
"""
import ipaddress
import logging
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# 内网/保留/loopback/link-local 网络黑名单，覆盖 IPv4 + IPv6
# 用于 SSRF 防护：拒绝任何解析到这些网络的 URL
_BLOCKED_NETWORKS = [
    # IPv4
    ipaddress.ip_network('0.0.0.0/8'),         # "this network"
    ipaddress.ip_network('10.0.0.0/8'),        # RFC 1918 私网
    ipaddress.ip_network('100.64.0.0/10'),     # CGNAT
    ipaddress.ip_network('127.0.0.0/8'),       # loopback
    ipaddress.ip_network('169.254.0.0/16'),    # link-local（含 AWS metadata 169.254.169.254）
    ipaddress.ip_network('172.16.0.0/12'),     # RFC 1918 私网
    ipaddress.ip_network('192.0.0.0/24'),      # IETF 协议分配段
    ipaddress.ip_network('192.168.0.0/16'),    # RFC 1918 私网
    ipaddress.ip_network('198.18.0.0/15'),     # benchmark 测试段
    ipaddress.ip_network('224.0.0.0/4'),       # 组播
    ipaddress.ip_network('240.0.0.0/4'),       # 保留段
    # IPv6
    ipaddress.ip_network('::1/128'),           # IPv6 loopback
    ipaddress.ip_network('::/128'),            # 未指定地址
    ipaddress.ip_network('fc00::/7'),          # IPv6 ULA（含 fd00::/8）
    ipaddress.ip_network('fe80::/10'),         # IPv6 link-local
]


def _resolve_and_check_ip(hostname: str) -> bool:
    """解析 hostname 并检查所有 A/AAAA 记录是否都不在黑名单内

    使用 getaddrinfo 替代 gethostbyname 以捕获 IPv6 AAAA 记录，
    防止 happy-eyeballs / dual-stack 客户端通过 IPv6 绕过黑名单。

    返回 True 表示安全（公网可达），False 表示拒绝。
    """
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError, UnicodeError):
        logger.warning("DNS 解析失败: %s", hostname)
        return False

    if not infos:
        logger.warning("DNS 解析结果为空: %s", hostname)
        return False

    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            # 解析失败保守拒绝
            logger.warning("无法解析 IP 字面量: %s -> %s", hostname, ip_str)
            return False
        # IPv4 映射的 IPv6（::ffff:10.0.0.1）需还原为 IPv4 再比对
        if getattr(ip, "ipv4_mapped", None) is not None:
            ip = ip.ipv4_mapped
        for network in _BLOCKED_NETWORKS:
            if ip.version == network.version and ip in network:
                logger.warning("拒绝内网 IP: %s -> %s", hostname, ip_str)
                return False
    return True


@dataclass
class ImageGenParams:
    """图像生成参数"""
    size: str = "1024x1024"
    n: int = 1
    style: Optional[str] = None
    model_name: str = ""           # 来自 LLMModel.model_name
    request_params: dict = field(default_factory=dict)  # 来自 LLMModel.request_params


@dataclass
class ImageGenResult:
    """图像生成结果"""
    image_urls: List[str]          # 生成的图片 URL 列表（OSS）
    model_used: str                # 实际使用的模型标识
    revised_prompt: str = ""       # provider 修改后的 prompt（如有）
    elapsed_seconds: float = 0.0


class ImageGenError(Exception):
    """图像生成错误，携带可重试标记

    retryable=True: 超时/限流/5xx → 触发 fallback 链
    retryable=False: 鉴权失败/参数错误/余额不足 → 不重试
    """
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ImageModelProvider(ABC):
    """图像生成 Provider 抽象接口

    子类实现 4 种操作 + validate_config。
    通过 Provider Registry 从 LLMProvider.provider_type 路由到具体实现。
    """

    def __init__(self, base_url: str, api_key: str, oss_client=None):
        self.base_url = base_url
        self.api_key = api_key
        self.oss_client = oss_client

    @abstractmethod
    async def text2img(self, prompt: str, params: ImageGenParams) -> ImageGenResult:
        """文生图"""

    @abstractmethod
    async def img2img(self, prompt: str, reference_image: str, params: ImageGenParams) -> ImageGenResult:
        """图生图（reference_image 为 OSS URL）"""

    @abstractmethod
    async def inpaint(self, prompt: str, image_url: str, mask_url: str, params: ImageGenParams) -> ImageGenResult:
        """局部重绘"""

    @abstractmethod
    async def upload_edit(self, image_url: str, instruction: str, params: ImageGenParams) -> ImageGenResult:
        """上传编辑（指令式）"""

    @abstractmethod
    def validate_config(self) -> None:
        """校验 provider 配置是否可用（启动时调用）"""

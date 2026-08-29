"""
backend/app/core/exceptions.py

应用级异常定义。
"""


class QuotaExceeded(Exception):
    """
    配额超限异常。

    reason 取值：
      - "daily_limit_exceeded"    — 日配额用完
      - "monthly_limit_exceeded"  — 月配额用完
      - "validity_not_started"    — 有效期未开始（now < valid_from）
      - "validity_expired"        — 有效期已过（now > valid_until）
      - "no_quota"                — 用户在 llm_user_quota 表无记录
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class InvalidQuotaMode(Exception):
    """grant 时的配额模式/字段校验失败（HTTP 400）"""


class ServiceDegraded(Exception):
    """
    服务降级中，拒绝新请求。

    当 DegradationService.is_degraded() 返回 True 时抛出，
    通知上层跳过所有下游调用（Dify / OSS 等）。
    """

    def __init__(self, message: str = "图像生成服务降级中，请稍后再试"):
        super().__init__(message)
        self.message = message

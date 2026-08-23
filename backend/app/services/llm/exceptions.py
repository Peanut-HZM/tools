"""LLM 调用相关的异常类型

用于 OrderedLLMGateway 的兜底链错误分类：
  - RecoverableFailure: 跳过当前模型，尝试下一个
  - UnrecoverableFailure: 立即抛出，不再尝试
  - AllModelsUnavailableError: 所有模型都失败
"""


class RecoverableFailure(Exception):
    """可恢复失败（429/5xx/超时/无额度），兜底链应跳过"""


class UnrecoverableFailure(Exception):
    """不可恢复失败（401/400 参数错），兜底链应抛出"""


class AllModelsUnavailableError(Exception):
    """所有模型都不可用"""

    def __init__(self, failures: list[tuple[str, str]]):
        """failures: [(model_id, reason), ...]"""
        self.failures = failures
        super().__init__(f"所有模型均不可用: {failures}")


class OperationNotSupportedError(RecoverableFailure):
    """当前 provider 不支持指定操作（兜底链应跳过）"""

    def __init__(self, provider_type: str, operation: str):
        self.provider_type = provider_type
        self.operation = operation
        super().__init__(f"{provider_type} 不支持操作 {operation}")


class UnknownProviderError(Exception):
    """未知的 provider_type（Factory 报错）"""

    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        super().__init__(f"未知的 provider_type: {provider_type}")

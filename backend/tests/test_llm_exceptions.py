"""LLM 异常类型测试"""

import pytest

from app.services.llm.exceptions import (
    AllModelsUnavailableError,
    OperationNotSupportedError,
    RecoverableFailure,
    UnrecoverableFailure,
    UnknownProviderError,
)


def test_recoverable_is_exception():
    e = RecoverableFailure("rate limited")
    assert isinstance(e, Exception)


def test_unrecoverable_is_exception():
    e = UnrecoverableFailure("invalid api key")
    assert isinstance(e, Exception)


def test_all_models_unavailable_carries_failures():
    e = AllModelsUnavailableError([("m1", "rate limit"), ("m2", "quota")])
    assert e.failures == [("m1", "rate limit"), ("m2", "quota")]


def test_operation_not_supported():
    e = OperationNotSupportedError("openai_image", "inpaint")
    assert e.provider_type == "openai_image"
    assert e.operation == "inpaint"


def test_unknown_provider():
    e = UnknownProviderError("some_provider")
    assert e.provider_type == "some_provider"

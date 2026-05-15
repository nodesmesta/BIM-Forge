from enum import Enum
from typing import Optional, Dict, Any


class ProductionError(Exception):
    def __init__(
        self,
        message: str,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.retryable = retryable
        self.details = details or {}
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.message}"


class PromptUnparseableError(ProductionError):
    def __init__(self, message: str, prompt: str = None, **kwargs):
        super().__init__(
            message,
            retryable=False,
            details={"prompt_preview": prompt[:200] if prompt else None, **kwargs}
        )


class LLMInternalError(ProductionError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, details=kwargs)


class LLMServiceError(ProductionError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, details=kwargs)


class RateLimitError(LLMServiceError):
    def __init__(self, message: str = "Rate limit exceeded", retry_after: float = None, **kwargs):
        super().__init__(message, retry_after=retry_after, **kwargs)


class TimeoutError(LLMServiceError):
    def __init__(self, message: str = "Request timeout", timeout: float = None, **kwargs):
        super().__init__(message, timeout=timeout, **kwargs)


class NetworkError(LLMServiceError):
    def __init__(self, message: str = "Network error", **kwargs):
        super().__init__(message, **kwargs)


class MaxRetriesExceeded(ProductionError):
    def __init__(self, message: str, max_attempts: int, last_error: str = None, **kwargs):
        super().__init__(
            message,
            retryable=False,
            details={"max_attempts": max_attempts, "last_error": last_error, **kwargs}
        )


class IFCGenerationError(ProductionError):
    def __init__(self, message: str, element_type: str = None, **kwargs):
        super().__init__(message, retryable=False, details={"element_type": element_type, **kwargs})


class BlenderRenderError(ProductionError):
    def __init__(self, message: str, is_transient: bool = False, **kwargs):
        super().__init__(message, retryable=is_transient, details={"is_transient": is_transient, **kwargs})


class ValidationError(ProductionError):
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, retryable=False, details={"field": field, **kwargs})

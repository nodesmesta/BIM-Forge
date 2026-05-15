"""
Retry utilities with exponential backoff and circuit breaker pattern.

This module provides retry logic for agent operations that may fail transiently.
"""

import asyncio
import random
from typing import Callable, TypeVar, Any, Optional, List
from functools import wraps
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel


logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """Raised when all retry attempts fail."""

    def __init__(self, message: str, last_error: Optional[Exception] = None, attempts: int = 0):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    delay_multiplier: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[str] = []  # Exception class names to retry on
    timeout: Optional[float] = None  # Timeout per attempt in seconds


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds before attempting reset
    half_open_requests: int = 3  # Requests allowed in half-open state


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    def __init__(self, config: CircuitBreakerConfig = None):
        self.config = config or CircuitBreakerConfig()
        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_requests = 0

    @property
    def state(self) -> str:
        return self._state

    def can_execute(self) -> bool:
        """Check if a request can be executed."""
        if self._state == "CLOSED":
            return True

        if self._state == "OPEN":
            # Check if recovery timeout has passed
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    self._state = "HALF_OPEN"
                    self._half_open_requests = 0
                    return True
            return False

        if self._state == "HALF_OPEN":
            if self._half_open_requests < self.config.half_open_requests:
                self._half_open_requests += 1
                return True
            return False

        return False

    def record_success(self):
        """Record a successful execution."""
        if self._state == "HALF_OPEN":
            self._success_count += 1
            if self._success_count >= self.config.half_open_requests:
                self._state = "CLOSED"
                self._failure_count = 0
                self._success_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        elif self._state == "CLOSED":
            self._failure_count = 0

    def record_failure(self):
        """Record a failed execution."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == "HALF_OPEN":
            self._state = "OPEN"
            logger.warning(f"Circuit breaker OPEN - too many failures: {self._failure_count}")
        elif self._state == "CLOSED" and self._failure_count >= self.config.failure_threshold:
            self._state = "OPEN"
            logger.warning(f"Circuit breaker OPEN - threshold reached: {self._failure_count}")

    def reset(self):
        """Reset the circuit breaker."""
        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0


class RetryHandler:
    """
    Handles retry logic with exponential backoff.

    Usage:
        retry_handler = RetryHandler(config)

        @retry_handler.retry
        async def my_operation():
            await some_async_operation()

        # Or use directly:
        result = await retry_handler.execute(my_operation)
    """

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self._circuit_breakers: dict = {}

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a named operation."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker()
        return self._circuit_breakers[name]

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt using exponential backoff."""
        delay = self.config.initial_delay * (self.config.delay_multiplier ** attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            delay = delay * (0.5 + random.random())  # Add jitter

        return delay

    def is_retryable(self, exception: Exception) -> bool:
        """Check if an exception is retryable."""
        if not self.config.retryable_exceptions:
            return True  # Retry all if no filter specified

        exception_name = exception.__class__.__name__
        return exception_name in self.config.retryable_exceptions

    async def execute(
        self,
        func: Callable[..., Any],
        *args,
        operation_name: str = "unknown",
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            operation_name: Name for logging and circuit breaker
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function

        Raises:
            RetryError: If all attempts fail
            CircuitBreakerError: If circuit breaker is open
        """
        circuit_breaker = self.get_circuit_breaker(operation_name)

        # Check circuit breaker
        if not circuit_breaker.can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker open for {operation_name}"
            )

        last_error = None

        for attempt in range(self.config.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.config.max_attempts} for {operation_name}")

                # Execute with optional timeout
                if self.config.timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.config.timeout
                    )
                else:
                    result = await func(*args, **kwargs)

                # Success
                circuit_breaker.record_success()
                if attempt > 0:
                    logger.info(
                        f"Operation {operation_name} succeeded on attempt {attempt + 1}"
                    )
                return result

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")

            except Exception as e:
                last_error = e
                if not self.is_retryable(e):
                    logger.error(f"Non-retryable error: {e}")
                    circuit_breaker.record_failure()
                    raise
                logger.warning(f"Retryable error on attempt {attempt + 1}: {e}")

            circuit_breaker.record_failure()

            # Don't sleep after last attempt
            if attempt < self.config.max_attempts - 1:
                delay = self.calculate_delay(attempt)
                logger.info(f"Retrying {operation_name} in {delay:.2f}s...")
                await asyncio.sleep(delay)

        # All attempts failed
        error_msg = f"Operation {operation_name} failed after {self.config.max_attempts} attempts"
        logger.error(error_msg)
        raise RetryError(
            message=error_msg,
            last_error=last_error,
            attempts=self.config.max_attempts
        )

    def retry(self, operation_name: str = None):
        """
        Decorator for adding retry logic to async functions.

        Usage:
            @retry_handler.retry(operation_name="my_operation")
            async def my_operation():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                op_name = operation_name or func.__name__
                return await self.execute(
                    func,
                    *args,
                    operation_name=op_name,
                    **kwargs
                )
            return wrapper
        return decorator


# Default retry handler instance
_default_retry_handler: Optional[RetryHandler] = None


def get_retry_handler(config: RetryConfig = None) -> RetryHandler:
    """Get or create the default retry handler."""
    global _default_retry_handler
    if _default_retry_handler is None:
        _default_retry_handler = RetryHandler(config)
    return _default_retry_handler


# Common exception types that are typically retryable
RETRYABLE_EXCEPTIONS = [
    "ConnectionError",
    "TimeoutError",
    "NetworkError",
    "ServiceUnavailableError",
    "RateLimitError",
    "TemporaryError",
]

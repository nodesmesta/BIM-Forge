import asyncio
import random
from typing import Callable, Any, TypeVar
from .errors import (
    ProductionError,
    LLMServiceError,
    RateLimitError,
    TimeoutError,
    NetworkError,
    MaxRetriesExceeded
)

T = TypeVar('T')


class RetryOrchestrator:
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 2.0,
        max_delay: float = 30.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def _calculate_delay(self, attempt: int) -> float:
        delay = self.initial_delay * (2 ** attempt)
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay *= (0.5 + random.random())
        return delay

    async def execute(self, func: Callable, *args, **kwargs) -> T:
        last_error = None

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)

            except (LLMServiceError, RateLimitError, TimeoutError, NetworkError) as e:
                last_error = e

                if attempt >= self.max_attempts - 1:
                    raise MaxRetriesExceeded(
                        f"Failed after {attempt + 1} attempts: {e}",
                        max_attempts=attempt + 1,
                        last_error=str(e)
                    ) from e

                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

            except ProductionError:
                raise

            except Exception as e:
                raise ProductionError(f"Unexpected error: {type(e).__name__}: {e}") from e

        raise MaxRetriesExceeded(
            "Unexpected code path reached",
            max_attempts=self.max_attempts,
            last_error=str(last_error) if last_error else "unknown"
        )


_default_orchestrator: RetryOrchestrator = None


def get_retry_orchestrator(
    max_attempts: int = 3,
    initial_delay: float = 2.0,
    max_delay: float = 30.0
) -> RetryOrchestrator:
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = RetryOrchestrator(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay
        )
    return _default_orchestrator

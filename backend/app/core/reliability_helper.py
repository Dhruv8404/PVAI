import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger("app.ai")


class CircuitBreakerOpenException(Exception):
    """Exception raised when the circuit breaker is open."""
    pass


class CircuitBreaker:
    """Implements the Circuit Breaker pattern to protect external API calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_time_secs: int = 60, name: str = "External Service"):
        self.failure_threshold = failure_threshold
        self.recovery_time_secs = recovery_time_secs
        self.name = name
        
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0
        self.required_successes = 3  # successes needed in HALF-OPEN to close

    def record_success(self):
        if self.state == "HALF-OPEN":
            self.success_count += 1
            if self.success_count >= self.required_successes:
                logger.info(f"[CIRCUIT BREAKER] {self.name} circuit closed (recovered).")
                self.state = "CLOSED"
                self.failure_count = 0
        elif self.state == "CLOSED":
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(f"[CIRCUIT BREAKER] {self.name} failed. Failure count: {self.failure_count}/{self.failure_threshold}")
        
        if self.state in ["CLOSED", "HALF-OPEN"] and self.failure_count >= self.failure_threshold:
            logger.error(f"[CIRCUIT BREAKER] {self.name} circuit opened (tripped). Stays open for {self.recovery_time_secs}s.")
            self.state = "OPEN"

    def check_state(self):
        if self.state == "OPEN":
            # Check if recovery cooldown has elapsed
            if time.time() - self.last_failure_time > self.recovery_time_secs:
                logger.info(f"[CIRCUIT BREAKER] {self.name} circuit transitioned to HALF-OPEN.")
                self.state = "HALF-OPEN"
                self.success_count = 0
            else:
                raise CircuitBreakerOpenException(
                    f"{self.name} circuit is temporarily open due to repeated failures."
                )


def retry_with_backoff(retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0, exception_types: tuple = (Exception,)):
    """Async decorator that retries a function with exponential backoff."""
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exception_types as e:
                    # Do not retry circuit breaker open exceptions or timeout pings if already failed
                    if isinstance(e, CircuitBreakerOpenException) or attempt == retries:
                        raise e
                    
                    logger.warning(
                        f"Attempt {attempt}/{retries} for {func.__name__} failed with error: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Singleton circuit breakers for system services
llm_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_time_secs=60, name="LLM Provider Gateway")
embeddings_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_time_secs=60, name="SentenceTransformer Model")


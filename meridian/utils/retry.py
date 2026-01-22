"""Retry logic with exponential backoff for MERIDIAN"""

import time
import random
from typing import Any, Callable, Optional, Type, Tuple
from functools import wraps

from meridian.logging_config import get_logger

logger = get_logger("meridian.retry")


class RetryError(Exception):
    """Raised when all retry attempts fail"""
    
    def __init__(self, message: str, last_error: Optional[Exception] = None, attempts: int = 0):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts
        self.message = message
        
    def __str__(self):
        if self.last_error:
            return f"{self.message} after {self.attempts} attempts. Last error: {self.last_error}"
        return f"{self.message} after {self.attempts} attempts"


def exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retriable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delays
        retriable_exceptions: Tuple of exceptions to retry on
        
    Example:
        @exponential_backoff(max_retries=5, initial_delay=2)
        def call_api():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        # Log retry attempt
                        logger.info(
                            f"Retrying {func.__name__} (attempt {attempt + 1}/{max_retries + 1})",
                            extra={
                                "operation": "retry",
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "delay": delay
                            }
                        )
                    
                    # Try to execute the function
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            f"Retry successful for {func.__name__} on attempt {attempt + 1}",
                            extra={
                                "operation": "retry_success",
                                "function": func.__name__,
                                "attempt": attempt + 1
                            }
                        )
                    
                    return result
                    
                except retriable_exceptions as e:
                    last_exception = e
                    
                    # Log the error
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}",
                        extra={
                            "operation": "retry_failure",
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                    
                    # If this was the last attempt, raise
                    if attempt >= max_retries:
                        logger.error(
                            f"All retry attempts failed for {func.__name__}",
                            extra={
                                "operation": "retry_exhausted",
                                "function": func.__name__,
                                "total_attempts": attempt + 1
                            }
                        )
                        raise RetryError(
                            f"Failed to execute {func.__name__}",
                            last_error=last_exception,
                            attempts=attempt + 1
                        )
                    
                    # Calculate next delay
                    if jitter:
                        # Add jitter: delay * (0.5 to 1.5)
                        actual_delay = delay * (0.5 + random.random())
                    else:
                        actual_delay = delay
                    
                    # Sleep before retry
                    logger.debug(f"Waiting {actual_delay:.2f} seconds before retry")
                    time.sleep(actual_delay)
                    
                    # Update delay for next iteration
                    delay = min(delay * exponential_base, max_delay)
            
            # Should never reach here, but just in case
            raise RetryError(
                f"Unexpected retry failure for {func.__name__}",
                last_error=last_exception,
                attempts=max_retries + 1
            )
        
        return wrapper
    return decorator


def retry_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    max_retries: int = 3,
    **retry_kwargs
) -> Any:
    """
    Try primary function with retries, fall back to alternative on failure.
    
    Args:
        primary_func: Primary function to try
        fallback_func: Fallback function if primary fails
        max_retries: Max retries for primary function
        **retry_kwargs: Additional args for exponential_backoff
        
    Returns:
        Result from primary or fallback function
        
    Example:
        result = retry_with_fallback(
            primary_func=lambda: call_claude_api(prompt),
            fallback_func=lambda: call_local_llm(prompt),
            max_retries=3
        )
    """
    try:
        # Try primary with retries
        decorated_primary = exponential_backoff(
            max_retries=max_retries,
            **retry_kwargs
        )(primary_func)
        
        result = decorated_primary()
        logger.info("Primary function succeeded", extra={"operation": "fallback", "used": "primary"})
        return result
        
    except RetryError as e:
        logger.warning(
            f"Primary function failed, trying fallback: {e}",
            extra={"operation": "fallback", "reason": str(e)}
        )
        
        try:
            result = fallback_func()
            logger.info("Fallback function succeeded", extra={"operation": "fallback", "used": "fallback"})
            return result
        except Exception as fallback_error:
            logger.error(
                f"Both primary and fallback failed",
                extra={
                    "operation": "fallback_failed",
                    "primary_error": str(e),
                    "fallback_error": str(fallback_error)
                }
            )
            raise RetryError(
                "Both primary and fallback functions failed",
                last_error=fallback_error,
                attempts=1
            )


class RetryableOperation:
    """
    Context manager for retryable operations with state tracking.
    
    Example:
        with RetryableOperation("fetch_data", max_retries=5) as op:
            for attempt in op:
                try:
                    data = fetch_data()
                    op.success()
                    break
                except Exception as e:
                    op.failure(e)
    """
    
    def __init__(
        self,
        operation_name: str,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.operation_name = operation_name
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.current_attempt = 0
        self.current_delay = initial_delay
        self.succeeded = False
        self.last_error = None
        
    def __enter__(self):
        logger.info(f"Starting retryable operation: {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.succeeded and exc_type is not None:
            logger.error(
                f"Retryable operation failed: {self.operation_name}",
                extra={
                    "operation": self.operation_name,
                    "attempts": self.current_attempt,
                    "error": str(exc_val)
                }
            )
        return False
        
    def __iter__(self):
        return self
        
    def __next__(self):
        if self.current_attempt >= self.max_retries + 1:
            raise StopIteration
        
        if self.current_attempt > 0:
            # Wait before retry
            time.sleep(self.current_delay)
            self.current_delay = min(
                self.current_delay * self.exponential_base,
                self.max_delay
            )
            
        self.current_attempt += 1
        return self.current_attempt
        
    def success(self):
        """Mark the operation as successful"""
        self.succeeded = True
        if self.current_attempt > 1:
            logger.info(
                f"Operation succeeded on attempt {self.current_attempt}: {self.operation_name}"
            )
            
    def failure(self, error: Exception):
        """Record a failure"""
        self.last_error = error
        logger.warning(
            f"Attempt {self.current_attempt} failed for {self.operation_name}: {error}"
        )
        
        if self.current_attempt >= self.max_retries + 1:
            raise RetryError(
                f"Operation {self.operation_name} failed",
                last_error=error,
                attempts=self.current_attempt
            )
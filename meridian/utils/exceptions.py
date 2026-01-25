"""Enhanced exception handling with context for MERIDIAN"""

from typing import Any, Dict, Optional
from pathlib import Path
import traceback

from meridian.logging_config import get_logger

logger = get_logger("meridian.exceptions")


class MeridianError(Exception):
    """Base exception for MERIDIAN with context information"""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        mode: Optional[str] = None,
        artifact_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.operation = operation or "unknown"
        self.mode = mode or "system"
        self.artifact_id = artifact_id or "none"
        self.context = context or {}
        self.cause = cause
        
        # Log the error with context
        logger.error(
            message,
            extra={
                "operation": self.operation,
                "mode": self.mode,
                "artifact_id": self.artifact_id,
                "context": self.context,
                "cause": str(cause) if cause else None
            },
            exc_info=cause
        )
    
    def __str__(self):
        parts = [self.message]
        
        if self.operation != "unknown":
            parts.append(f"Operation: {self.operation}")
        if self.mode != "system":
            parts.append(f"Mode: {self.mode}")
        if self.artifact_id != "none":
            parts.append(f"Artifact: {self.artifact_id}")
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
            
        return " | ".join(parts)


class DataError(MeridianError):
    """Raised when data validation or processing fails"""
    pass


class GateError(MeridianError):
    """Raised when gate conditions are not met"""
    pass


class ArtifactError(MeridianError):
    """Raised when artifact operations fail"""
    pass


class LLMError(MeridianError):
    """Raised when LLM operations fail"""
    pass


class ConfigError(MeridianError):
    """Raised when configuration is invalid"""
    pass


class FileOperationError(MeridianError):
    """Raised when file operations fail"""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None,
        operation_type: str = "unknown",
        **kwargs
    ):
        if file_path:
            kwargs["context"] = kwargs.get("context", {})
            kwargs["context"]["file_path"] = str(file_path)
            kwargs["context"]["operation_type"] = operation_type
        
        super().__init__(message, **kwargs)


def handle_exception(
    operation: str,
    mode: Optional[str] = None,
    artifact_id: Optional[str] = None,
    reraise: bool = True,
    default_return: Any = None
):
    """
    Decorator for handling exceptions with context.
    
    Args:
        operation: Name of the operation being performed
        mode: Mode context
        artifact_id: Artifact context
        reraise: Whether to reraise the exception
        default_return: Value to return if exception is caught and not reraised
        
    Example:
        @handle_exception("load_data", mode="2")
        def load_data(path):
            return pd.read_csv(path)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except MeridianError:
                # Already handled, just reraise
                if reraise:
                    raise
                return default_return
            except Exception as e:
                # Extract context from function arguments
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],  # Truncate long args
                    "kwargs": str(kwargs)[:200]
                }
                
                # Create appropriate exception type
                error_class = MeridianError
                if "file" in str(e).lower() or isinstance(e, (IOError, OSError)):
                    error_class = FileOperationError
                elif "data" in operation.lower():
                    error_class = DataError
                elif "gate" in operation.lower():
                    error_class = GateError
                elif "artifact" in operation.lower():
                    error_class = ArtifactError
                elif "llm" in operation.lower() or "api" in operation.lower():
                    error_class = LLMError
                
                # Wrap the exception with context
                wrapped_error = error_class(
                    f"Failed to {operation}: {str(e)}",
                    operation=operation,
                    mode=mode,
                    artifact_id=artifact_id,
                    context=context,
                    cause=e
                )
                
                if reraise:
                    raise wrapped_error
                    
                return default_return
                
        return wrapper
    return decorator


class ErrorContext:
    """
    Context manager for error handling with detailed context.
    
    Example:
        with ErrorContext("processing_data", mode="2", data_path=str(path)):
            df = pd.read_csv(path)
            # process data
    """
    
    def __init__(
        self,
        operation: str,
        mode: Optional[str] = None,
        artifact_id: Optional[str] = None,
        reraise: bool = True,
        **context
    ):
        self.operation = operation
        self.mode = mode or "system"
        self.artifact_id = artifact_id or "none"
        self.reraise = reraise
        self.context = context
        
        logger.debug(
            f"Entering operation: {operation}",
            extra={
                "operation": operation,
                "mode": self.mode,
                "artifact_id": self.artifact_id,
                "context": context
            }
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            logger.debug(
                f"Operation completed successfully: {self.operation}",
                extra={
                    "operation": self.operation,
                    "mode": self.mode,
                    "artifact_id": self.artifact_id
                }
            )
            return False
        
        # Don't re-wrap our own exceptions
        if isinstance(exc_val, MeridianError):
            return False
        
        # Enhance the exception with context
        tb_str = ''.join(traceback.format_tb(exc_tb))
        
        error_class = MeridianError
        if issubclass(exc_type, (IOError, OSError)):
            error_class = FileOperationError
        
        wrapped_error = error_class(
            f"Operation '{self.operation}' failed: {exc_val}",
            operation=self.operation,
            mode=self.mode,
            artifact_id=self.artifact_id,
            context={
                **self.context,
                "exception_type": exc_type.__name__,
                "traceback": tb_str[-500:]  # Last 500 chars of traceback
            },
            cause=exc_val
        )
        
        if self.reraise:
            raise wrapped_error from exc_val
        
        return True  # Suppress the exception


def validate_input(
    value: Any,
    expected_type: type,
    name: str,
    operation: str,
    mode: Optional[str] = None,
    allow_none: bool = False
) -> Any:
    """
    Validate input with detailed error reporting.
    
    Args:
        value: Value to validate
        expected_type: Expected type
        name: Name of the parameter
        operation: Operation context
        mode: Mode context
        allow_none: Whether None is allowed
        
    Returns:
        The validated value
        
    Raises:
        DataError: If validation fails
        
    Example:
        data_path = validate_input(
            data_path, Path, "data_path", "load_data", mode="2"
        )
    """
    if value is None:
        if allow_none:
            return value
        raise DataError(
            f"Required parameter '{name}' is None",
            operation=f"validate_{operation}",
            mode=mode,
            context={"parameter": name, "expected_type": expected_type.__name__}
        )
    
    if not isinstance(value, expected_type):
        raise DataError(
            f"Parameter '{name}' has wrong type: expected {expected_type.__name__}, "
            f"got {type(value).__name__}",
            operation=f"validate_{operation}",
            mode=mode,
            context={
                "parameter": name,
                "expected_type": expected_type.__name__,
                "actual_type": type(value).__name__,
                "value": str(value)[:100]  # First 100 chars
            }
        )
    
    return value
"""Structured logging configuration for MERIDIAN"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Create logs directory
LOGS_DIR = Path.home() / ".meridian" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class ContextFilter(logging.Filter):
    """Add context information to log records"""
    
    def filter(self, record):
        # Add default context if not present
        if not hasattr(record, 'mode'):
            record.mode = 'system'
        if not hasattr(record, 'artifact_id'):
            record.artifact_id = 'none'
        if not hasattr(record, 'operation'):
            record.operation = 'general'
        return True


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True
) -> logging.Logger:
    """
    Configure structured logging for MERIDIAN.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file
        console: Whether to log to console
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("meridian")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Format with useful context
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - '
        '[%(mode)s:%(operation)s:%(artifact_id)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file is None:
        log_file = LOGS_DIR / "meridian.log"
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG in file
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Add context filter
    context_filter = ContextFilter()
    for handler in logger.handlers:
        handler.addFilter(context_filter)
    
    # Log startup
    logger.info("MERIDIAN logging initialized", extra={
        "operation": "startup",
        "log_level": level,
        "log_file": str(log_file)
    })
    
    return logger


def get_logger(name: str = "meridian") -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


def log_operation(operation: str, mode: str = "system", artifact_id: str = "none"):
    """
    Context manager for logging operations.
    
    Usage:
        with log_operation("mode_execution", mode="2", artifact_id="abc-123"):
            # Your code here
    """
    class LogContext:
        def __init__(self, op, md, aid):
            self.operation = op
            self.mode = md
            self.artifact_id = aid
            self.logger = get_logger()
            
        def __enter__(self):
            self.logger.info(
                f"Starting {self.operation}",
                extra={
                    "operation": self.operation,
                    "mode": self.mode,
                    "artifact_id": self.artifact_id
                }
            )
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.logger.info(
                    f"Completed {self.operation}",
                    extra={
                        "operation": self.operation,
                        "mode": self.mode,
                        "artifact_id": self.artifact_id
                    }
                )
            else:
                self.logger.error(
                    f"Failed {self.operation}: {exc_val}",
                    extra={
                        "operation": self.operation,
                        "mode": self.mode,
                        "artifact_id": self.artifact_id,
                        "error_type": exc_type.__name__
                    },
                    exc_info=True
                )
            return False
    
    return LogContext(operation, mode, artifact_id)


# Initialize default logger
DEFAULT_LOGGER = setup_logging()
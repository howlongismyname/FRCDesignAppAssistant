"""Logging configuration and utilities."""

import logging
import logging.handlers
import sys
from typing import Optional, Dict, Any
from datetime import datetime
import json
from pathlib import Path

from .config import LoggingConfig


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in (
                    "name", "msg", "args", "levelname", "levelno", "pathname", 
                    "filename", "module", "lineno", "funcName", "created", 
                    "msecs", "relativeCreated", "thread", "threadName", 
                    "processName", "process", "message", "exc_info", "exc_text",
                    "stack_info"
                ):
                    log_entry[key] = value
        
        # Add source location for debug level
        if record.levelno <= logging.DEBUG:
            log_entry["source"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName
            }
        
        return json.dumps(log_entry, default=str)


class ContextFilter(logging.Filter):
    """Add context information to log records."""
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_operation(
        self, 
        operation: str, 
        duration_ms: float, 
        success: bool = True,
        **kwargs
    ):
        """Log operation performance."""
        self.logger.info(
            "Operation completed",
            extra={
                "operation": operation,
                "duration_ms": duration_ms,
                "success": success,
                **kwargs
            }
        )
    
    def log_api_call(
        self,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        **kwargs
    ):
        """Log API call performance."""
        self.logger.info(
            "API call completed",
            extra={
                "api_method": method,
                "api_url": url,
                "api_status_code": status_code,
                "duration_ms": duration_ms,
                "success": 200 <= status_code < 400,
                **kwargs
            }
        )


def setup_logging(config: LoggingConfig) -> None:
    """Setup logging configuration."""
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    if config.console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.level))
        
        # Use JSON format for production, simple format for development
        if config.level == "DEBUG":
            console_formatter = logging.Formatter(config.format)
        else:
            console_formatter = JSONFormatter()
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if config.file:
        file_path = Path(config.file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.file,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count
        )
        file_handler.setLevel(getattr(logging, config.level))
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Set levels for specific loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Setup application loggers
    app_logger = logging.getLogger("design_assistant")
    app_logger.setLevel(getattr(logging, config.level))


def get_logger(name: str) -> logging.Logger:
    """Get logger with design assistant prefix."""
    return logging.getLogger(f"design_assistant.{name}")


class TimingContextManager:
    """Context manager for timing operations."""
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds() * 1000
        
        if exc_type is None:
            self.logger.log(
                self.level, 
                f"Completed {self.operation}",
                extra={"duration_ms": duration, "success": True}
            )
        else:
            self.logger.error(
                f"Failed {self.operation}: {exc_val}",
                extra={"duration_ms": duration, "success": False},
                exc_info=True
            )


def log_timing(operation: str, level: int = logging.INFO):
    """Decorator for timing function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            with TimingContextManager(logger, f"{func.__name__}({operation})", level):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def log_async_timing(operation: str, level: int = logging.INFO):
    """Decorator for timing async function execution."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            with TimingContextManager(logger, f"{func.__name__}({operation})", level):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


class StructuredLogger:
    """Structured logger with built-in context."""
    
    def __init__(self, name: str, context: Dict[str, Any] = None):
        self.logger = get_logger(name)
        self.context = context or {}
    
    def _log(self, level: int, message: str, **kwargs):
        """Log with context and additional kwargs."""
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def with_context(self, **context) -> "StructuredLogger":
        """Create new logger with additional context."""
        new_context = {**self.context, **context}
        return StructuredLogger(self.logger.name, new_context)


# Common loggers
def get_bom_logger() -> StructuredLogger:
    """Get logger for BOM operations."""
    return StructuredLogger("bom")


def get_thumbnail_logger() -> StructuredLogger:
    """Get logger for thumbnail operations."""
    return StructuredLogger("thumbnail")


def get_onshape_logger() -> StructuredLogger:
    """Get logger for Onshape API operations."""
    return StructuredLogger("onshape")


def get_cache_logger() -> StructuredLogger:
    """Get logger for cache operations."""
    return StructuredLogger("cache")


# Request ID context manager
class RequestContext:
    """Context manager for request-scoped logging."""
    
    def __init__(self, request_id: str, user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id
        self.filter = ContextFilter({
            "request_id": request_id,
            "user_id": user_id
        })
    
    def __enter__(self):
        # Add filter to all handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.addFilter(self.filter)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove filter from all handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.removeFilter(self.filter)
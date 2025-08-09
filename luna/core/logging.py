"""
Structured logging configuration for L.U.N.A. with correlation tracking.
"""
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

from .types import CorrelationId, LogLevel


# Context variable for correlation ID tracking
current_correlation_id: ContextVar[Optional[CorrelationId]] = ContextVar('correlation_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter that includes correlation IDs and structured fields.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Build the base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        correlation_id = current_correlation_id.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id.value
            
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        # Add any extra fields from the log record
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        return json.dumps(log_entry, default=str)


class CorrelationAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes correlation IDs.
    """
    
    def process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple[Any, Dict[str, Any]]:
        correlation_id = current_correlation_id.get()
        if correlation_id and 'extra' not in kwargs:
            kwargs['extra'] = {'correlation_id': correlation_id.value}
        elif correlation_id and 'extra' in kwargs:
            kwargs['extra']['correlation_id'] = correlation_id.value
        
        return msg, kwargs


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    structured: bool = True,
    include_console: bool = True,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for L.U.N.A.
    
    Args:
        level: Logging level
        structured: Whether to use structured JSON logging
        include_console: Whether to log to console
        log_file: Optional file path for logging
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root level
    root_logger.setLevel(level.value)
    
    # Choose formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Silence noisy third-party loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('ollama').setLevel(logging.WARNING)


def get_logger(name: str) -> CorrelationAdapter:
    """
    Get a logger with correlation ID support.
    
    Args:
        name: Logger name
        
    Returns:
        Logger with correlation support
    """
    logger = logging.getLogger(name)
    return CorrelationAdapter(logger, {})


def set_correlation_id(correlation_id: Optional[CorrelationId]) -> None:
    """Set the current correlation ID for logging."""
    current_correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[CorrelationId]:
    """Get the current correlation ID."""
    return current_correlation_id.get()


def with_correlation_id(correlation_id: CorrelationId):
    """Context manager for setting correlation ID."""
    from contextlib import contextmanager
    
    @contextmanager
    def _context():
        token = current_correlation_id.set(correlation_id)
        try:
            yield
        finally:
            current_correlation_id.reset(token)
    
    return _context()


class LoggingMixin:
    """
    Mixin class that provides logging capabilities to any class.
    """
    
    @property
    def logger(self) -> CorrelationAdapter:
        """Get a logger for this class."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def log_with_correlation(
        self,
        level: LogLevel,
        message: str,
        correlation_id: Optional[CorrelationId] = None,
        **extra_fields
    ) -> None:
        """Log a message with optional correlation ID and extra fields."""
        if correlation_id:
            with with_correlation_id(correlation_id):
                getattr(self.logger, level.lower())(message, extra={"extra_fields": extra_fields})
        else:
            getattr(self.logger, level.lower())(message, extra={"extra_fields": extra_fields})
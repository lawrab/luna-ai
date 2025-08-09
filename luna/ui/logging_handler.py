"""
Custom logging handler that integrates with the split terminal UI.
"""
import logging
from typing import Optional

from .terminal import get_terminal_ui


class SplitUILogHandler(logging.Handler):
    """
    Logging handler that sends messages to the split terminal UI.
    """
    
    def __init__(self, level: int = logging.NOTSET):
        super().__init__(level)
        self.ui = get_terminal_ui()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the UI."""
        try:
            # Format the message
            message = self.format(record)
            
            # Strip the logger name from the formatted message since UI handles it
            # Most formatters include the logger name, but we want to handle it separately
            if hasattr(record, 'getMessage'):
                clean_message = record.getMessage()
            else:
                clean_message = str(record.msg)
            
            # Send to UI
            self.ui.add_log_message(
                level=record.levelname,
                logger_name=record.name,
                message=clean_message
            )
        except Exception:
            # Don't let logging errors crash the application
            pass


def setup_ui_logging(level: int = logging.INFO) -> None:
    """
    Set up logging to use the split UI handler and prevent console output.
    """
    # Create the UI handler
    ui_handler = SplitUILogHandler()
    ui_handler.setLevel(level)
    
    # Create a simple formatter (UI handles the formatting)
    formatter = logging.Formatter('%(message)s')
    ui_handler.setFormatter(formatter)
    
    # Get the root logger and completely replace all handlers
    root_logger = logging.getLogger()
    
    # Clear all existing handlers completely
    root_logger.handlers.clear()
    
    # Add only our UI handler
    root_logger.addHandler(ui_handler)
    root_logger.setLevel(level)
    
    # Ensure no console output anywhere
    root_logger.propagate = False
    
    # Configure all loggers that might be used
    for logger_name in ['luna', '__main__', 'asyncio']:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.handlers.clear()
        logger_obj.addHandler(ui_handler)
        logger_obj.setLevel(level)
        logger_obj.propagate = False
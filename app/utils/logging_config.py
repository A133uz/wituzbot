"""
Centralized logging configuration for all services (bot, admin, celery).
Provides structured, consistent log output across the entire application.
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional


class JSONFormatter(logging.Formatter):
    """
    Simple structured formatter that outputs JSON-like fields.
    Useful for log aggregation systems.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Build a consistent message with service/level/message fields
        level = record.levelname
        service = record.name.split('.')[1] if '.' in record.name else 'app'
        msg = record.getMessage()
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        
        # If there's an exception, include the traceback
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            return f"{timestamp} | {service:15} | {level:8} | {msg}\n{exc_text}"
        
        return f"{timestamp} | {service:15} | {level:8} | {msg}"


def configure_logging(
    service_name: str = "app",
    level: Optional[str] = None,
    use_json: bool = False
) -> None:
    """
    Configure root logger and all handlers for consistent output.
    
    Args:
        service_name: Service identifier (admin, bot, feedback-bot, celery)
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to env var LOG_LEVEL or INFO.
        use_json: If True, use JSON formatter for structured logging. Default False for now.
    """
    
    # Get log level from parameter, env var, or default to INFO
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    log_level = getattr(logging, level, logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create stdout handler (all services should log to stdout for Docker)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    
    # Choose formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        # Simple format with timestamp, service, level, and message
        formatter = logging.Formatter(
            f"%(asctime)s | {service_name:15} | %(levelname)-8s | %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)
    
    # Suppress overly verbose third-party logs
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Log the startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {service_name} at {level} level")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance. Wrapper for logging.getLogger with a consistent naming convention.
    """
    return logging.getLogger(name)

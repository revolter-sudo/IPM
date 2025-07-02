"""
Centralized logging configuration for the IPM application.

This module provides a standardized logging setup with:
- Timestamped log entries
- File rotation to prevent large log files
- Console and file output
- Persistent storage outside Docker containers
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path


class TimestampedFormatter(logging.Formatter):
    """Custom formatter that ensures consistent timestamp format across all logs."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def formatTime(self, record, datefmt=None):
        """Override to ensure consistent timezone handling."""
        ct = self.converter(record.created)
        if datefmt:
            s = datetime(*ct[:6]).strftime(datefmt)
        else:
            s = datetime(*ct[:6]).strftime("%Y-%m-%d %H:%M:%S")
        return s


def setup_logging(
    log_level: str = None,
    log_dir: str = None,
    app_name: str = "ipm",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
):
    """
    Set up centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). If None, uses LOG_LEVEL env var or defaults to INFO
        log_dir: Directory where log files will be stored. If None, uses LOG_DIR env var or defaults to /app/logs
        app_name: Application name for log file naming
        max_file_size: Maximum size of each log file before rotation (bytes)
        backup_count: Number of backup files to keep
    """

    # Use environment variables as fallback if parameters are None
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", "/app/logs")

    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create custom formatter
    formatter = TimestampedFormatter()

    # Console handler for immediate feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Main application log file with rotation
    app_log_file = log_path / f"{app_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(app_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error-specific log file for critical issues
    error_log_file = log_path / f"{app_name}_errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        filename=str(error_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Performance log file for slow queries and performance metrics
    perf_log_file = log_path / f"{app_name}_performance.log"
    perf_handler = logging.handlers.RotatingFileHandler(
        filename=str(perf_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    perf_handler.setLevel(logging.WARNING)
    perf_handler.setFormatter(formatter)

    # Create performance logger
    perf_logger = logging.getLogger("performance")
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.WARNING)
    perf_logger.propagate = False  # Don't propagate to root logger

    # Database operations log file
    db_log_file = log_path / f"{app_name}_database.log"
    db_handler = logging.handlers.RotatingFileHandler(
        filename=str(db_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    db_handler.setLevel(logging.INFO)
    db_handler.setFormatter(formatter)

    # Create database logger
    db_logger = logging.getLogger("database")
    db_logger.addHandler(db_handler)
    db_logger.setLevel(logging.INFO)
    db_logger.propagate = False

    # API requests log file
    api_log_file = log_path / f"{app_name}_api.log"
    api_handler = logging.handlers.RotatingFileHandler(
        filename=str(api_log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(formatter)

    # Create API logger
    api_logger = logging.getLogger("api")
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    api_logger.propagate = False

    # Log the initialization
    logging.info(f"Logging initialized - Log directory: {log_dir}")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Max file size: {max_file_size / (1024*1024):.1f}MB")
    logging.info(f"Backup count: {backup_count}")

    return {
        "main_logger": root_logger,
        "performance_logger": perf_logger,
        "database_logger": db_logger,
        "api_logger": api_logger,
        "log_directory": str(log_path),
    }


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (if None, returns root logger)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_performance_logger() -> logging.Logger:
    """Get the performance-specific logger."""
    return logging.getLogger("performance")


def get_database_logger() -> logging.Logger:
    """Get the database-specific logger."""
    return logging.getLogger("database")


def get_api_logger() -> logging.Logger:
    """Get the API-specific logger."""
    return logging.getLogger("api")


def log_startup_info():
    """Log important startup information."""
    logger = get_logger(__name__)
    logger.info("=" * 50)
    logger.info("IPM Application Starting")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info("=" * 50)


def log_shutdown_info():
    """Log application shutdown information."""
    logger = get_logger(__name__)
    logger.info("=" * 50)
    logger.info("IPM Application Shutting Down")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

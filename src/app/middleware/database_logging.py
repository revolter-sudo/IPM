"""
Database logging middleware to ensure all database operations are properly logged.
"""

import time
from contextlib import contextmanager
from sqlalchemy.orm import Session
from src.app.utils.logging_config import get_database_logger, get_performance_logger

# Get loggers
db_logger = get_database_logger()
perf_logger = get_performance_logger()


@contextmanager
def log_database_operation(operation_name: str, session: Session = None):
    """
    Context manager to log database operations with timing.
    
    Args:
        operation_name: Name of the database operation
        session: SQLAlchemy session (optional)
    """
    start_time = time.time()
    db_logger.info(f"Starting database operation: {operation_name}")
    
    try:
        yield
        execution_time = time.time() - start_time
        db_logger.info(f"Completed database operation: {operation_name} in {execution_time:.4f}s")
        
        # Log slow operations to performance logger
        if execution_time > 0.5:  # Log operations taking more than 500ms
            perf_logger.warning(f"Slow database operation: {operation_name} took {execution_time:.4f}s")
        elif execution_time > 0.1:  # Log operations taking more than 100ms as info
            perf_logger.info(f"Database operation timing: {operation_name} took {execution_time:.4f}s")
            
    except Exception as e:
        execution_time = time.time() - start_time
        db_logger.error(f"Database operation failed: {operation_name} after {execution_time:.4f}s - Error: {str(e)}")
        raise


def log_query_execution(query_name: str, query_sql: str = None):
    """
    Log SQL query execution.
    
    Args:
        query_name: Name/description of the query
        query_sql: SQL query string (optional, for debugging)
    """
    if query_sql:
        db_logger.debug(f"Executing query '{query_name}': {query_sql}")
    else:
        db_logger.info(f"Executing query: {query_name}")


def log_transaction_start(operation: str):
    """Log the start of a database transaction."""
    db_logger.info(f"Starting transaction for: {operation}")


def log_transaction_commit(operation: str):
    """Log successful transaction commit."""
    db_logger.info(f"Transaction committed successfully for: {operation}")


def log_transaction_rollback(operation: str, error: str = None):
    """Log transaction rollback."""
    if error:
        db_logger.error(f"Transaction rolled back for: {operation} - Error: {error}")
    else:
        db_logger.warning(f"Transaction rolled back for: {operation}")


def log_connection_event(event_type: str, details: str = None):
    """
    Log database connection events.
    
    Args:
        event_type: Type of connection event (connect, disconnect, error, etc.)
        details: Additional details about the event
    """
    if details:
        db_logger.info(f"Database connection {event_type}: {details}")
    else:
        db_logger.info(f"Database connection {event_type}")


class DatabaseLoggingMixin:
    """
    Mixin class to add database logging capabilities to service classes.
    """
    
    def __init__(self):
        self.db_logger = get_database_logger()
        self.perf_logger = get_performance_logger()
    
    def log_db_operation(self, operation: str, details: str = None):
        """Log a database operation."""
        if details:
            self.db_logger.info(f"{operation}: {details}")
        else:
            self.db_logger.info(operation)
    
    def log_db_error(self, operation: str, error: str):
        """Log a database error."""
        self.db_logger.error(f"{operation} failed: {error}")
    
    def log_performance_warning(self, operation: str, duration: float):
        """Log a performance warning for slow operations."""
        self.perf_logger.warning(f"Slow operation: {operation} took {duration:.4f}s")

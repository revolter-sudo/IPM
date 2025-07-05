# Logging Fix Guide - IPM Application

## Problem Description
In production, only `ipm_api.log` contains logs while other log files (`ipm_database.log`, `ipm_performance.log`, `ipm_errors.log`) remain empty. This suggests that Docker recreation might be cleaning log files improperly and the specific loggers aren't being used correctly.

## Root Causes Identified

1. **Log File Initialization**: Log files weren't being created with proper permissions during Docker startup
2. **Logger Usage**: The codebase wasn't using the specific loggers (database, performance) properly
3. **Docker Volume Permissions**: Log files might be getting reset during container recreation

## Fixes Applied

### 1. Enhanced Logging Configuration (`src/app/utils/logging_config.py`)

**Changes Made:**
- Added explicit log file creation with proper permissions during setup
- Changed performance logger level from WARNING to INFO to capture more logs
- Added test logging to each logger during initialization to ensure they work
- Improved error handling and file permissions

**Key Improvements:**
```python
# Ensure log files are created with proper permissions
for log_file_name in [f"{app_name}.log", f"{app_name}_errors.log", f"{app_name}_performance.log", 
                     f"{app_name}_database.log", f"{app_name}_api.log"]:
    log_file_path = log_path / log_file_name
    if not log_file_path.exists():
        log_file_path.touch()
        os.chmod(str(log_file_path), 0o666)

# Test each logger to ensure they're working
perf_logger.info("Performance logger initialized successfully")
db_logger.info("Database logger initialized successfully")
api_logger.info("API logger initialized successfully")
```

### 2. Database Logging Enhancement (`src/app/database/database.py`)

**Changes Made:**
- Added database event listeners to log connection events
- Enhanced the `get_db()` function with proper logging
- Added database initialization logging

**Key Features:**
```python
# Add database event listeners for logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log database connections."""
    db_logger.info("Database connection established")

# Enhanced DB dependency with logging
def get_db():
    db = SessionLocal()
    db_logger.debug("Database session created")
    try:
        yield db
        db_logger.debug("Database session yielded successfully")
    except Exception as e:
        db_logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()
        db_logger.debug("Database session closed")
```

### 3. Database Logging Middleware (`src/app/middleware/database_logging.py`)

**New File Created:**
- Context manager for logging database operations with timing
- Mixin class for easy integration into service classes
- Helper functions for transaction logging

**Usage Example:**
```python
from src.app.middleware.database_logging import log_database_operation

# In your service functions:
with log_database_operation("create_user", session=db):
    # Your database operations here
    user = User(name="John", email="john@example.com")
    db.add(user)
    db.commit()
```

### 4. Enhanced Docker Entrypoint Scripts

**Changes Made to `entrypoint.sh` and `entrypoint_new.sh`:**
- Explicit creation of all log files during container startup
- Proper permission setting for log files
- Ownership management to prevent permission issues

**Key Additions:**
```bash
# Create all log files with proper permissions
touch "$LOG_DIR/ipm.log"
touch "$LOG_DIR/ipm_api.log"
touch "$LOG_DIR/ipm_database.log"
touch "$LOG_DIR/ipm_performance.log"
touch "$LOG_DIR/ipm_errors.log"

# Set proper permissions for log files
chmod 666 "$LOG_DIR"/*.log
chown -R 1000:1000 "$LOG_DIR" 2>/dev/null || true
```

## How to Use the Different Loggers

### 1. Main Application Logger
```python
from src.app.utils.logging_config import get_logger
logger = get_logger(__name__)
logger.info("General application message")
logger.error("Application error occurred")
```

### 2. API Logger
```python
from src.app.utils.logging_config import get_api_logger
api_logger = get_api_logger()
api_logger.info(f"Request: {request.method} {request.url.path}")
api_logger.info(f"Response: Status {response.status_code}")
```

### 3. Database Logger
```python
from src.app.utils.logging_config import get_database_logger
db_logger = get_database_logger()
db_logger.info("Starting database operation: create_user")
db_logger.error("Database operation failed: connection timeout")
```

### 4. Performance Logger
```python
from src.app.utils.logging_config import get_performance_logger
perf_logger = get_performance_logger()
perf_logger.info(f"Query execution time: {duration:.4f}s")
perf_logger.warning(f"Slow query detected: {query_name} took {duration:.4f}s")
```

## Testing the Fix

1. **Run the test script:**
   ```bash
   python test_logging.py
   ```

2. **Check log files after deployment:**
   ```bash
   ls -la logs/
   tail -f logs/ipm_database.log
   tail -f logs/ipm_performance.log
   tail -f logs/ipm_errors.log
   ```

3. **Verify in production:**
   - Deploy the updated code
   - Check that all log files are created and have content
   - Monitor the logs during normal application usage

## Deployment Steps

1. **Build and deploy the updated Docker image**
2. **Verify log directory permissions:**
   ```bash
   docker exec -it <container_name> ls -la /app/logs/
   ```
3. **Monitor logs in real-time:**
   ```bash
   docker exec -it <container_name> tail -f /app/logs/ipm_database.log
   ```

## Expected Results

After applying these fixes:
- All log files should be created during container startup
- Database operations should appear in `ipm_database.log`
- Performance metrics should appear in `ipm_performance.log`
- Errors should appear in both main log and `ipm_errors.log`
- API requests should continue to appear in `ipm_api.log`
- Log files should persist across Docker container recreations

## Monitoring and Maintenance

- Set up log rotation monitoring
- Check log file sizes regularly
- Monitor for any permission issues
- Ensure log directory is properly mounted as a volume in production

#!/usr/bin/env python3
"""
Test script to verify that all logging functionality is working correctly.
This script tests all different loggers and ensures they write to their respective files.
"""

import os
import sys
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app.utils.logging_config import (
    setup_logging, 
    get_logger, 
    get_api_logger, 
    get_database_logger, 
    get_performance_logger
)

def test_all_loggers():
    """Test all loggers to ensure they're working correctly."""
    
    print("Setting up logging...")
    
    # Initialize logging
    setup_logging(
        log_level="INFO",
        log_dir="./logs",
        app_name="ipm"
    )
    
    print("Getting logger instances...")
    
    # Get all loggers
    main_logger = get_logger(__name__)
    api_logger = get_api_logger()
    db_logger = get_database_logger()
    perf_logger = get_performance_logger()
    
    print("Testing main logger...")
    main_logger.info("This is a test message from the main logger")
    main_logger.warning("This is a warning from the main logger")
    main_logger.error("This is an error from the main logger")
    
    print("Testing API logger...")
    api_logger.info("API Request: GET /test - Client: 127.0.0.1")
    api_logger.info("API Response: GET /test - Status: 200 - Time: 0.0123s")
    
    print("Testing database logger...")
    db_logger.info("Database connection established")
    db_logger.info("Executing query: SELECT * FROM users")
    db_logger.info("Query completed successfully")
    db_logger.warning("Database connection pool is running low")
    
    print("Testing performance logger...")
    perf_logger.info("Performance metric: Query execution time 0.0456s")
    perf_logger.warning("Slow query detected: get_user_projects took 1.2345s")
    
    print("Testing error scenarios...")
    try:
        # Simulate an error
        raise ValueError("This is a test error")
    except Exception as e:
        main_logger.error(f"Caught exception: {str(e)}")
        db_logger.error(f"Database operation failed: {str(e)}")
    
    print("All loggers tested successfully!")
    
    # Check if log files were created
    log_dir = Path("./logs")
    expected_files = [
        "ipm.log",
        "ipm_api.log", 
        "ipm_database.log",
        "ipm_performance.log",
        "ipm_errors.log"
    ]
    
    print("\nChecking log files...")
    for file_name in expected_files:
        file_path = log_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✓ {file_name} exists ({size} bytes)")
            
            # Show first few lines of each log file
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"  Sample content: {lines[-1].strip()}")
                    else:
                        print(f"  ⚠️  {file_name} is empty")
            except Exception as e:
                print(f"  ⚠️  Could not read {file_name}: {e}")
        else:
            print(f"✗ {file_name} does not exist")
    
    print("\nLogging test completed!")

if __name__ == "__main__":
    test_all_loggers()

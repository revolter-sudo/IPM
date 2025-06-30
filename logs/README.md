# IPM Application Logs

This directory contains persistent log files for the IPM application. These logs are stored outside the Docker container to ensure they persist even when containers are stopped, removed, and recreated.

## Configuration

The logging system is configured through environment variables:

- **LOG_LEVEL**: Controls the minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO
- **LOG_DIR**: Directory where log files are stored. Default: /app/logs

These can be set in your `.env` file or docker-compose.yml environment section.

## Log Files

The application creates several log files with automatic rotation:

### Main Application Logs
- **ipm.log** - Main application log with all INFO and above messages
- **ipm_errors.log** - Error-specific log with ERROR and CRITICAL messages only
- **ipm_performance.log** - Performance-related logs including slow queries and operations
- **ipm_database.log** - Database operation logs
- **ipm_api.log** - API request/response logs

### Log Rotation
- Each log file has a maximum size of 10MB
- When a log file reaches the limit, it's rotated (e.g., ipm.log becomes ipm.log.1)
- Up to 5 backup files are kept for each log type
- Older backup files are automatically deleted

### Log Format
All logs use a consistent timestamp format:
```
YYYY-MM-DD HH:MM:SS - logger_name - LOG_LEVEL - message
```

Example:
```
2025-06-26 14:30:15 - src.app.main - INFO - IPM Application Starting
2025-06-26 14:30:16 - api - INFO - Request: GET /admin/docs - Client: 172.18.0.1
2025-06-26 14:30:16 - performance - WARNING - Slow query detected: get_user_projects took 1.2345s
```

## Directory Structure
```
logs/
├── README.md           # This file
├── ipm.log            # Main application log
├── ipm.log.1          # Rotated backup (most recent)
├── ipm.log.2          # Rotated backup
├── ...
├── ipm_errors.log     # Error-specific log
├── ipm_errors.log.1   # Error log backup
├── ...
├── ipm_performance.log # Performance log
├── ipm_api.log        # API request log
└── ipm_database.log   # Database operation log
```

## Monitoring Logs

### View Real-time Logs
```bash
# Main application log
tail -f logs/ipm.log

# Error logs only
tail -f logs/ipm_errors.log

# API requests
tail -f logs/ipm_api.log

# Performance issues
tail -f logs/ipm_performance.log
```

### Search Logs
```bash
# Search for specific errors
grep -i "error" logs/ipm.log

# Search for slow queries
grep "Slow query" logs/ipm_performance.log

# Search for specific API endpoints
grep "POST /auth/login" logs/ipm_api.log
```

### Log Analysis
```bash
# Count error occurrences
grep -c "ERROR" logs/ipm_errors.log

# Find most recent errors
tail -20 logs/ipm_errors.log

# Check application startup
grep "Application Starting" logs/ipm.log
```

## Troubleshooting

### Common Issues

1. **Permission Issues**
   - Ensure the logs directory is writable by the Docker container
   - Check file permissions: `ls -la logs/`

2. **Disk Space**
   - Monitor disk usage: `du -sh logs/`
   - Log rotation should prevent excessive disk usage

3. **Missing Logs**
   - Check if the logging configuration is properly initialized
   - Verify Docker volume mounting in docker-compose.yml

### Log Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about application flow
- **WARNING**: Something unexpected happened but the application continues
- **ERROR**: A serious problem occurred
- **CRITICAL**: A very serious error occurred

## Maintenance

### Manual Log Cleanup
If needed, you can manually clean up old logs:
```bash
# Remove logs older than 30 days
find logs/ -name "*.log.*" -mtime +30 -delete

# Compress old logs
gzip logs/*.log.[2-9]
```

### Backup Important Logs
For critical deployments, consider backing up error logs:
```bash
# Create daily backup of error logs
cp logs/ipm_errors.log logs/backups/ipm_errors_$(date +%Y%m%d).log
```

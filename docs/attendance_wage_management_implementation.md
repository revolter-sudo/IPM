# Attendance and Wage Management Module - Implementation Guide

## Overview

This document provides a comprehensive guide to the newly implemented Attendance and Wage Management module for the IPM (Infrastructure Project Management) system. The module follows clean code principles, includes comprehensive testing, and implements role-based access control.

## 🚀 Features Implemented

### Self Attendance Management
- **Punch In/Out**: Users can mark their daily attendance with location coordinates
- **Location Validation**: GPS coordinates are validated for accuracy and proximity
- **Automatic Project Assignment**: Tracks which projects user was assigned to at punch-in time
- **Current Day Restriction**: Attendance can only be marked for the current day
- **Flexible Punch Out**: Users can punch in next day even if they forgot to punch out previous day

### Project Attendance Management
- **Labour Attendance**: Site engineers can mark attendance for labours working on projects
- **Sub-contractor Tracking**: Links attendance to specific sub-contractors
- **Location Recording**: Records GPS coordinates where attendance was marked
- **Role-based Access**: Only authorized roles can mark project attendance
- **Automatic Wage Calculation**: Calculates wages automatically when attendance is marked

### Wage Management
- **Daily Wage Configuration**: Configure daily wage rates for projects with effective dates
- **Historical Tracking**: Maintains complete history of wage rate changes
- **Automatic Calculation**: Calculates total wages (no_of_labours × daily_wage_rate)
- **Date-effective Rates**: Uses the correct wage rate based on attendance date
- **Role-based Configuration**: Only Admin/Project Manager/Super Admin can configure rates

## 📁 File Structure

```
src/app/
├── database/
│   └── models.py                    # Updated with new attendance/wage models
├── schemas/
│   ├── attendance_schemas.py        # Pydantic schemas for attendance APIs
│   └── wage_schemas.py             # Pydantic schemas for wage management APIs
├── services/
│   ├── attendance_service.py        # Core attendance business logic
│   ├── attendance_endpoints.py      # FastAPI routes for attendance
│   ├── wage_service.py             # Core wage management logic
│   ├── wage_endpoints.py           # FastAPI routes for wage management
│   └── location_service.py         # Enhanced with coordinate validation
├── tests/
│   ├── conftest.py                 # Test configuration and fixtures
│   ├── test_attendance_models.py   # Model tests
│   ├── test_attendance_service.py  # Service logic tests
│   ├── test_attendance_endpoints.py # API endpoint tests
│   ├── test_wage_service.py        # Wage service tests
│   └── run_tests.py               # Test runner script
└── main.py                        # Updated with new routers

alembic/versions/
├── 20250628_create_attendance_and_wage_management_tables.py
└── 20250628_add_attendance_indexes.py
```

## 🗄️ Database Schema

### New Tables Added

#### `self_attendance`
- Tracks individual user attendance with punch in/out times
- Stores GPS coordinates for both punch in and punch out
- Maintains assigned projects at time of punch in
- Unique constraint: user_id + attendance_date + is_deleted

#### `project_attendance`
- Records labour attendance for specific projects
- Links site engineer, project, and sub-contractor
- Stores number of labours and location coordinates
- Check constraint: no_of_labours > 0

#### `project_daily_wage`
- Configures daily wage rates for projects
- Date-effective wage rates with history tracking
- Unique constraint: project_id + effective_date + is_deleted
- Check constraint: daily_wage_rate > 0

#### `project_attendance_wage`
- Automatic wage calculations for project attendance
- Links attendance record to wage configuration
- Stores calculated total amount
- Unique constraint: project_attendance_id + is_deleted

## 🔧 API Endpoints

### Self Attendance Endpoints

#### POST `/attendance/self/punch-in`
```json
{
  "phone": 9876543210,
  "password": "userpassword",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "location_address": "Optional address"
}
```

#### POST `/attendance/self/punch-out`
```json
{
  "phone": 9876543210,
  "password": "userpassword",
  "latitude": 28.6140,
  "longitude": 77.2091,
  "location_address": "Optional address"
}
```

#### GET `/attendance/self/status`
Returns current attendance status for today.

#### GET `/attendance/self/history`
Query parameters: `start_date`, `end_date`, `page`, `limit`

### Project Attendance Endpoints

#### POST `/attendance/project`
```json
{
  "project_id": "uuid",
  "sub_contractor_id": "uuid",
  "no_of_labours": 15,
  "latitude": 28.6139,
  "longitude": 77.2090,
  "location_address": "Project site",
  "notes": "Optional notes"
}
```

#### GET `/attendance/project/history`
Query parameters: `project_id`, `start_date`, `end_date`, `page`, `limit`

### Wage Management Endpoints

#### POST `/wage/projects/{project_id}/daily-wage`
```json
{
  "daily_wage_rate": 350.0,
  "effective_date": "2025-06-28"
}
```

#### GET `/wage/projects/{project_id}/daily-wage`
Returns current active wage rate for project.

#### GET `/wage/projects/{project_id}/daily-wage/history`
Query parameters: `page`, `limit`

## 🔐 Authentication & Authorization

### Role-based Access Control

- **Self Attendance**: All authenticated users
- **Project Attendance**: Site Engineer, Project Manager, Admin, Super Admin
- **Wage Configuration**: Admin, Project Manager, Super Admin

### Security Features

- Phone/password authentication for attendance marking
- JWT token validation for API access
- Location coordinate validation
- Input sanitization and validation

## 🧪 Testing

### Test Coverage

The module includes comprehensive tests covering:

- **Model Tests**: Database model validation and constraints
- **Service Tests**: Business logic and helper functions
- **Endpoint Tests**: API functionality and error handling
- **Integration Tests**: End-to-end workflows

### Running Tests

```bash
# Run all tests
python src/app/tests/run_tests.py

# Run with coverage
python src/app/tests/run_tests.py coverage

# Run specific tests
python src/app/tests/run_tests.py specific "attendance"

# Run linting
python src/app/tests/run_tests.py lint
```

## 📊 Key Features

### Location Validation
- GPS coordinate validation (-90 to 90 latitude, -180 to 180 longitude)
- Coordinate precision detection (high/medium/low)
- Distance calculation between coordinates
- Proximity validation for project sites
- India boundary validation

### Automatic Wage Calculation
- Real-time wage calculation when attendance is marked
- Uses date-effective wage rates
- Handles multiple wage rate changes
- Maintains calculation history

### Data Integrity
- Unique constraints prevent duplicate records
- Check constraints ensure data validity
- Soft delete pattern for data retention
- Comprehensive logging for audit trails

## 🚀 Deployment

### Database Migration

```bash
# Run migrations to create new tables
alembic upgrade head
```

### Environment Variables

No new environment variables required. Uses existing database and authentication configuration.

## 📈 Performance Considerations

### Database Indexes
- Optimized indexes for common query patterns
- Composite indexes for date-range queries
- Foreign key indexes for relationship queries

### Caching
- Leverages existing Redis caching infrastructure
- Cacheable wage rate lookups
- Optimized query patterns

## 🔍 Monitoring & Logging

### Logging
- Comprehensive logging for all operations
- Performance monitoring for slow requests
- Error tracking and debugging information
- Audit trails for wage configurations

### Health Checks
- Database connectivity validation
- Service availability monitoring
- Performance metrics tracking

## 🛠️ Maintenance

### Regular Tasks
- Monitor attendance patterns
- Review wage calculation accuracy
- Validate location data quality
- Archive old attendance records

### Troubleshooting
- Check logs for authentication issues
- Validate GPS coordinate accuracy
- Monitor wage calculation consistency
- Review role-based access permissions

## 📝 Code Quality

### Standards Followed
- Clean code principles
- SOLID design patterns
- Comprehensive error handling
- Input validation and sanitization
- Type hints and documentation
- Consistent naming conventions

### Linting & Formatting
- Flake8 for code quality
- Black for code formatting
- Pylance for type checking
- 120 character line limit

This implementation provides a robust, scalable, and maintainable attendance and wage management system that integrates seamlessly with the existing IPM infrastructure.

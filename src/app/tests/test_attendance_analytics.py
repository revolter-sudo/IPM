"""
Test cases for attendance analytics endpoints
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID
from src.app.services.attendance_endpoints import get_user_attendance_analytics, get_admin_attendance_analytics
from src.app.database.models import User, SelfAttendance
from src.app.schemas.auth_service_schamas import UserRole
from src.app.utils.attendance_utils import (
    get_current_month_working_days,
    calculate_attendance_percentage,
    get_attendance_feedback,
    parse_month_year,
    get_month_date_range,
    get_working_days_in_month
)


class TestAttendanceUtils:
    """Test cases for attendance utility functions"""
    
    def test_get_working_days_in_month(self):
        """Test working days calculation for a month (6-day work week, only Sundays off)"""
        # January 2024 has 27 working days (31 days - 4 Sundays: 7th, 14th, 21st, 28th)
        working_days = get_working_days_in_month(2024, 1)
        assert working_days == 27

        # February 2024 has 25 working days (29 days - 4 Sundays: 4th, 11th, 18th, 25th)
        working_days = get_working_days_in_month(2024, 2)
        assert working_days == 25
    
    def test_calculate_attendance_percentage(self):
        """Test attendance percentage calculation"""
        # 100% attendance
        percentage = calculate_attendance_percentage(20, 20)
        assert percentage == 100.0
        
        # 50% attendance
        percentage = calculate_attendance_percentage(10, 20)
        assert percentage == 50.0
        
        # 0% attendance
        percentage = calculate_attendance_percentage(0, 20)
        assert percentage == 0.0
        
        # Edge case: no working days
        percentage = calculate_attendance_percentage(0, 0)
        assert percentage == 0.0
    
    def test_get_attendance_feedback(self):
        """Test attendance feedback messages"""
        assert get_attendance_feedback(95) == "Excellent Attendance Record"
        assert get_attendance_feedback(85) == "Good Attendance Record"
        assert get_attendance_feedback(65) == "Average Attendance Record"
        assert get_attendance_feedback(30) == "Poor Attendance Record"
    
    def test_parse_month_year_valid(self):
        """Test valid month year parsing"""
        month, year = parse_month_year("12-2024")
        assert month == 12
        assert year == 2024
        
        month, year = parse_month_year("01-2023")
        assert month == 1
        assert year == 2023
    
    def test_parse_month_year_invalid(self):
        """Test invalid month year parsing"""
        with pytest.raises(ValueError):
            parse_month_year("13-2024")  # Invalid month
        
        with pytest.raises(ValueError):
            parse_month_year("00-2024")  # Invalid month
        
        with pytest.raises(ValueError):
            parse_month_year("12-2019")  # Year too old
        
        with pytest.raises(ValueError):
            parse_month_year("12-2031")  # Year too new
        
        with pytest.raises(ValueError):
            parse_month_year("12/2024")  # Wrong separator
        
        with pytest.raises(ValueError):
            parse_month_year("2024-12")  # Wrong order
        
        with pytest.raises(ValueError):
            parse_month_year("")  # Empty string
    
    def test_get_month_date_range(self):
        """Test month date range calculation"""
        start_date, end_date = get_month_date_range(2024, 1)
        assert start_date == date(2024, 1, 1)
        assert end_date == date(2024, 1, 31)
        
        start_date, end_date = get_month_date_range(2024, 2)
        assert start_date == date(2024, 2, 1)
        assert end_date == date(2024, 2, 29)  # 2024 is a leap year


class TestUserAttendanceAnalytics:
    """Test cases for user attendance analytics endpoint"""
    
    @patch('src.app.services.attendance_endpoints.get_current_month_working_days')
    @patch('src.app.services.attendance_endpoints.get_month_date_range')
    def test_user_analytics_success(self, mock_date_range, mock_working_days):
        """Test successful user analytics retrieval"""
        # Mock dependencies (using 6-day work week)
        mock_working_days.return_value = 26  # 6-day work week for a typical month
        mock_date_range.return_value = (date(2024, 1, 1), date(2024, 1, 31))

        # Mock database and user
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.uuid = uuid4()

        # Mock query result
        mock_query = MagicMock()
        mock_query.count.return_value = 24  # 24 present days out of 26
        mock_db.query.return_value.filter.return_value = mock_query

        # Call the function
        result = get_user_attendance_analytics(db=mock_db, current_user=mock_user)

        # Verify result (24/26 = 92.31% -> 92%)
        assert result['status_code'] == 200
        assert result['message'] == "Attendance Analytics Fetched Successfully."
        assert result['data']['current_month']['percentage'] == 92
        assert result['data']['current_month']['feedback'] == "Excellent Attendance Record"
    
    def test_user_analytics_invalid_user(self):
        """Test user analytics with invalid user"""
        mock_db = MagicMock()
        mock_user = None
        
        result = get_user_attendance_analytics(db=mock_db, current_user=mock_user)
        
        assert result['status_code'] == 401
        assert "Invalid user session" in result['message']
    
    @patch('src.app.services.attendance_endpoints.get_current_month_working_days')
    def test_user_analytics_no_working_days(self, mock_working_days):
        """Test user analytics when no working days in month"""
        mock_working_days.return_value = 0
        
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.uuid = uuid4()
        
        result = get_user_attendance_analytics(db=mock_db, current_user=mock_user)
        
        assert result['status_code'] == 400
        assert "No working days found" in result['message']


class TestAdminAttendanceAnalytics:
    """Test cases for admin attendance analytics endpoint"""
    
    @patch('src.app.services.attendance_endpoints.parse_month_year')
    @patch('src.app.services.attendance_endpoints.get_working_days_in_month')
    @patch('src.app.services.attendance_endpoints.get_month_date_range')
    def test_admin_analytics_success(self, mock_date_range, mock_working_days, mock_parse):
        """Test successful admin analytics retrieval"""
        # Mock dependencies (using 6-day work week)
        mock_parse.return_value = (12, 2024)
        mock_working_days.return_value = 26  # 6-day work week for December
        mock_date_range.return_value = (date(2024, 12, 1), date(2024, 12, 31))

        # Mock database and users
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN
        mock_admin_user.uuid = uuid4()

        target_user_id = uuid4()
        mock_target_user = MagicMock()
        mock_target_user.uuid = target_user_id

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_target_user
        mock_query = MagicMock()
        mock_query.count.return_value = 24  # 24 present days out of 26
        mock_db.query.return_value.filter.return_value = mock_query

        # Call the function
        result = get_admin_attendance_analytics(
            month="12-2024",
            user_id=target_user_id,
            db=mock_db,
            current_user=mock_admin_user
        )

        # Verify result (24/26 = 92.31% -> 92%)
        assert result['status_code'] == 200
        assert result['message'] == "Attendance Analytics Fetched Successfully."
        assert result['data']['current_month']['percentage'] == 92
        assert result['data']['current_month']['feedback'] == "Excellent Attendance Record"
    
    def test_admin_analytics_unauthorized(self):
        """Test admin analytics with unauthorized user"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.role = UserRole.SITE_ENGINEER  # Not admin
        mock_user.uuid = uuid4()
        
        result = get_admin_attendance_analytics(
            month="12-2024",
            user_id=uuid4(),
            db=mock_db,
            current_user=mock_user
        )
        
        assert result['status_code'] == 403
        assert "Access denied" in result['message']
    
    def test_admin_analytics_invalid_month(self):
        """Test admin analytics with invalid month format"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN
        mock_admin_user.uuid = uuid4()

        result = get_admin_attendance_analytics(
            month="invalid-month",
            user_id=uuid4(),
            db=mock_db,
            current_user=mock_admin_user
        )

        assert result['status_code'] == 400
        # The error message should contain information about invalid format
        assert "Month part must be 2 digits" in result['message'] or "Invalid month format" in result['message']
    
    def test_admin_analytics_user_not_found(self):
        """Test admin analytics with non-existent user"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN
        mock_admin_user.uuid = uuid4()
        
        # Mock user not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch('src.app.services.attendance_endpoints.parse_month_year') as mock_parse:
            mock_parse.return_value = (12, 2024)
            
            result = get_admin_attendance_analytics(
                month="12-2024",
                user_id=uuid4(),
                db=mock_db,
                current_user=mock_admin_user
            )
        
        assert result['status_code'] == 404
        assert "User not found" in result['message']
    
    def test_admin_analytics_empty_parameters(self):
        """Test admin analytics with empty parameters"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN
        mock_admin_user.uuid = uuid4()
        
        # Test empty month
        result = get_admin_attendance_analytics(
            month="",
            user_id=uuid4(),
            db=mock_db,
            current_user=mock_admin_user
        )
        
        assert result['status_code'] == 400
        assert "Month parameter is required" in result['message']


class TestAttendanceAnalyticsIntegration:
    """Integration test cases for attendance analytics"""

    def test_percentage_calculation_edge_cases(self):
        """Test percentage calculation with edge cases"""
        # Test with very small numbers
        percentage = calculate_attendance_percentage(1, 1)
        assert percentage == 100.0

        # Test with large numbers
        percentage = calculate_attendance_percentage(999, 1000)
        assert percentage == 99.9

        # Test rounding
        percentage = calculate_attendance_percentage(1, 3)
        assert percentage == 33.33

    def test_feedback_boundary_conditions(self):
        """Test feedback messages at boundary conditions"""
        assert get_attendance_feedback(90.0) == "Excellent Attendance Record"
        assert get_attendance_feedback(89.9) == "Good Attendance Record"
        assert get_attendance_feedback(70.0) == "Good Attendance Record"
        assert get_attendance_feedback(69.9) == "Average Attendance Record"
        assert get_attendance_feedback(50.0) == "Average Attendance Record"
        assert get_attendance_feedback(49.9) == "Poor Attendance Record"
        assert get_attendance_feedback(0.0) == "Poor Attendance Record"

    @patch('src.app.services.attendance_endpoints.get_current_month_working_days')
    @patch('src.app.services.attendance_endpoints.get_month_date_range')
    def test_database_error_handling(self, mock_date_range, mock_working_days):
        """Test database error handling in user analytics"""
        mock_working_days.return_value = 26  # 6-day work week
        mock_date_range.return_value = (date(2024, 1, 1), date(2024, 1, 31))

        # Mock database error
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database connection error")

        mock_user = MagicMock()
        mock_user.uuid = uuid4()

        result = get_user_attendance_analytics(db=mock_db, current_user=mock_user)

        assert result['status_code'] == 500
        assert "Error retrieving attendance data" in result['message']

    def test_month_parsing_comprehensive(self):
        """Comprehensive test for month parsing edge cases"""
        # Test various invalid formats
        invalid_formats = [
            "1-2024",      # Single digit month
            "12-24",       # Two digit year
            "12-2024-01",  # Extra parts
            "12 2024",     # Space separator
            "12.2024",     # Dot separator
            "2024-12",     # Reversed order
            "abc-2024",    # Non-numeric month
            "12-abcd",     # Non-numeric year
        ]

        for invalid_format in invalid_formats:
            with pytest.raises(ValueError):
                parse_month_year(invalid_format)

    def test_working_days_calculation_edge_cases(self):
        """Test working days calculation for edge cases (6-day work week)"""
        # Test February in leap year vs non-leap year
        leap_year_feb = get_working_days_in_month(2024, 2)  # 2024 is leap year
        non_leap_year_feb = get_working_days_in_month(2023, 2)  # 2023 is not leap year

        assert leap_year_feb == 25  # 29 days - 4 Sundays
        assert non_leap_year_feb == 24  # 28 days - 4 Sundays

        # Test months with different numbers of days
        january = get_working_days_in_month(2024, 1)  # 31 days
        april = get_working_days_in_month(2024, 4)    # 30 days

        assert january == 27  # 31 days - 4 Sundays
        assert april == 26   # 30 days - 4 Sundays

    @patch('src.app.services.attendance_endpoints.parse_month_year')
    @patch('src.app.services.attendance_endpoints.get_working_days_in_month')
    def test_admin_analytics_zero_working_days(self, mock_working_days, mock_parse):
        """Test admin analytics when month has zero working days"""
        mock_parse.return_value = (12, 2024)
        mock_working_days.return_value = 0

        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.SUPER_ADMIN
        mock_admin_user.uuid = uuid4()

        mock_target_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_target_user

        result = get_admin_attendance_analytics(
            month="12-2024",
            user_id=uuid4(),
            db=mock_db,
            current_user=mock_admin_user
        )

        assert result['status_code'] == 400
        assert "No working days found" in result['message']

    def test_super_admin_access(self):
        """Test that super admin has access to admin analytics"""
        mock_db = MagicMock()
        mock_super_admin = MagicMock()
        mock_super_admin.role = UserRole.SUPER_ADMIN
        mock_super_admin.uuid = uuid4()

        # Mock target user found
        mock_target_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_target_user

        with patch('src.app.services.attendance_endpoints.parse_month_year') as mock_parse:
            mock_parse.return_value = (12, 2024)
            with patch('src.app.services.attendance_endpoints.get_working_days_in_month') as mock_working_days:
                mock_working_days.return_value = 26  # 6-day work week
                with patch('src.app.services.attendance_endpoints.get_month_date_range') as mock_date_range:
                    mock_date_range.return_value = (date(2024, 12, 1), date(2024, 12, 31))

                    # Mock attendance query
                    mock_query = MagicMock()
                    mock_query.count.return_value = 24  # 24 present days out of 26
                    mock_db.query.return_value.filter.return_value = mock_query

                    result = get_admin_attendance_analytics(
                        month="12-2024",
                        user_id=uuid4(),
                        db=mock_db,
                        current_user=mock_super_admin
                    )

        # Should succeed for super admin
        assert result['status_code'] == 200

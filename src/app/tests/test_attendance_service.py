"""
Test cases for attendance service functions
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from src.app.services.attendance_service import (
    validate_coordinates,
    get_user_assigned_projects,
    authenticate_user_credentials,
    calculate_hours_worked,
    get_current_hours_worked
)
from src.app.services.location_service import LocationService


class TestAttendanceServiceHelpers:
    """Test helper functions in attendance service"""
    
    def test_validate_coordinates_valid(self):
        """Test coordinate validation with valid coordinates"""
        assert validate_coordinates(28.6139, 77.2090) is True
        assert validate_coordinates(0.0, 0.0) is True
        assert validate_coordinates(-90.0, -180.0) is True
        assert validate_coordinates(90.0, 180.0) is True
    
    def test_validate_coordinates_invalid(self):
        """Test coordinate validation with invalid coordinates"""
        assert validate_coordinates(91.0, 77.2090) is False  # Invalid latitude
        assert validate_coordinates(28.6139, 181.0) is False  # Invalid longitude
        assert validate_coordinates(-91.0, 77.2090) is False  # Invalid latitude
        assert validate_coordinates(28.6139, -181.0) is False  # Invalid longitude
    
    def test_get_user_assigned_projects(self, db_session, test_user, test_project, test_project_user_map):
        """Test getting user assigned projects"""
        projects = get_user_assigned_projects(test_user.uuid, db_session)
        
        assert len(projects) == 1
        assert projects[0]["uuid"] == str(test_project.uuid)
        assert projects[0]["name"] == test_project.name
    
    def test_get_user_assigned_projects_no_projects(self, db_session, test_user):
        """Test getting user assigned projects when user has no projects"""
        projects = get_user_assigned_projects(test_user.uuid, db_session)
        
        assert len(projects) == 0
    
    def test_authenticate_user_credentials_valid(self, db_session, test_user):
        """Test user authentication with valid credentials"""
        authenticated_user = authenticate_user_credentials(
            test_user.phone, 
            "testpassword", 
            db_session
        )
        
        assert authenticated_user is not None
        assert authenticated_user.uuid == test_user.uuid
        assert authenticated_user.phone == test_user.phone
    
    def test_authenticate_user_credentials_invalid_phone(self, db_session):
        """Test user authentication with invalid phone"""
        authenticated_user = authenticate_user_credentials(
            1234567890,  # Non-existent phone
            "testpassword", 
            db_session
        )
        
        assert authenticated_user is None
    
    def test_authenticate_user_credentials_invalid_password(self, db_session, test_user):
        """Test user authentication with invalid password"""
        authenticated_user = authenticate_user_credentials(
            test_user.phone, 
            "wrongpassword", 
            db_session
        )
        
        assert authenticated_user is None
    
    def test_calculate_hours_worked(self):
        """Test hours calculation between punch in and punch out"""
        punch_in = datetime(2023, 1, 1, 9, 0, 0)
        punch_out = datetime(2023, 1, 1, 17, 30, 0)
        
        hours = calculate_hours_worked(punch_in, punch_out)
        
        assert hours == "8.5"
    
    def test_calculate_hours_worked_no_punch_out(self):
        """Test hours calculation when punch out is None"""
        punch_in = datetime(2023, 1, 1, 9, 0, 0)
        
        hours = calculate_hours_worked(punch_in, None)
        
        assert hours is None
    
    @patch('src.app.services.attendance_service.datetime')
    def test_get_current_hours_worked(self, mock_datetime):
        """Test current hours calculation"""
        # Mock current time
        mock_now = datetime(2023, 1, 1, 15, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        punch_in = datetime(2023, 1, 1, 9, 0, 0)
        
        hours = get_current_hours_worked(punch_in)
        
        assert hours == "6.0"


class TestLocationServiceIntegration:
    """Test location service integration"""
    
    def test_validate_coordinates_integration(self):
        """Test coordinate validation using LocationService"""
        # Valid coordinates
        assert LocationService.validate_coordinates(28.6139, 77.2090) is True
        
        # Invalid coordinates
        assert LocationService.validate_coordinates(91.0, 77.2090) is False
        assert LocationService.validate_coordinates(28.6139, 181.0) is False
    
    def test_get_coordinate_precision(self):
        """Test coordinate precision detection"""
        # High precision (6+ decimal places)
        precision = LocationService.get_coordinate_precision(28.613912, 77.209021)
        assert precision == "high"
        
        # Medium precision (4-5 decimal places)
        precision = LocationService.get_coordinate_precision(28.6139, 77.2090)
        assert precision == "medium"
        
        # Low precision (0-3 decimal places)
        precision = LocationService.get_coordinate_precision(28.61, 77.21)
        assert precision == "low"
    
    def test_calculate_distance(self):
        """Test distance calculation between coordinates"""
        # Distance between Delhi and Mumbai (approximately 1150 km)
        delhi_lat, delhi_lon = 28.6139, 77.2090
        mumbai_lat, mumbai_lon = 19.0760, 72.8777
        
        distance = LocationService.calculate_distance(
            delhi_lat, delhi_lon, mumbai_lat, mumbai_lon
        )
        
        # Should be approximately 1150 km (allow some tolerance)
        assert 1100 <= distance <= 1200
    
    def test_is_within_radius(self):
        """Test radius check functionality"""
        center_lat, center_lon = 28.6139, 77.2090
        
        # Point within 1 km
        nearby_lat, nearby_lon = 28.6149, 77.2100
        assert LocationService.is_within_radius(
            center_lat, center_lon, nearby_lat, nearby_lon, 1.0
        ) is True
        
        # Point outside 1 km
        far_lat, far_lon = 28.7139, 77.3090
        assert LocationService.is_within_radius(
            center_lat, center_lon, far_lat, far_lon, 1.0
        ) is False
    
    def test_validate_location_for_attendance(self):
        """Test comprehensive location validation for attendance"""
        # Valid location
        result = LocationService.validate_location_for_attendance(28.6139, 77.2090)
        
        assert result["is_valid"] is True
        assert result["precision"] in ["high", "medium", "low"]
        assert isinstance(result["warnings"], list)
        assert isinstance(result["errors"], list)
    
    def test_validate_location_for_attendance_invalid(self):
        """Test location validation with invalid coordinates"""
        result = LocationService.validate_location_for_attendance(91.0, 181.0)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert "Invalid coordinates provided" in result["errors"]
    
    def test_validate_location_for_attendance_with_project_location(self):
        """Test location validation with project location proximity check"""
        project_location = {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "max_distance_km": 1.0
        }
        
        # Location within project radius
        result = LocationService.validate_location_for_attendance(
            28.6149, 77.2100, project_location
        )
        
        assert result["is_valid"] is True
        
        # Location outside project radius
        result = LocationService.validate_location_for_attendance(
            28.7139, 77.3090, project_location
        )
        
        assert result["is_valid"] is True  # Still valid coordinates
        assert any("more than" in warning for warning in result["warnings"])
    
    def test_get_location_info(self):
        """Test getting location information"""
        # Delhi coordinates
        info = LocationService.get_location_info(28.6139, 77.2090)
        
        assert info["latitude"] == 28.6139
        assert info["longitude"] == 77.2090
        assert info["is_valid"] is True
        assert info["precision"] in ["high", "medium", "low"]
        assert info["estimated_state"] == "Delhi"
        assert info["estimated_city"] == "New Delhi"
    
    def test_get_location_info_mumbai(self):
        """Test getting location information for Mumbai"""
        # Mumbai coordinates
        info = LocationService.get_location_info(19.0760, 72.8777)
        
        assert info["latitude"] == 19.0760
        assert info["longitude"] == 72.8777
        assert info["is_valid"] is True
        assert info["estimated_state"] == "Maharashtra"
        assert info["estimated_city"] == "Mumbai"
    
    def test_get_location_info_bangalore(self):
        """Test getting location information for Bangalore"""
        # Bangalore coordinates
        info = LocationService.get_location_info(12.9716, 77.5946)
        
        assert info["latitude"] == 12.9716
        assert info["longitude"] == 77.5946
        assert info["is_valid"] is True
        assert info["estimated_state"] == "Karnataka"
        assert info["estimated_city"] == "Bengaluru"
    
    def test_get_location_info_invalid(self):
        """Test getting location information for invalid coordinates"""
        info = LocationService.get_location_info(91.0, 181.0)
        
        assert info["is_valid"] is False
        assert info["estimated_state"] is None
        assert info["estimated_city"] is None

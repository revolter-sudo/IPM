"""
Test cases for attendance endpoints
"""

import pytest
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch
from src.app.database.models import SelfAttendance, ProjectAttendance


class TestSelfAttendanceEndpoints:
    """Test self attendance endpoints"""
    
    def test_punch_in_success(self, client, auth_headers, sample_attendance_data, test_user, test_project_user_map):
        """Test successful punch in"""
        response = client.post(
            "/attendance/self/punch-in",
            json=sample_attendance_data["punch_in"],
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Punch in successful"
        assert data["data"]["attendance_date"] == str(date.today())
        assert data["data"]["punch_in_location"]["latitude"] == 28.6139
        assert data["data"]["punch_in_location"]["longitude"] == 77.2090
    
    def test_punch_in_invalid_credentials(self, client, auth_headers):
        """Test punch in with invalid credentials"""
        invalid_data = {
            "phone": 9876543210,
            "password": "wrongpassword",
            "latitude": 28.6139,
            "longitude": 77.2090
        }
        
        response = client.post(
            "/attendance/self/punch-in",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["message"] == "Invalid phone number or password"
    
    def test_punch_in_invalid_coordinates(self, client, auth_headers, sample_attendance_data):
        """Test punch in with invalid coordinates"""
        invalid_data = sample_attendance_data["punch_in"].copy()
        invalid_data["latitude"] = 91.0  # Invalid latitude
        
        response = client.post(
            "/attendance/self/punch-in",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Invalid coordinates provided"
    
    def test_punch_in_duplicate(self, client, auth_headers, sample_attendance_data, test_self_attendance):
        """Test punch in when already punched in today"""
        response = client.post(
            "/attendance/self/punch-in",
            json=sample_attendance_data["punch_in"],
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Attendance already marked for today"
    
    def test_punch_out_success(self, client, auth_headers, sample_attendance_data, test_self_attendance):
        """Test successful punch out"""
        response = client.post(
            "/attendance/self/punch-out",
            json=sample_attendance_data["punch_out"],
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Punch out successful"
        assert data["data"]["punch_out_time"] is not None
        assert data["data"]["total_hours"] is not None
    
    def test_punch_out_no_punch_in(self, client, auth_headers, sample_attendance_data):
        """Test punch out without punch in"""
        response = client.post(
            "/attendance/self/punch-out",
            json=sample_attendance_data["punch_out"],
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "No punch in record found for today"
    
    def test_get_attendance_status_not_punched_in(self, client, auth_headers):
        """Test getting attendance status when not punched in"""
        response = client.get(
            "/attendance/self/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_punched_in"] is False
    
    def test_get_attendance_status_punched_in(self, client, auth_headers, test_self_attendance):
        """Test getting attendance status when punched in"""
        response = client.get(
            "/attendance/self/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_punched_in"] is True
        assert data["data"]["punch_in_time"] is not None
        assert data["data"]["current_hours"] is not None
    
    def test_get_attendance_history(self, client, auth_headers, test_self_attendance):
        """Test getting attendance history"""
        response = client.get(
            "/attendance/self/history?page=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_count"] >= 1
        assert len(data["data"]["attendances"]) >= 1
        assert data["data"]["page"] == 1
        assert data["data"]["limit"] == 10
    
    def test_get_attendance_history_with_date_filter(self, client, auth_headers, test_self_attendance):
        """Test getting attendance history with date filters"""
        today = date.today()
        response = client.get(
            f"/attendance/self/history?start_date={today}&end_date={today}&page=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_count"] >= 1


class TestProjectAttendanceEndpoints:
    """Test project attendance endpoints"""
    
    def test_mark_project_attendance_success(self, client, auth_headers, sample_project_attendance_data, 
                                           test_project_user_map, test_daily_wage):
        """Test successful project attendance marking"""
        response = client.post(
            "/attendance/project",
            json=sample_project_attendance_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Project attendance marked successfully with wage calculation"
        assert data["data"]["no_of_labours"] == 15
        assert data["data"]["project"]["name"] == "Test Project"
        assert data["data"]["sub_contractor"]["name"] == "Test Contractor"
        assert data["data"]["wage_calculation"] is not None
    
    def test_mark_project_attendance_unauthorized_role(self, client, sample_project_attendance_data):
        """Test project attendance marking with unauthorized role"""
        # Create a user with unauthorized role
        from src.app.services.auth_service import create_access_token
        from src.app.database.models import User
        from uuid import uuid4
        
        unauthorized_user = User(
            uuid=uuid4(),
            name="Unauthorized User",
            phone=9876543213,
            role="Client",  # Not authorized for attendance marking
            is_deleted=False,
            is_active=True
        )
        
        token = create_access_token(data={"sub": str(unauthorized_user.uuid)})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/attendance/project",
            json=sample_project_attendance_data,
            headers=headers
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["message"] == "Not authorized to mark project attendance"
    
    def test_mark_project_attendance_invalid_coordinates(self, client, auth_headers, sample_project_attendance_data):
        """Test project attendance marking with invalid coordinates"""
        invalid_data = sample_project_attendance_data.copy()
        invalid_data["latitude"] = 91.0  # Invalid latitude
        
        response = client.post(
            "/attendance/project",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["message"] == "Invalid coordinates provided"
    
    def test_mark_project_attendance_not_assigned(self, client, auth_headers, sample_project_attendance_data):
        """Test project attendance marking when user not assigned to project"""
        # Remove project assignment by not including test_project_user_map fixture
        response = client.post(
            "/attendance/project",
            json=sample_project_attendance_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["message"] == "Not assigned to this project"
    
    def test_mark_project_attendance_invalid_project(self, client, auth_headers, test_project_user_map):
        """Test project attendance marking with invalid project ID"""
        from uuid import uuid4
        
        invalid_data = {
            "project_id": str(uuid4()),  # Non-existent project
            "sub_contractor_id": str(uuid4()),
            "no_of_labours": 10,
            "latitude": 28.6139,
            "longitude": 77.2090
        }
        
        response = client.post(
            "/attendance/project",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["message"] == "Project not found"
    
    def test_mark_project_attendance_invalid_contractor(self, client, auth_headers, test_project_user_map, test_project):
        """Test project attendance marking with invalid sub-contractor ID"""
        from uuid import uuid4
        
        invalid_data = {
            "project_id": str(test_project.uuid),
            "sub_contractor_id": str(uuid4()),  # Non-existent contractor
            "no_of_labours": 10,
            "latitude": 28.6139,
            "longitude": 77.2090
        }
        
        response = client.post(
            "/attendance/project",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["message"] == "Sub-contractor not found"
    
    def test_get_project_attendance_history(self, client, auth_headers, test_project_attendance, test_wage_calculation):
        """Test getting project attendance history"""
        response = client.get(
            "/attendance/project/history?page=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_count"] >= 1
        assert len(data["data"]["attendances"]) >= 1
        assert data["data"]["summary"]["total_labour_days"] >= 10
        assert data["data"]["summary"]["unique_contractors"] >= 1
    
    def test_get_project_attendance_history_with_filters(self, client, auth_headers, test_project_attendance, test_project):
        """Test getting project attendance history with filters"""
        today = date.today()
        response = client.get(
            f"/attendance/project/history?project_id={test_project.uuid}&start_date={today}&end_date={today}&page=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_count"] >= 1
    
    def test_get_project_attendance_history_admin_access(self, client, admin_auth_headers, test_project_attendance):
        """Test that admin can see all project attendances"""
        response = client.get(
            "/attendance/project/history?page=1&limit=10",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Admin should be able to see all attendances
        assert data["data"]["total_count"] >= 1


class TestAttendanceEndpointsValidation:
    """Test validation in attendance endpoints"""
    
    def test_punch_in_invalid_phone_format(self, client, auth_headers):
        """Test punch in with invalid phone format"""
        invalid_data = {
            "phone": 123,  # Too short
            "password": "testpassword",
            "latitude": 28.6139,
            "longitude": 77.2090
        }
        
        response = client.post(
            "/attendance/self/punch-in",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_project_attendance_negative_labours(self, client, auth_headers, test_project, test_person):
        """Test project attendance with negative number of labours"""
        invalid_data = {
            "project_id": str(test_project.uuid),
            "sub_contractor_id": str(test_person.uuid),
            "no_of_labours": -5,  # Invalid: negative
            "latitude": 28.6139,
            "longitude": 77.2090
        }
        
        response = client.post(
            "/attendance/project",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_attendance_history_invalid_pagination(self, client, auth_headers):
        """Test attendance history with invalid pagination parameters"""
        response = client.get(
            "/attendance/self/history?page=0&limit=0",  # Invalid values
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error

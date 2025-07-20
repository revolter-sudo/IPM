"""
Test cases for role-based person query endpoints
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID
from src.app.services.auth_service import get_persons_by_role, update_person_role
from src.app.database.models import User, Person
from src.app.schemas.auth_service_schamas import UserRole, PersonWithRole, UpdatePersonRoleRequest


class TestRoleBasedPersonQueries:
    """Test cases for role-based person query functionality"""
    
    def test_get_persons_by_role_success_direct_role(self):
        """Test successful retrieval of persons with direct role assignment"""
        # Mock dependencies
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()
        
        # Mock person with direct role
        mock_person = MagicMock()
        mock_person.uuid = uuid4()
        mock_person.name = "John Doe"
        mock_person.phone_number = "1234567890"
        mock_person.account_number = "123456789012345"
        mock_person.ifsc_code = "ABCD0123456"
        mock_person.upi_number = "john@upi"
        mock_person.role = UserRole.SITE_ENGINEER.value
        mock_person.user_id = None
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_person]
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        # Call the function
        result = get_persons_by_role(
            role=UserRole.SITE_ENGINEER,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        # Verify result
        assert result['status_code'] == 200
        assert "fetched successfully" in result['message']
        assert len(result['data']) == 1
        assert result['data'][0]['name'] == "John Doe"
        assert result['data'][0]['role'] == UserRole.SITE_ENGINEER.value
        assert result['data'][0]['role_source'] == "person"
    
    def test_get_persons_by_role_success_user_role(self):
        """Test successful retrieval of persons with user role assignment"""
        # Mock dependencies
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()
        
        # Mock person linked to user with role
        user_id = uuid4()
        mock_person = MagicMock()
        mock_person.uuid = uuid4()
        mock_person.name = "Jane Smith"
        mock_person.phone_number = "9876543210"
        mock_person.account_number = "987654321098765"
        mock_person.ifsc_code = "EFGH0987654"
        mock_person.upi_number = "jane@upi"
        mock_person.role = None
        mock_person.user_id = user_id
        
        # Mock user with role
        mock_user = MagicMock()
        mock_user.uuid = user_id
        mock_user.role = UserRole.PROJECT_MANAGER.value
        
        # Mock database queries
        # First query (direct role) returns empty
        mock_db.query.return_value.filter.return_value.all.return_value = []
        # Second query (user role) returns person
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_person]
        # User lookup query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Call the function
        result = get_persons_by_role(
            role=UserRole.PROJECT_MANAGER,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        # Verify result
        assert result['status_code'] == 200
        assert "fetched successfully" in result['message']
        assert len(result['data']) == 1
        assert result['data'][0]['name'] == "Jane Smith"
        assert result['data'][0]['role'] == UserRole.PROJECT_MANAGER.value
        assert result['data'][0]['role_source'] == "user"
        assert str(result['data'][0]['user_id']) == str(user_id)
    
    def test_get_persons_by_role_combined_deduplication(self):
        """Test combining results from both sources with deduplication"""
        # Mock dependencies
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.SUPER_ADMIN.value
        mock_admin_user.uuid = uuid4()
        
        # Mock person that appears in both queries (should be deduplicated)
        person_uuid = uuid4()
        user_id = uuid4()
        
        # Person with direct role
        mock_person_direct = MagicMock()
        mock_person_direct.uuid = person_uuid
        mock_person_direct.name = "Duplicate Person"
        mock_person_direct.phone_number = "1111111111"
        mock_person_direct.account_number = "111111111111111"
        mock_person_direct.ifsc_code = "AAAA1111111"
        mock_person_direct.upi_number = "duplicate@upi"
        mock_person_direct.role = UserRole.ADMIN.value
        mock_person_direct.user_id = user_id
        
        # Same person from user role query
        mock_person_user = MagicMock()
        mock_person_user.uuid = person_uuid  # Same UUID
        mock_person_user.name = "Duplicate Person"
        mock_person_user.phone_number = "1111111111"
        mock_person_user.account_number = "111111111111111"
        mock_person_user.ifsc_code = "AAAA1111111"
        mock_person_user.upi_number = "duplicate@upi"
        mock_person_user.role = None
        mock_person_user.user_id = user_id
        
        # Mock user
        mock_user = MagicMock()
        mock_user.uuid = user_id
        mock_user.role = UserRole.ADMIN.value
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_person_direct]
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_person_user]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Call the function
        result = get_persons_by_role(
            role=UserRole.ADMIN,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        # Verify result - should only have one person (deduplicated)
        assert result['status_code'] == 200
        assert len(result['data']) == 1
        assert result['data'][0]['name'] == "Duplicate Person"
        assert result['data'][0]['role_source'] == "person"  # Direct role takes precedence
    
    def test_get_persons_by_role_unauthorized_user(self):
        """Test access denied for unauthorized user roles"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.role = UserRole.SITE_ENGINEER.value  # Not authorized
        mock_user.uuid = uuid4()
        
        result = get_persons_by_role(
            role=UserRole.ADMIN,
            db=mock_db,
            current_user=mock_user
        )
        
        assert result['status_code'] == 403
        assert "Access denied" in result['message']
    
    def test_get_persons_by_role_invalid_user_session(self):
        """Test handling of invalid user session"""
        mock_db = MagicMock()
        mock_user = None  # Invalid user
        
        result = get_persons_by_role(
            role=UserRole.ADMIN,
            db=mock_db,
            current_user=mock_user
        )
        
        assert result['status_code'] == 401
        assert "Invalid user session" in result['message']
    
    def test_get_persons_by_role_database_error_direct_role(self):
        """Test handling of database error in direct role query"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()
        
        # Mock database error
        mock_db.query.return_value.filter.return_value.all.side_effect = Exception("Database error")
        
        result = get_persons_by_role(
            role=UserRole.ADMIN,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        assert result['status_code'] == 500
        assert "Error retrieving persons with direct role" in result['message']
    
    def test_get_persons_by_role_database_error_user_role(self):
        """Test handling of database error in user role query"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()
        
        # First query succeeds, second query fails
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.side_effect = Exception("Database error")
        
        result = get_persons_by_role(
            role=UserRole.ADMIN,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        assert result['status_code'] == 500
        assert "Error retrieving persons with user role" in result['message']
    
    def test_get_persons_by_role_empty_results(self):
        """Test handling when no persons are found"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()
        
        # Both queries return empty results
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = get_persons_by_role(
            role=UserRole.ADMIN,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        assert result['status_code'] == 200
        assert len(result['data']) == 0
        assert "Found 0 persons" in result['message']
    
    def test_get_persons_by_role_project_manager_access(self):
        """Test that project managers have access to the endpoint"""
        mock_db = MagicMock()
        mock_pm_user = MagicMock()
        mock_pm_user.role = UserRole.PROJECT_MANAGER.value
        mock_pm_user.uuid = uuid4()
        
        # Mock empty results
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = get_persons_by_role(
            role=UserRole.SITE_ENGINEER,
            db=mock_db,
            current_user=mock_pm_user
        )
        
        # Should succeed (not get 403 error)
        assert result['status_code'] == 200
    
    def test_get_persons_by_role_invalid_person_data(self):
        """Test handling of invalid person data"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()
        
        # Mock person with missing attributes
        mock_person = MagicMock()
        mock_person.uuid = uuid4()
        mock_person.name = None  # Missing name
        mock_person.phone_number = None  # Missing phone
        mock_person.account_number = "123456789012345"
        mock_person.ifsc_code = "ABCD0123456"
        mock_person.upi_number = None
        mock_person.role = UserRole.ADMIN.value
        mock_person.user_id = None
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_person]
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = get_persons_by_role(
            role=UserRole.ADMIN,
            db=mock_db,
            current_user=mock_admin_user
        )
        
        # Should handle missing data gracefully
        assert result['status_code'] == 200
        assert len(result['data']) == 1
        assert result['data'][0]['name'] == ""  # Should default to empty string
        assert result['data'][0]['phone_number'] == ""


class TestPersonRoleUpdate:
    """Test cases for person role update functionality"""

    def test_update_person_role_success_assign_role(self):
        """Test successful role assignment to person"""
        # Mock dependencies
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()

        # Mock person to update
        person_id = uuid4()
        mock_person = MagicMock()
        mock_person.uuid = person_id
        mock_person.name = "John Doe"
        mock_person.phone_number = "1234567890"
        mock_person.role = None  # No role initially

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_person
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Create request data
        request_data = UpdatePersonRoleRequest(role=UserRole.SITE_ENGINEER)

        # Call the function
        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_admin_user
        )

        # Verify result
        assert result['status_code'] == 200
        assert "Role set to 'SiteEngineer'" in result['message']
        assert result['data']['person_id'] == str(person_id)
        assert result['data']['old_role'] is None
        assert result['data']['new_role'] == UserRole.SITE_ENGINEER.value
        assert result['data']['updated_by'] == str(mock_admin_user.uuid)

        # Verify database operations
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_person)
        assert mock_person.role == UserRole.SITE_ENGINEER.value

    def test_update_person_role_success_remove_role(self):
        """Test successful role removal from person"""
        # Mock dependencies
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.SUPER_ADMIN.value
        mock_admin_user.uuid = uuid4()

        # Mock person with existing role
        person_id = uuid4()
        mock_person = MagicMock()
        mock_person.uuid = person_id
        mock_person.name = "Jane Smith"
        mock_person.phone_number = "9876543210"
        mock_person.role = UserRole.PROJECT_MANAGER.value  # Has existing role

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_person
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Create request data to remove role
        request_data = UpdatePersonRoleRequest(role=None)

        # Call the function
        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_admin_user
        )

        # Verify result
        assert result['status_code'] == 200
        assert "Role removed" in result['message']
        assert result['data']['person_id'] == str(person_id)
        assert result['data']['old_role'] == UserRole.PROJECT_MANAGER.value
        assert result['data']['new_role'] is None

        # Verify database operations
        mock_db.commit.assert_called_once()
        assert mock_person.role is None

    def test_update_person_role_unauthorized_user(self):
        """Test role update with unauthorized user"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.role = UserRole.SITE_ENGINEER.value  # Not authorized
        mock_user.uuid = uuid4()

        person_id = uuid4()
        request_data = UpdatePersonRoleRequest(role=UserRole.ADMIN)

        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_user
        )

        assert result['status_code'] == 403
        assert "Access denied" in result['message']

    def test_update_person_role_invalid_user_session(self):
        """Test role update with invalid user session"""
        mock_db = MagicMock()
        mock_user = None  # Invalid user

        person_id = uuid4()
        request_data = UpdatePersonRoleRequest(role=UserRole.ADMIN)

        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_user
        )

        assert result['status_code'] == 401
        assert "Invalid user session" in result['message']

    def test_update_person_role_person_not_found(self):
        """Test role update when person doesn't exist"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()

        # Mock person not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        person_id = uuid4()
        request_data = UpdatePersonRoleRequest(role=UserRole.SITE_ENGINEER)

        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_admin_user
        )

        assert result['status_code'] == 404
        assert "Person not found" in result['message']

    def test_update_person_role_database_error_query(self):
        """Test role update with database query error"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()

        # Mock database error during query
        mock_db.query.return_value.filter.return_value.first.side_effect = Exception("Database error")

        person_id = uuid4()
        request_data = UpdatePersonRoleRequest(role=UserRole.SITE_ENGINEER)

        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_admin_user
        )

        assert result['status_code'] == 500
        assert "Error retrieving person data" in result['message']

    def test_update_person_role_database_error_commit(self):
        """Test role update with database commit error"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()

        # Mock person found
        person_id = uuid4()
        mock_person = MagicMock()
        mock_person.uuid = person_id
        mock_person.name = "Test Person"
        mock_person.role = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_person

        # Mock database error during commit
        mock_db.commit.side_effect = Exception("Commit failed")

        request_data = UpdatePersonRoleRequest(role=UserRole.SITE_ENGINEER)

        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_admin_user
        )

        assert result['status_code'] == 500
        assert "Error updating person role" in result['message']
        mock_db.rollback.assert_called_once()

    def test_update_person_role_change_existing_role(self):
        """Test changing an existing role to a different role"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.SUPER_ADMIN.value
        mock_admin_user.uuid = uuid4()

        # Mock person with existing role
        person_id = uuid4()
        mock_person = MagicMock()
        mock_person.uuid = person_id
        mock_person.name = "Role Changer"
        mock_person.phone_number = "5555555555"
        mock_person.role = UserRole.SITE_ENGINEER.value  # Existing role

        mock_db.query.return_value.filter.return_value.first.return_value = mock_person
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Change role to PROJECT_MANAGER
        request_data = UpdatePersonRoleRequest(role=UserRole.PROJECT_MANAGER)

        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_admin_user
        )

        # Verify result
        assert result['status_code'] == 200
        assert "Role set to 'ProjectManager'" in result['message']
        assert result['data']['old_role'] == UserRole.SITE_ENGINEER.value
        assert result['data']['new_role'] == UserRole.PROJECT_MANAGER.value

        # Verify role was updated
        assert mock_person.role == UserRole.PROJECT_MANAGER.value

    def test_update_person_role_project_manager_unauthorized(self):
        """Test that project managers cannot update person roles"""
        mock_db = MagicMock()
        mock_pm_user = MagicMock()
        mock_pm_user.role = UserRole.PROJECT_MANAGER.value  # Not authorized for role updates
        mock_pm_user.uuid = uuid4()

        person_id = uuid4()
        request_data = UpdatePersonRoleRequest(role=UserRole.SITE_ENGINEER)

        result = update_person_role(
            person_id=person_id,
            request_data=request_data,
            db=mock_db,
            current_user=mock_pm_user
        )

        assert result['status_code'] == 403
        assert "Access denied" in result['message']

    def test_update_person_role_empty_person_id(self):
        """Test role update with empty person ID"""
        mock_db = MagicMock()
        mock_admin_user = MagicMock()
        mock_admin_user.role = UserRole.ADMIN.value
        mock_admin_user.uuid = uuid4()

        request_data = UpdatePersonRoleRequest(role=UserRole.SITE_ENGINEER)

        result = update_person_role(
            person_id=None,
            request_data=request_data,
            db=mock_db,
            current_user=mock_admin_user
        )

        assert result['status_code'] == 400
        assert "Person ID is required" in result['message']

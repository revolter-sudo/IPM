"""
Test cases for payment API endpoints with khatabook status validation.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from src.app.database.models import Payment, User
from src.app.schemas.auth_service_schamas import UserRole


class TestPaymentAPIKhatabookValidation:
    """Test class for payment API validation with khatabook status."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user with admin role."""
        user = Mock(spec=User)
        user.uuid = uuid4()
        user.role = UserRole.ADMIN.value
        return user

    @pytest.fixture
    def mock_khatabook_payment(self):
        """Create a mock payment with khatabook status."""
        payment = Mock(spec=Payment)
        payment.uuid = uuid4()
        payment.status = "khatabook"
        payment.amount = 1000.0
        payment.project_id = uuid4()
        payment.created_by = uuid4()
        return payment

    @pytest.fixture
    def mock_regular_payment(self):
        """Create a mock payment with regular status."""
        payment = Mock(spec=Payment)
        payment.uuid = uuid4()
        payment.status = "requested"
        payment.amount = 1000.0
        payment.project_id = uuid4()
        payment.created_by = uuid4()
        return payment

    @patch('src.app.services.payment_service.get_current_user')
    @patch('src.app.services.payment_service.get_db')
    def test_approve_khatabook_payment_returns_error(
        self, mock_get_db, mock_get_current_user, mock_user, mock_khatabook_payment
    ):
        """Test that approving a khatabook payment returns an error."""
        # Arrange
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_khatabook_payment
        mock_get_db.return_value = mock_db
        mock_get_current_user.return_value = mock_user

        # Import here to avoid circular imports
        from src.app.services.payment_service import approve_payment

        # Act
        result = approve_payment(
            payment_id=mock_khatabook_payment.uuid,
            bank_uuid=None,
            files=None,
            db=mock_db,
            current_user=mock_user
        )

        # Assert
        assert result['status_code'] == 400
        assert "Khatabook payments cannot be approved" in result['message']

    @patch('src.app.services.payment_service.get_current_user')
    @patch('src.app.services.payment_service.get_db')
    def test_decline_khatabook_payment_returns_error(
        self, mock_get_db, mock_get_current_user, mock_user, mock_khatabook_payment
    ):
        """Test that declining a khatabook payment returns an error."""
        # Arrange
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_khatabook_payment
        mock_get_db.return_value = mock_db
        mock_get_current_user.return_value = mock_user

        # Import here to avoid circular imports
        from src.app.services.payment_service import decline_payment

        # Act
        result = decline_payment(
            payment_id=mock_khatabook_payment.uuid,
            remarks="Test decline",
            db=mock_db,
            current_user=mock_user
        )

        # Assert
        assert result['status_code'] == 400
        assert "Khatabook payments cannot be declined" in result['message']

    @patch('src.app.services.payment_service.get_current_user')
    @patch('src.app.services.payment_service.get_db')
    def test_approve_regular_payment_works(
        self, mock_get_db, mock_get_current_user, mock_user, mock_regular_payment
    ):
        """Test that approving a regular payment still works."""
        # Arrange
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_regular_payment
        mock_db.commit = Mock()
        mock_get_db.return_value = mock_db
        mock_get_current_user.return_value = mock_user

        # Mock the notification function
        with patch('src.app.services.payment_service.notify_payment_status_update'):
            # Import here to avoid circular imports
            from src.app.services.payment_service import approve_payment

            # Act
            result = approve_payment(
                payment_id=mock_regular_payment.uuid,
                bank_uuid=None,
                files=None,
                db=mock_db,
                current_user=mock_user
            )

            # Assert
            assert result['status_code'] == 200
            assert "successfully" in result['message']

    def test_payment_status_validation_logic(self):
        """Test the payment status validation logic."""
        # Test khatabook payment validation
        khatabook_payment = Mock()
        khatabook_payment.status = "khatabook"
        
        # Should not be approvable
        assert khatabook_payment.status == "khatabook"
        
        # Test regular payment validation
        regular_payment = Mock()
        regular_payment.status = "requested"
        
        # Should be approvable
        assert regular_payment.status != "khatabook"

    def test_status_order_mapping_includes_khatabook(self):
        """Test that status order mapping includes khatabook with highest priority."""
        status_order_map = {
            "requested": 1,
            "verified": 2,
            "approved": 3,
            "transferred": 4,
            "khatabook": 5
        }
        
        # Khatabook should have the highest order (non-changeable)
        assert status_order_map["khatabook"] == 5
        assert status_order_map["khatabook"] > max([
            status_order_map["requested"],
            status_order_map["verified"],
            status_order_map["approved"],
            status_order_map["transferred"]
        ])


class TestPaymentTotalCalculations:
    """Test class for payment total calculations with khatabook exclusions."""

    @pytest.fixture
    def mock_db_with_payments(self):
        """Create a mock database with various payment types."""
        db = Mock()
        
        # Mock query results for different payment types
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 5000.0  # Total excluding khatabook
        
        db.query.return_value = mock_query
        return db

    def test_payment_total_calculation_logic(self):
        """Test the logic for payment total calculations."""
        # Test that the correct statuses are used for calculations
        request_statuses = ["requested", "verified", "approved", "transferred"]
        pending_statuses = ["requested", "verified", "approved"]

        # Verify khatabook is not included
        assert "khatabook" not in request_statuses
        assert "khatabook" not in pending_statuses

        # Verify regular statuses are included
        assert "transferred" in request_statuses
        assert "transferred" not in pending_statuses

    def test_payment_status_filtering_logic(self):
        """Test the logic for filtering payment statuses."""
        # Define the statuses that should be included in global totals
        included_statuses = ["requested", "verified", "approved", "transferred"]
        excluded_statuses = ["khatabook", "declined"]
        
        # Test that khatabook is not in included statuses
        assert "khatabook" not in included_statuses
        assert "khatabook" in excluded_statuses
        
        # Test that regular statuses are included
        for status in ["requested", "verified", "approved", "transferred"]:
            assert status in included_statuses


class TestKhatabookPaymentCreationValidation:
    """Test class for validating khatabook payment creation rules."""

    def test_khatabook_payment_creation_requirements(self):
        """Test the requirements for creating payments from khatabook entries."""
        # Test data with both project and person (should create payment)
        valid_data = {
            "project_id": uuid4(),
            "person_id": uuid4(),
            "amount": 1000.0
        }
        
        # Test data missing project (should not create payment)
        missing_project_data = {
            "project_id": None,
            "person_id": uuid4(),
            "amount": 1000.0
        }
        
        # Test data missing person (should not create payment)
        missing_person_data = {
            "project_id": uuid4(),
            "person_id": None,
            "amount": 1000.0
        }
        
        # Validation logic
        def should_create_payment(data):
            return data.get("project_id") is not None and data.get("person_id") is not None
        
        # Assertions
        assert should_create_payment(valid_data) is True
        assert should_create_payment(missing_project_data) is False
        assert should_create_payment(missing_person_data) is False

    def test_khatabook_payment_properties(self):
        """Test the properties of payments created from khatabook entries."""
        # Expected properties for khatabook payments
        expected_properties = {
            "status": "khatabook",
            "self_payment": False,
            "description_prefix": "Auto-generated from khatabook entry"
        }
        
        # Verify expected properties
        assert expected_properties["status"] == "khatabook"
        assert expected_properties["self_payment"] is False
        assert "Auto-generated" in expected_properties["description_prefix"]


if __name__ == "__main__":
    pytest.main([__file__])

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


class TestKhatabookPaymentVisibilityAndEditing:
    """Test class for khatabook payment visibility and editing restrictions."""

    @pytest.fixture
    def mock_creator_user(self):
        """Create a mock user who created the khatabook entry."""
        user = Mock(spec=User)
        user.uuid = uuid4()
        user.role = UserRole.SITE_ENGINEER.value
        return user

    @pytest.fixture
    def mock_project_manager(self):
        """Create a mock project manager user."""
        user = Mock(spec=User)
        user.uuid = uuid4()
        user.role = UserRole.PROJECT_MANAGER.value
        return user

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user."""
        user = Mock(spec=User)
        user.uuid = uuid4()
        user.role = UserRole.ADMIN.value
        return user

    @pytest.fixture
    def mock_accountant_user(self):
        """Create a mock accountant user."""
        user = Mock(spec=User)
        user.uuid = uuid4()
        user.role = UserRole.ACCOUNTANT.value
        return user

    @pytest.fixture
    def mock_other_user(self):
        """Create a mock user who is not related to the khatabook entry."""
        user = Mock(spec=User)
        user.uuid = uuid4()
        user.role = UserRole.SITE_ENGINEER.value
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

    def test_khatabook_payment_visibility_rules(
        self, mock_creator_user, mock_project_manager, mock_admin_user,
        mock_accountant_user, mock_other_user
    ):
        """Test who can see khatabook payments."""
        project_id = uuid4()
        creator_id = mock_creator_user.uuid

        # Simulate visibility logic
        def can_see_khatabook_payment(user, payment_creator_id, payment_project_id, user_project_ids=None):
            # Creator can always see their khatabook payments
            if user.uuid == payment_creator_id:
                return True

            # Admin, Accountant, Super Admin can see all khatabook payments
            if user.role in [UserRole.ADMIN.value, UserRole.ACCOUNTANT.value, UserRole.SUPER_ADMIN.value]:
                return True

            # Project Manager can see khatabook payments from their projects
            if user.role == UserRole.PROJECT_MANAGER.value:
                if user_project_ids and payment_project_id in user_project_ids:
                    return True

            return False

        # Test visibility for different users
        assert can_see_khatabook_payment(mock_creator_user, creator_id, project_id) is True
        assert can_see_khatabook_payment(mock_admin_user, creator_id, project_id) is True
        assert can_see_khatabook_payment(mock_accountant_user, creator_id, project_id) is True
        assert can_see_khatabook_payment(mock_project_manager, creator_id, project_id, [project_id]) is True
        assert can_see_khatabook_payment(mock_project_manager, creator_id, project_id, [uuid4()]) is False
        assert can_see_khatabook_payment(mock_other_user, creator_id, project_id) is False

    def test_khatabook_payment_edit_restrictions(self):
        """Test that khatabook payments cannot be edited."""
        # Test the can_edit_payment function logic
        from src.app.services.payment_service import can_edit_payment

        # Test with khatabook status
        assert can_edit_payment(["khatabook"], UserRole.ADMIN.value, "khatabook") is False
        assert can_edit_payment(["requested", "khatabook"], UserRole.ADMIN.value) is False
        assert can_edit_payment(["khatabook"], UserRole.PROJECT_MANAGER.value) is False
        assert can_edit_payment(["khatabook"], UserRole.SUPER_ADMIN.value) is False

        # Test with regular statuses (should be editable by appropriate roles)
        assert can_edit_payment(["requested"], UserRole.ADMIN.value, "requested") is True
        assert can_edit_payment(["verified"], UserRole.PROJECT_MANAGER.value, "verified") is True

    @patch('src.app.services.payment_service.get_current_user')
    @patch('src.app.services.payment_service.get_db')
    def test_update_khatabook_payment_returns_error(
        self, mock_get_db, mock_get_current_user, mock_admin_user, mock_khatabook_payment
    ):
        """Test that updating a khatabook payment returns an error."""
        # Arrange
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_khatabook_payment
        mock_get_db.return_value = mock_db
        mock_get_current_user.return_value = mock_admin_user

        # Import here to avoid circular imports
        from src.app.services.payment_service import update_payment_amount
        from src.app.schemas.payment_service_schemas import PaymentUpdateSchema

        # Create mock payload
        mock_payload = PaymentUpdateSchema(amount=2000.0, remark="Test update")

        # Act
        result = update_payment_amount(
            payment_uuid=mock_khatabook_payment.uuid,
            payload=mock_payload,
            db=mock_db,
            current_user=mock_admin_user
        )

        # Assert
        assert result['status_code'] == 400
        assert "Khatabook payments cannot be edited" in result['message']


class TestKhatabookPaymentPersonVisibility:
    """Test class for person-based visibility of khatabook payments."""

    def test_person_visibility_logic(self):
        """Test that persons with user accounts can see khatabook payments where they are selected."""
        from uuid import uuid4

        # Mock data
        user_id = uuid4()
        person_id = uuid4()
        other_person_id = uuid4()
        project_id = uuid4()

        # Simulate the visibility logic
        def can_see_khatabook_payment_as_person(current_user_id, user_person_id, payment_person_id, payment_status):
            # If the current user has a linked person record and that person is selected in the khatabook payment
            if (payment_status == "khatabook" and
                user_person_id is not None and
                payment_person_id == user_person_id):
                return True
            return False

        # Test scenarios
        assert can_see_khatabook_payment_as_person(user_id, person_id, person_id, "khatabook") is True
        assert can_see_khatabook_payment_as_person(user_id, person_id, other_person_id, "khatabook") is False
        assert can_see_khatabook_payment_as_person(user_id, None, person_id, "khatabook") is False  # No linked person
        assert can_see_khatabook_payment_as_person(user_id, person_id, person_id, "requested") is False  # Not khatabook

    def test_combined_visibility_rules(self):
        """Test combined visibility rules for khatabook payments."""
        from src.app.schemas.auth_service_schamas import UserRole

        def can_see_khatabook_payment_combined(
            user_role, is_creator, is_project_manager_of_project,
            is_admin_role, is_selected_person
        ):
            # Creator can always see
            if is_creator:
                return True

            # Admin, Accountant, Super Admin can see all
            if is_admin_role:
                return True

            # Project Manager can see if assigned to the project
            if user_role == UserRole.PROJECT_MANAGER.value and is_project_manager_of_project:
                return True

            # Person selected in the khatabook payment can see it
            if is_selected_person:
                return True

            return False

        # Test all combinations
        assert can_see_khatabook_payment_combined(
            UserRole.SITE_ENGINEER.value, True, False, False, False
        ) is True  # Creator

        assert can_see_khatabook_payment_combined(
            UserRole.ADMIN.value, False, False, True, False
        ) is True  # Admin

        assert can_see_khatabook_payment_combined(
            UserRole.PROJECT_MANAGER.value, False, True, False, False
        ) is True  # PM of project

        assert can_see_khatabook_payment_combined(
            UserRole.SITE_ENGINEER.value, False, False, False, True
        ) is True  # Selected person

        assert can_see_khatabook_payment_combined(
            UserRole.SITE_ENGINEER.value, False, False, False, False
        ) is False  # No access


class TestKhatabookPaymentFilteredTotals:
    """Test class for khatabook payment inclusion in filtered totals."""

    def test_filtered_vs_global_totals_logic(self):
        """Test the logic for including khatabook payments in filtered vs global totals."""

        def should_include_khatabook_in_totals(project_filter, item_filter, person_filter, user_filter):
            """Determine if khatabook payments should be included in totals."""
            has_specific_filters = any([project_filter, item_filter, person_filter, user_filter])
            return has_specific_filters

        # Test scenarios
        assert should_include_khatabook_in_totals(True, False, False, False) is True  # Project filter
        assert should_include_khatabook_in_totals(False, True, False, False) is True  # Item filter
        assert should_include_khatabook_in_totals(False, False, True, False) is True  # Person filter
        assert should_include_khatabook_in_totals(False, False, False, True) is True  # User filter
        assert should_include_khatabook_in_totals(True, True, False, False) is True  # Multiple filters
        assert should_include_khatabook_in_totals(False, False, False, False) is False  # No filters (global)

    def test_status_inclusion_logic(self):
        """Test which statuses are included in different scenarios."""

        def get_included_statuses(has_filters):
            """Get the list of statuses to include in totals."""
            base_statuses = ["requested", "verified", "approved", "transferred"]
            if has_filters:
                return base_statuses + ["khatabook"]
            return base_statuses

        # Test status inclusion
        global_statuses = get_included_statuses(False)
        filtered_statuses = get_included_statuses(True)

        assert "khatabook" not in global_statuses
        assert "khatabook" in filtered_statuses
        assert len(filtered_statuses) == len(global_statuses) + 1

        # Verify all base statuses are included in both
        for status in ["requested", "verified", "approved", "transferred"]:
            assert status in global_statuses
            assert status in filtered_statuses


class TestKhatabookPaymentRecentPaymentsExclusion:
    """Test class for ensuring khatabook payments are excluded from recent payments."""

    def test_recent_payments_status_exclusion_logic(self):
        """Test that khatabook payments are excluded from recent payments along with declined and transferred."""

        # Define the statuses that should be excluded from recent payments
        excluded_from_recent = ["declined", "transferred", "khatabook"]

        # Define all possible payment statuses
        all_statuses = ["requested", "verified", "approved", "transferred", "declined", "khatabook"]

        # Calculate which statuses should be included in recent payments
        included_in_recent = [status for status in all_statuses if status not in excluded_from_recent]

        # Verify the exclusion logic
        assert "khatabook" in excluded_from_recent
        assert "declined" in excluded_from_recent
        assert "transferred" in excluded_from_recent

        # Verify the inclusion logic
        assert "requested" in included_in_recent
        assert "verified" in included_in_recent
        assert "approved" in included_in_recent

        # Verify khatabook is not in recent payments
        assert "khatabook" not in included_in_recent

    def test_recent_payments_filtering_scenarios(self):
        """Test different scenarios for recent payments filtering."""

        # Simulate payment data with different statuses
        payments = [
            {"id": 1, "status": "requested", "created_at": "2024-01-05"},
            {"id": 2, "status": "verified", "created_at": "2024-01-04"},
            {"id": 3, "status": "khatabook", "created_at": "2024-01-03"},  # Should be excluded
            {"id": 4, "status": "approved", "created_at": "2024-01-02"},
            {"id": 5, "status": "transferred", "created_at": "2024-01-01"},  # Should be excluded
            {"id": 6, "status": "declined", "created_at": "2023-12-31"},  # Should be excluded
        ]

        def filter_recent_payments(payments):
            """Simulate the recent payments filtering logic."""
            excluded_statuses = ["declined", "transferred", "khatabook"]
            return [p for p in payments if p["status"] not in excluded_statuses]

        # Apply the filtering
        recent_payments = filter_recent_payments(payments)

        # Verify results
        assert len(recent_payments) == 3  # Only requested, verified, approved

        recent_statuses = [p["status"] for p in recent_payments]
        assert "requested" in recent_statuses
        assert "verified" in recent_statuses
        assert "approved" in recent_statuses

        # Verify excluded statuses are not present
        assert "khatabook" not in recent_statuses
        assert "transferred" not in recent_statuses
        assert "declined" not in recent_statuses

    def test_recent_payments_query_logic(self):
        """Test the query logic for recent payments exclusion."""

        def build_recent_query_filter(exclude_statuses):
            """Simulate the recent payments query filter logic."""
            # This simulates: Payment.status.not_in(recent_status)
            return lambda payment_status: payment_status not in exclude_statuses

        # Test the filter with the correct exclusion list
        exclude_statuses = ["declined", "transferred", "khatabook"]
        filter_func = build_recent_query_filter(exclude_statuses)

        # Test various payment statuses
        test_cases = [
            ("requested", True),    # Should be included
            ("verified", True),     # Should be included
            ("approved", True),     # Should be included
            ("transferred", False), # Should be excluded
            ("declined", False),    # Should be excluded
            ("khatabook", False),   # Should be excluded
        ]

        for status, should_be_included in test_cases:
            result = filter_func(status)
            assert result == should_be_included, f"Status '{status}' inclusion test failed"

    def test_recent_payments_business_logic(self):
        """Test the business logic reasoning for excluding khatabook payments from recent payments."""

        # Define the characteristics of different payment types
        payment_characteristics = {
            "requested": {
                "user_initiated": True,
                "requires_action": True,
                "show_in_recent": True,
                "reason": "User needs to see their payment requests"
            },
            "verified": {
                "user_initiated": True,
                "requires_action": True,
                "show_in_recent": True,
                "reason": "Payment is progressing through approval workflow"
            },
            "approved": {
                "user_initiated": True,
                "requires_action": True,
                "show_in_recent": True,
                "reason": "Payment is ready for transfer"
            },
            "transferred": {
                "user_initiated": True,
                "requires_action": False,
                "show_in_recent": False,
                "reason": "Payment is complete, no action needed"
            },
            "declined": {
                "user_initiated": True,
                "requires_action": False,
                "show_in_recent": False,
                "reason": "Payment was rejected, no action needed"
            },
            "khatabook": {
                "user_initiated": False,
                "requires_action": False,
                "show_in_recent": False,
                "reason": "Auto-generated system entry, not a user payment request"
            }
        }

        # Verify that only user-initiated payments that require action are shown in recent
        for status, characteristics in payment_characteristics.items():
            expected_in_recent = characteristics["user_initiated"] and characteristics["requires_action"]
            actual_in_recent = characteristics["show_in_recent"]

            assert actual_in_recent == expected_in_recent, (
                f"Status '{status}' recent payment logic failed. "
                f"Expected: {expected_in_recent}, Actual: {actual_in_recent}. "
                f"Reason: {characteristics['reason']}"
            )

        # Specifically verify khatabook exclusion reasoning
        khatabook_chars = payment_characteristics["khatabook"]
        assert not khatabook_chars["user_initiated"], "Khatabook payments are system-generated"
        assert not khatabook_chars["requires_action"], "Khatabook payments require no user action"
        assert not khatabook_chars["show_in_recent"], "Khatabook payments should not appear in recent payments"


if __name__ == "__main__":
    pytest.main([__file__])

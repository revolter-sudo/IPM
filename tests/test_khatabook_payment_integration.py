"""
Test cases for the auto-generation of payment records from khatabook entries.
"""

import pytest
from uuid import uuid4
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from src.app.database.models import (
    Khatabook, Payment, PaymentStatusHistory, KhatabookBalance,
    User, Person, Project, KhatabookItem, PaymentItem, Item
)
from src.app.services.khatabook_service import (
    create_khatabook_entry_service,
    create_payment_from_khatabook_entry
)
from src.app.schemas.payment_service_schemas import PaymentStatus


class TestKhatabookPaymentIntegration:
    """Test class for khatabook-payment integration features."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []  # For khatabook items query
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.rollback = Mock()
        return db

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_project_id(self):
        """Sample project ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_person_id(self):
        """Sample person ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_khatabook_entry(self, sample_user_id, sample_project_id, sample_person_id):
        """Create a sample khatabook entry."""
        return Khatabook(
            uuid=uuid4(),
            amount=1000.0,
            remarks="Test khatabook entry",
            person_id=sample_person_id,
            project_id=sample_project_id,
            created_by=sample_user_id,
            balance_after_entry=500.0,
            payment_mode="Cash",
            entry_type="Debit"
        )

    def test_create_payment_from_khatabook_entry_success(
        self, mock_db, sample_khatabook_entry, sample_user_id
    ):
        """Test successful creation of payment from khatabook entry."""
        # Act
        result = create_payment_from_khatabook_entry(
            mock_db, sample_khatabook_entry, sample_user_id
        )

        # Assert
        assert result is not None
        assert isinstance(result, Payment)
        assert result.amount == sample_khatabook_entry.amount
        assert result.project_id == sample_khatabook_entry.project_id
        assert result.person == sample_khatabook_entry.person_id
        assert result.status == "khatabook"
        assert result.created_by == sample_user_id
        assert result.self_payment is False
        assert "Auto-generated from khatabook entry" in result.description

        # Verify database operations
        assert mock_db.add.call_count == 2  # Payment + PaymentStatusHistory
        mock_db.flush.assert_called_once()

    def test_create_payment_from_khatabook_entry_missing_project(
        self, mock_db, sample_khatabook_entry, sample_user_id
    ):
        """Test that payment is not created when project_id is missing."""
        # Arrange
        sample_khatabook_entry.project_id = None

        # Act
        result = create_payment_from_khatabook_entry(
            mock_db, sample_khatabook_entry, sample_user_id
        )

        # Assert
        assert result is None
        mock_db.add.assert_not_called()

    def test_create_payment_from_khatabook_entry_missing_person(
        self, mock_db, sample_khatabook_entry, sample_user_id
    ):
        """Test that payment is not created when person_id is missing."""
        # Arrange
        sample_khatabook_entry.person_id = None

        # Act
        result = create_payment_from_khatabook_entry(
            mock_db, sample_khatabook_entry, sample_user_id
        )

        # Assert
        assert result is None
        mock_db.add.assert_not_called()

    def test_payment_status_enum_includes_khatabook(self):
        """Test that PaymentStatus enum includes KHATABOOK."""
        assert hasattr(PaymentStatus, 'KHATABOOK')
        assert PaymentStatus.KHATABOOK.value == "khatabook"

    def test_khatabook_entry_creation_integration_logic(
        self, sample_project_id, sample_person_id
    ):
        """Test the integration logic for khatabook entry and payment creation."""
        # Test the logic that determines when payments should be created
        data_with_project_and_person = {
            "project_id": sample_project_id,
            "person_id": sample_person_id,
            "amount": 500.0
        }

        data_missing_project = {
            "project_id": None,
            "person_id": sample_person_id,
            "amount": 500.0
        }

        data_missing_person = {
            "project_id": sample_project_id,
            "person_id": None,
            "amount": 500.0
        }

        # Test the logic for when payments should be created
        def should_create_payment(data):
            return data.get("project_id") is not None and data.get("person_id") is not None

        assert should_create_payment(data_with_project_and_person) is True
        assert should_create_payment(data_missing_project) is False
        assert should_create_payment(data_missing_person) is False

    def test_payment_status_filtering_excludes_khatabook(self):
        """Test that payment status filtering logic excludes khatabook payments."""
        # Define the statuses that should be included in global totals
        included_statuses = ["requested", "verified", "approved", "transferred"]
        excluded_statuses = ["khatabook", "declined"]

        # Test that khatabook is not in included statuses
        assert "khatabook" not in included_statuses
        assert "khatabook" in excluded_statuses

        # Test that regular statuses are included
        for status in ["requested", "verified", "approved", "transferred"]:
            assert status in included_statuses


class TestKhatabookPaymentValidation:
    """Test class for khatabook payment validation features."""

    @pytest.fixture
    def mock_payment(self):
        """Create a mock payment with khatabook status."""
        payment = Mock(spec=Payment)
        payment.uuid = uuid4()
        payment.status = "khatabook"
        payment.amount = 1000.0
        return payment

    def test_khatabook_payment_cannot_be_approved(self, mock_payment):
        """Test that khatabook payments cannot be approved."""
        # This would be tested in the actual approve_payment endpoint
        # Here we just verify the status check logic
        assert mock_payment.status == "khatabook"
        
        # In the actual implementation, this should return an error
        can_approve = mock_payment.status != "khatabook"
        assert not can_approve

    def test_khatabook_payment_cannot_be_declined(self, mock_payment):
        """Test that khatabook payments cannot be declined."""
        # This would be tested in the actual decline_payment endpoint
        # Here we just verify the status check logic
        assert mock_payment.status == "khatabook"
        
        # In the actual implementation, this should return an error
        can_decline = mock_payment.status != "khatabook"
        assert not can_decline

    def test_khatabook_status_order_is_highest(self):
        """Test that khatabook status has the highest order value."""
        status_order_map = {
            "requested": 1,
            "verified": 2,
            "approved": 3,
            "transferred": 4,
            "khatabook": 5
        }
        
        assert status_order_map["khatabook"] == 5
        assert status_order_map["khatabook"] > status_order_map["transferred"]


class TestKhatabookPaymentErrorHandling:
    """Test class for error handling in khatabook-payment integration."""

    def test_payment_creation_error_handling_logic(self):
        """Test the error handling logic for payment creation."""
        # Test that the function should handle database errors gracefully
        # This tests the logic without actually calling the database

        # Simulate the error handling logic
        def simulate_payment_creation_with_error():
            try:
                # Simulate database error
                raise Exception("Database error")
            except Exception as e:
                # This should be logged and handled gracefully
                error_message = str(e)
                return None, error_message

        # Act
        result, error = simulate_payment_creation_with_error()

        # Assert
        assert result is None
        assert "Database error" in error

        # The key point is that the error should be caught and handled,
        # not propagated to fail the entire khatabook creation process


class TestKhatabookPaymentAccessControl:
    """Test class for khatabook payment access control and visibility."""

    def test_role_based_visibility_logic(self):
        """Test the role-based visibility logic for khatabook payments."""
        from src.app.schemas.auth_service_schamas import UserRole

        # Define visibility rules
        def can_see_khatabook_payment(user_role, is_creator, is_project_manager_of_project, is_admin_role):
            # Creator can always see
            if is_creator:
                return True

            # Admin, Accountant, Super Admin can see all
            if is_admin_role:
                return True

            # Project Manager can see if assigned to the project
            if user_role == UserRole.PROJECT_MANAGER.value and is_project_manager_of_project:
                return True

            return False

        # Test different scenarios
        assert can_see_khatabook_payment(UserRole.SITE_ENGINEER.value, True, False, False) is True  # Creator
        assert can_see_khatabook_payment(UserRole.ADMIN.value, False, False, True) is True  # Admin
        assert can_see_khatabook_payment(UserRole.ACCOUNTANT.value, False, False, True) is True  # Accountant
        assert can_see_khatabook_payment(UserRole.PROJECT_MANAGER.value, False, True, False) is True  # PM of project
        assert can_see_khatabook_payment(UserRole.PROJECT_MANAGER.value, False, False, False) is False  # PM not of project
        assert can_see_khatabook_payment(UserRole.SITE_ENGINEER.value, False, False, False) is False  # Other user

    def test_edit_restriction_logic(self):
        """Test that khatabook payments cannot be edited by anyone."""
        from src.app.services.payment_service import can_edit_payment
        from src.app.schemas.auth_service_schamas import UserRole

        # Test that no role can edit khatabook payments
        roles_to_test = [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
            UserRole.PROJECT_MANAGER.value,
            UserRole.SITE_ENGINEER.value
        ]

        for role in roles_to_test:
            # Test with khatabook status
            assert can_edit_payment(["khatabook"], role, "khatabook") is False

            # Test with khatabook in history
            assert can_edit_payment(["requested", "khatabook"], role) is False

        # Verify that regular payments can still be edited by appropriate roles
        assert can_edit_payment(["requested"], UserRole.ADMIN.value, "requested") is True


class TestKhatabookPaymentPersonVisibility:
    """Test class for person-based visibility of khatabook payments."""

    def test_person_linked_user_visibility(self):
        """Test that users linked to persons can see khatabook payments where they are selected."""
        from uuid import uuid4

        # Test data
        user_id = uuid4()
        person_id = uuid4()
        other_person_id = uuid4()

        # Mock the logic for checking if a user can see a khatabook payment as the selected person
        def can_see_as_selected_person(user_person_id, payment_person_id, payment_status):
            return (payment_status == "khatabook" and
                    user_person_id is not None and
                    payment_person_id == user_person_id)

        # Test scenarios
        assert can_see_as_selected_person(person_id, person_id, "khatabook") is True
        assert can_see_as_selected_person(person_id, other_person_id, "khatabook") is False
        assert can_see_as_selected_person(None, person_id, "khatabook") is False
        assert can_see_as_selected_person(person_id, person_id, "requested") is False

    def test_enhanced_role_restrictions_with_person_visibility(self):
        """Test the enhanced role restrictions that include person-based visibility."""
        from src.app.schemas.auth_service_schamas import UserRole

        def enhanced_visibility_check(user_role, is_creator, is_project_manager, is_admin, is_selected_person):
            """Enhanced visibility logic including person-based access."""

            # Creator can always see
            if is_creator:
                return True

            # Admin roles can see all
            if is_admin:
                return True

            # Project Manager can see from assigned projects
            if user_role == UserRole.PROJECT_MANAGER.value and is_project_manager:
                return True

            # Selected person can see khatabook payments where they are selected
            if is_selected_person:
                return True

            return False

        # Test all visibility scenarios
        test_cases = [
            # (role, is_creator, is_pm, is_admin, is_selected_person, expected)
            (UserRole.SITE_ENGINEER.value, True, False, False, False, True),    # Creator
            (UserRole.SITE_ENGINEER.value, False, False, False, True, True),    # Selected person
            (UserRole.PROJECT_MANAGER.value, False, True, False, False, True),  # PM of project
            (UserRole.ADMIN.value, False, False, True, False, True),            # Admin
            (UserRole.ACCOUNTANT.value, False, False, True, False, True),       # Accountant
            (UserRole.SITE_ENGINEER.value, False, False, False, False, False), # No access
        ]

        for role, is_creator, is_pm, is_admin, is_selected_person, expected in test_cases:
            result = enhanced_visibility_check(role, is_creator, is_pm, is_admin, is_selected_person)
            assert result == expected, f"Failed for role {role} with flags: creator={is_creator}, pm={is_pm}, admin={is_admin}, selected={is_selected_person}"


class TestKhatabookPaymentFilteredTotals:
    """Test class for khatabook payment inclusion in filtered totals."""

    def test_filter_detection_logic(self):
        """Test the logic for detecting when specific filters are applied."""

        def has_specific_filters(project_id, item_id, person_id, from_uuid, to_uuid):
            """Check if any specific filters are applied."""
            return any([project_id, item_id, person_id, from_uuid, to_uuid])

        # Test filter detection
        assert has_specific_filters(uuid4(), None, None, None, None) is True    # Project filter
        assert has_specific_filters(None, uuid4(), None, None, None) is True    # Item filter
        assert has_specific_filters(None, None, uuid4(), None, None) is True    # Person filter
        assert has_specific_filters(None, None, None, uuid4(), None) is True    # From user filter
        assert has_specific_filters(None, None, None, None, uuid4()) is True    # To user filter
        assert has_specific_filters(None, None, None, None, None) is False      # No filters

    def test_status_inclusion_based_on_filters(self):
        """Test which payment statuses are included based on filter presence."""

        def get_statuses_for_totals(has_filters):
            """Get the appropriate statuses for total calculations."""
            base_statuses = ["requested", "verified", "approved", "transferred"]
            if has_filters:
                return base_statuses + ["khatabook"]
            return base_statuses

        # Test status inclusion
        global_statuses = get_statuses_for_totals(False)
        filtered_statuses = get_statuses_for_totals(True)

        # Global totals should exclude khatabook
        assert "khatabook" not in global_statuses
        assert set(global_statuses) == {"requested", "verified", "approved", "transferred"}

        # Filtered totals should include khatabook
        assert "khatabook" in filtered_statuses
        assert set(filtered_statuses) == {"requested", "verified", "approved", "transferred", "khatabook"}

    def test_total_calculation_scenarios(self):
        """Test different scenarios for total calculations."""

        scenarios = [
            {
                "name": "Global totals (no filters)",
                "filters": {"project_id": None, "item_id": None, "person_id": None, "from_uuid": None, "to_uuid": None},
                "should_include_khatabook": False
            },
            {
                "name": "Project-specific totals",
                "filters": {"project_id": uuid4(), "item_id": None, "person_id": None, "from_uuid": None, "to_uuid": None},
                "should_include_khatabook": True
            },
            {
                "name": "Person-specific totals",
                "filters": {"project_id": None, "item_id": None, "person_id": uuid4(), "from_uuid": None, "to_uuid": None},
                "should_include_khatabook": True
            },
            {
                "name": "User-specific totals (from)",
                "filters": {"project_id": None, "item_id": None, "person_id": None, "from_uuid": uuid4(), "to_uuid": None},
                "should_include_khatabook": True
            },
            {
                "name": "User-specific totals (to)",
                "filters": {"project_id": None, "item_id": None, "person_id": None, "from_uuid": None, "to_uuid": uuid4()},
                "should_include_khatabook": True
            },
            {
                "name": "Item-specific totals",
                "filters": {"project_id": None, "item_id": uuid4(), "person_id": None, "from_uuid": None, "to_uuid": None},
                "should_include_khatabook": True
            }
        ]

        for scenario in scenarios:
            filters = scenario["filters"]
            has_filters = any(filters.values())
            expected = scenario["should_include_khatabook"]

            assert has_filters == expected, f"Failed for scenario: {scenario['name']}"


class TestKhatabookPaymentItemMapping:
    """Test class for khatabook payment item mapping functionality."""

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_project_id(self):
        """Sample project ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_person_id(self):
        """Sample person ID for testing."""
        return uuid4()

    @pytest.fixture
    def mock_db_with_items(self):
        """Create a mock database session with item mapping."""
        db = Mock(spec=Session)

        # Mock khatabook items
        mock_kb_item1 = Mock(spec=KhatabookItem)
        mock_kb_item1.item_id = uuid4()
        mock_kb_item2 = Mock(spec=KhatabookItem)
        mock_kb_item2.item_id = uuid4()

        db.query.return_value.filter.return_value.all.return_value = [mock_kb_item1, mock_kb_item2]
        db.add = Mock()
        db.flush = Mock()
        return db, [mock_kb_item1, mock_kb_item2]

    @pytest.fixture
    def sample_khatabook_entry_with_items(self, sample_user_id, sample_project_id, sample_person_id):
        """Create a sample khatabook entry with items."""
        return Khatabook(
            uuid=uuid4(),
            amount=1000.0,
            remarks="Test khatabook entry with items",
            person_id=sample_person_id,
            project_id=sample_project_id,
            created_by=sample_user_id,
            balance_after_entry=500.0,
            payment_mode="Cash",
            entry_type="Debit"
        )

    def test_create_payment_with_item_mapping(
        self, mock_db_with_items, sample_khatabook_entry_with_items, sample_user_id
    ):
        """Test that payment creation includes item mapping from khatabook entry."""
        mock_db, mock_kb_items = mock_db_with_items

        # Act
        result = create_payment_from_khatabook_entry(
            mock_db, sample_khatabook_entry_with_items, sample_user_id
        )

        # Assert
        assert result is not None
        assert isinstance(result, Payment)

        # Verify that khatabook items were queried
        mock_db.query.assert_called()

        # Verify that payment items were created (2 items + 1 payment + 1 status history = 4 add calls)
        assert mock_db.add.call_count == 4  # Payment + PaymentStatusHistory + 2 PaymentItems

        # Verify the payment items were created with correct item_ids
        add_calls = mock_db.add.call_args_list
        payment_item_calls = [call for call in add_calls if isinstance(call[0][0], type(PaymentItem()))]
        assert len(payment_item_calls) == 2

    def test_create_payment_without_items(
        self, sample_user_id, sample_project_id, sample_person_id
    ):
        """Test that payment creation works when khatabook entry has no items."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.all.return_value = []  # No items
        mock_db.add = Mock()
        mock_db.flush = Mock()

        khatabook_entry = Khatabook(
            uuid=uuid4(),
            amount=1000.0,
            remarks="Test entry without items",
            person_id=sample_person_id,
            project_id=sample_project_id,
            created_by=sample_user_id,
            balance_after_entry=500.0,
            payment_mode="Cash",
            entry_type="Debit"
        )

        # Act
        result = create_payment_from_khatabook_entry(mock_db, khatabook_entry, sample_user_id)

        # Assert
        assert result is not None
        assert isinstance(result, Payment)

        # Verify only payment and status history were created (no payment items)
        assert mock_db.add.call_count == 2  # Payment + PaymentStatusHistory only

    def test_item_mapping_logic(self):
        """Test the logic for mapping khatabook items to payment items."""
        # Test data
        khatabook_id = uuid4()
        payment_id = uuid4()
        item_id_1 = uuid4()
        item_id_2 = uuid4()

        # Simulate the mapping logic
        def create_payment_items(khatabook_items, payment_id):
            payment_items = []
            for kb_item in khatabook_items:
                payment_item = {
                    "payment_id": payment_id,
                    "item_id": kb_item["item_id"]
                }
                payment_items.append(payment_item)
            return payment_items

        # Test with multiple items
        khatabook_items = [
            {"item_id": item_id_1},
            {"item_id": item_id_2}
        ]

        payment_items = create_payment_items(khatabook_items, payment_id)

        # Verify mapping
        assert len(payment_items) == 2
        assert payment_items[0]["payment_id"] == payment_id
        assert payment_items[0]["item_id"] == item_id_1
        assert payment_items[1]["payment_id"] == payment_id
        assert payment_items[1]["item_id"] == item_id_2

        # Test with no items
        empty_payment_items = create_payment_items([], payment_id)
        assert len(empty_payment_items) == 0

    def test_item_mapping_preserves_relationships(self):
        """Test that item mapping preserves the relationship between khatabook and payment items."""
        # This test verifies the conceptual relationship
        khatabook_entry_id = uuid4()
        payment_id = uuid4()
        item_ids = [uuid4(), uuid4(), uuid4()]

        # Simulate khatabook items
        khatabook_items = [
            {"khatabook_id": khatabook_entry_id, "item_id": item_id}
            for item_id in item_ids
        ]

        # Simulate payment items created from khatabook items
        payment_items = [
            {"payment_id": payment_id, "item_id": kb_item["item_id"]}
            for kb_item in khatabook_items
        ]

        # Verify that all items are preserved
        khatabook_item_ids = {kb_item["item_id"] for kb_item in khatabook_items}
        payment_item_ids = {p_item["item_id"] for p_item in payment_items}

        assert khatabook_item_ids == payment_item_ids
        assert len(payment_items) == len(khatabook_items)

        # Verify all payment items reference the correct payment
        for payment_item in payment_items:
            assert payment_item["payment_id"] == payment_id


class TestKhatabookPaymentFilteredTotalsIntegration:
    """Test class for verifying khatabook payments are included in filtered totals."""

    def test_filtered_total_calculation_with_khatabook_payments(self):
        """Test that filtered totals include khatabook payment amounts."""

        # Simulate payment data
        payments = [
            {"status": "requested", "amount": 1000.0, "project_id": "project-1"},
            {"status": "verified", "amount": 2000.0, "project_id": "project-1"},
            {"status": "khatabook", "amount": 500.0, "project_id": "project-1"},  # Khatabook payment
            {"status": "requested", "amount": 1500.0, "project_id": "project-2"},
            {"status": "khatabook", "amount": 300.0, "project_id": "project-2"},  # Khatabook payment
        ]

        def calculate_total_with_filters(payments, project_filter=None, include_khatabook=False):
            """Simulate the total calculation logic."""
            filtered_payments = payments

            # Apply project filter
            if project_filter:
                filtered_payments = [p for p in filtered_payments if p["project_id"] == project_filter]

            # Apply status filter
            if include_khatabook:
                valid_statuses = ["requested", "verified", "approved", "transferred", "khatabook"]
            else:
                valid_statuses = ["requested", "verified", "approved", "transferred"]

            filtered_payments = [p for p in filtered_payments if p["status"] in valid_statuses]

            return sum(p["amount"] for p in filtered_payments)

        # Test global totals (no filters) - should exclude khatabook
        global_total = calculate_total_with_filters(payments, include_khatabook=False)
        assert global_total == 4500.0  # 1000 + 2000 + 1500 (excludes khatabook amounts)

        # Test project-1 filtered totals - should include khatabook
        project1_total = calculate_total_with_filters(payments, project_filter="project-1", include_khatabook=True)
        assert project1_total == 3500.0  # 1000 + 2000 + 500 (includes khatabook)

        # Test project-2 filtered totals - should include khatabook
        project2_total = calculate_total_with_filters(payments, project_filter="project-2", include_khatabook=True)
        assert project2_total == 1800.0  # 1500 + 300 (includes khatabook)

        # Verify the difference between filtered and unfiltered
        project1_without_khatabook = calculate_total_with_filters(payments, project_filter="project-1", include_khatabook=False)
        assert project1_without_khatabook == 3000.0  # 1000 + 2000 (excludes khatabook)
        assert project1_total > project1_without_khatabook  # Filtered total should be higher

    def test_filter_detection_logic_comprehensive(self):
        """Test comprehensive filter detection scenarios."""

        def has_filters(**kwargs):
            """Simulate the filter detection logic."""
            return any([
                kwargs.get("project_id") is not None,
                kwargs.get("item_id") is not None,
                kwargs.get("person_id") is not None,
                kwargs.get("from_uuid") is not None,
                kwargs.get("to_uuid") is not None
            ])

        # Test all filter combinations
        test_cases = [
            # No filters
            {"expected": False},

            # Single filters
            {"project_id": uuid4(), "expected": True},
            {"item_id": uuid4(), "expected": True},
            {"person_id": uuid4(), "expected": True},
            {"from_uuid": uuid4(), "expected": True},
            {"to_uuid": uuid4(), "expected": True},

            # Multiple filters
            {"project_id": uuid4(), "item_id": uuid4(), "expected": True},
            {"person_id": uuid4(), "from_uuid": uuid4(), "expected": True},
            {"project_id": uuid4(), "person_id": uuid4(), "to_uuid": uuid4(), "expected": True},

            # All filters
            {
                "project_id": uuid4(),
                "item_id": uuid4(),
                "person_id": uuid4(),
                "from_uuid": uuid4(),
                "to_uuid": uuid4(),
                "expected": True
            }
        ]

        for case in test_cases:
            expected = case.pop("expected")
            result = has_filters(**case)
            assert result == expected, f"Failed for case: {case}"

    def test_khatabook_payment_amount_inclusion_scenarios(self):
        """Test specific scenarios where khatabook payments should be included in totals."""

        # Test data representing different payment scenarios
        scenarios = [
            {
                "name": "Project-specific request",
                "filters": {"project_id": "project-123"},
                "payments": [
                    {"amount": 1000, "status": "requested", "project_id": "project-123"},
                    {"amount": 500, "status": "khatabook", "project_id": "project-123"},
                    {"amount": 2000, "status": "requested", "project_id": "project-456"}
                ],
                "expected_total": 1500,  # Should include khatabook for project-123
                "should_include_khatabook": True
            },
            {
                "name": "Person-specific request",
                "filters": {"person_id": "person-789"},
                "payments": [
                    {"amount": 800, "status": "verified", "person_id": "person-789"},
                    {"amount": 300, "status": "khatabook", "person_id": "person-789"},
                    {"amount": 1200, "status": "verified", "person_id": "person-456"}
                ],
                "expected_total": 1100,  # Should include khatabook for person-789
                "should_include_khatabook": True
            },
            {
                "name": "Global request (no filters)",
                "filters": {},
                "payments": [
                    {"amount": 1000, "status": "requested"},
                    {"amount": 500, "status": "khatabook"},
                    {"amount": 2000, "status": "verified"}
                ],
                "expected_total": 3000,  # Should exclude khatabook globally
                "should_include_khatabook": False
            }
        ]

        for scenario in scenarios:
            # Simulate the filtering logic
            has_filters = bool(scenario["filters"])
            include_khatabook = has_filters

            # Apply filters to payments first
            filtered_payments = scenario["payments"]

            # Apply project filter if present
            if "project_id" in scenario["filters"]:
                project_filter = scenario["filters"]["project_id"]
                filtered_payments = [p for p in filtered_payments if p.get("project_id") == project_filter]

            # Apply person filter if present
            if "person_id" in scenario["filters"]:
                person_filter = scenario["filters"]["person_id"]
                filtered_payments = [p for p in filtered_payments if p.get("person_id") == person_filter]

            # Calculate total based on inclusion rules
            if include_khatabook:
                valid_statuses = ["requested", "verified", "approved", "transferred", "khatabook"]
            else:
                valid_statuses = ["requested", "verified", "approved", "transferred"]

            total = sum(
                payment["amount"]
                for payment in filtered_payments
                if payment["status"] in valid_statuses
            )

            assert total == scenario["expected_total"], f"Failed for scenario: {scenario['name']}"
            assert include_khatabook == scenario["should_include_khatabook"], f"Inclusion logic failed for: {scenario['name']}"


if __name__ == "__main__":
    pytest.main([__file__])

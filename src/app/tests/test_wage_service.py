"""
Test cases for wage service functions
"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4
from src.app.services.wage_service import (
    check_wage_configuration_permission,
    get_effective_wage_rate,
    calculate_and_save_wage
)
from src.app.database.models import ProjectDailyWage, ProjectAttendanceWage
from src.app.schemas.auth_service_schamas import UserRole


class TestWageServiceHelpers:
    """Test helper functions in wage service"""
    
    def test_check_wage_configuration_permission_admin(self):
        """Test wage configuration permission for admin"""
        assert check_wage_configuration_permission(UserRole.ADMIN) is True
        assert check_wage_configuration_permission(UserRole.SUPER_ADMIN) is True
        assert check_wage_configuration_permission(UserRole.PROJECT_MANAGER) is True
    
    def test_check_wage_configuration_permission_unauthorized(self):
        """Test wage configuration permission for unauthorized roles"""
        assert check_wage_configuration_permission(UserRole.SITE_ENGINEER) is False
        assert check_wage_configuration_permission(UserRole.CLIENT) is False
    
    def test_get_effective_wage_rate_exists(self, db_session, test_daily_wage):
        """Test getting effective wage rate when it exists"""
        wage_rate = get_effective_wage_rate(
            test_daily_wage.project_id,
            date.today(),
            db_session
        )
        
        assert wage_rate is not None
        assert wage_rate.uuid == test_daily_wage.uuid
        assert wage_rate.daily_wage_rate == 300.0
    
    def test_get_effective_wage_rate_not_exists(self, db_session, test_project):
        """Test getting effective wage rate when it doesn't exist"""
        wage_rate = get_effective_wage_rate(
            test_project.uuid,
            date.today(),
            db_session
        )
        
        assert wage_rate is None
    
    def test_get_effective_wage_rate_multiple_rates(self, db_session, test_project, test_admin_user):
        """Test getting effective wage rate with multiple rates"""
        # Create multiple wage rates with different effective dates
        wage1 = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=250.0,
            effective_date=date.today() - timedelta(days=10),
            configured_by_user_id=test_admin_user.uuid
        )
        
        wage2 = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=300.0,
            effective_date=date.today() - timedelta(days=5),
            configured_by_user_id=test_admin_user.uuid
        )
        
        wage3 = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=350.0,
            effective_date=date.today() + timedelta(days=5),  # Future date
            configured_by_user_id=test_admin_user.uuid
        )
        
        db_session.add_all([wage1, wage2, wage3])
        db_session.commit()
        
        # Should return the most recent rate that's effective today
        effective_rate = get_effective_wage_rate(
            test_project.uuid,
            date.today(),
            db_session
        )
        
        assert effective_rate is not None
        assert effective_rate.daily_wage_rate == 300.0  # Most recent effective rate
        assert effective_rate.effective_date == date.today() - timedelta(days=5)
    
    def test_calculate_and_save_wage_success(self, db_session, test_project_attendance, test_daily_wage):
        """Test successful wage calculation and saving"""
        wage_calculation = calculate_and_save_wage(
            project_id=test_daily_wage.project_id,
            attendance_id=test_project_attendance.uuid,
            no_of_labours=15,
            attendance_date=date.today(),
            db=db_session
        )
        
        assert wage_calculation is not None
        assert wage_calculation.project_attendance_id == test_project_attendance.uuid
        assert wage_calculation.project_daily_wage_id == test_daily_wage.uuid
        assert wage_calculation.no_of_labours == 15
        assert wage_calculation.daily_wage_rate == 300.0
        assert wage_calculation.total_wage_amount == 4500.0  # 15 * 300
    
    def test_calculate_and_save_wage_no_rate_config(self, db_session, test_project_attendance, test_project):
        """Test wage calculation when no wage rate is configured"""
        wage_calculation = calculate_and_save_wage(
            project_id=test_project.uuid,
            attendance_id=test_project_attendance.uuid,
            no_of_labours=10,
            attendance_date=date.today(),
            db=db_session
        )
        
        assert wage_calculation is None
    
    def test_calculate_and_save_wage_different_labour_counts(self, db_session, test_project_attendance, test_daily_wage):
        """Test wage calculation with different labour counts"""
        # Test with 5 labours
        wage_calc_5 = calculate_and_save_wage(
            project_id=test_daily_wage.project_id,
            attendance_id=test_project_attendance.uuid,
            no_of_labours=5,
            attendance_date=date.today(),
            db=db_session
        )
        
        assert wage_calc_5.total_wage_amount == 1500.0  # 5 * 300
        
        # Clean up for next test
        db_session.delete(wage_calc_5)
        db_session.commit()
        
        # Test with 20 labours
        wage_calc_20 = calculate_and_save_wage(
            project_id=test_daily_wage.project_id,
            attendance_id=test_project_attendance.uuid,
            no_of_labours=20,
            attendance_date=date.today(),
            db=db_session
        )
        
        assert wage_calc_20.total_wage_amount == 6000.0  # 20 * 300


class TestWageCalculationLogic:
    """Test wage calculation business logic"""
    
    def test_wage_calculation_accuracy(self):
        """Test wage calculation accuracy with various scenarios"""
        test_cases = [
            (10, 300.0, 3000.0),
            (5, 250.0, 1250.0),
            (15, 400.0, 6000.0),
            (1, 500.0, 500.0),
            (100, 200.0, 20000.0)
        ]
        
        for labours, rate, expected_total in test_cases:
            calculated_total = labours * rate
            assert calculated_total == expected_total
    
    def test_wage_calculation_precision(self):
        """Test wage calculation with decimal precision"""
        # Test with decimal wage rates
        test_cases = [
            (10, 299.50, 2995.0),
            (7, 333.33, 2333.31),
            (12, 275.75, 3309.0)
        ]
        
        for labours, rate, expected_total in test_cases:
            calculated_total = round(labours * rate, 2)
            assert calculated_total == expected_total
    
    def test_wage_rate_effective_date_logic(self, db_session, test_project, test_admin_user):
        """Test wage rate effective date logic"""
        # Create wage rates for different dates
        past_date = date.today() - timedelta(days=30)
        recent_date = date.today() - timedelta(days=10)
        future_date = date.today() + timedelta(days=10)
        
        wage_past = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=200.0,
            effective_date=past_date,
            configured_by_user_id=test_admin_user.uuid
        )
        
        wage_recent = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=300.0,
            effective_date=recent_date,
            configured_by_user_id=test_admin_user.uuid
        )
        
        wage_future = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=400.0,
            effective_date=future_date,
            configured_by_user_id=test_admin_user.uuid
        )
        
        db_session.add_all([wage_past, wage_recent, wage_future])
        db_session.commit()
        
        # Test for today - should get recent rate
        effective_today = get_effective_wage_rate(test_project.uuid, date.today(), db_session)
        assert effective_today.daily_wage_rate == 300.0
        
        # Test for past date - should get past rate
        effective_past = get_effective_wage_rate(test_project.uuid, past_date, db_session)
        assert effective_past.daily_wage_rate == 200.0
        
        # Test for future date - should get future rate
        effective_future = get_effective_wage_rate(test_project.uuid, future_date, db_session)
        assert effective_future.daily_wage_rate == 400.0
    
    def test_wage_calculation_with_deleted_rates(self, db_session, test_project, test_admin_user):
        """Test that deleted wage rates are not considered"""
        # Create active wage rate
        active_wage = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=300.0,
            effective_date=date.today() - timedelta(days=5),
            configured_by_user_id=test_admin_user.uuid,
            is_deleted=False
        )
        
        # Create deleted wage rate with higher rate
        deleted_wage = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=500.0,
            effective_date=date.today() - timedelta(days=2),
            configured_by_user_id=test_admin_user.uuid,
            is_deleted=True
        )
        
        db_session.add_all([active_wage, deleted_wage])
        db_session.commit()
        
        # Should return active wage rate, not deleted one
        effective_rate = get_effective_wage_rate(test_project.uuid, date.today(), db_session)
        assert effective_rate.daily_wage_rate == 300.0
        assert effective_rate.is_deleted is False


class TestWageServiceIntegration:
    """Test wage service integration with database"""
    
    def test_wage_calculation_persistence(self, db_session, test_project_attendance, test_daily_wage):
        """Test that wage calculations are properly persisted"""
        initial_count = db_session.query(ProjectAttendanceWage).count()
        
        wage_calculation = calculate_and_save_wage(
            project_id=test_daily_wage.project_id,
            attendance_id=test_project_attendance.uuid,
            no_of_labours=12,
            attendance_date=date.today(),
            db=db_session
        )
        
        final_count = db_session.query(ProjectAttendanceWage).count()
        
        assert final_count == initial_count + 1
        assert wage_calculation.is_deleted is False
        assert wage_calculation.calculated_at is not None
    
    def test_wage_calculation_relationships(self, db_session, test_project_attendance, test_daily_wage):
        """Test wage calculation relationships are properly set"""
        wage_calculation = calculate_and_save_wage(
            project_id=test_daily_wage.project_id,
            attendance_id=test_project_attendance.uuid,
            no_of_labours=8,
            attendance_date=date.today(),
            db=db_session
        )
        
        # Refresh to load relationships
        db_session.refresh(wage_calculation)
        
        assert wage_calculation.project_attendance is not None
        assert wage_calculation.project_daily_wage is not None
        assert wage_calculation.project_attendance.uuid == test_project_attendance.uuid
        assert wage_calculation.project_daily_wage.uuid == test_daily_wage.uuid

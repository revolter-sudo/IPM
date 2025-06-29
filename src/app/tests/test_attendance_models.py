"""
Test cases for attendance and wage management models
"""

import pytest
from datetime import datetime, date, timedelta
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from src.app.database.models import (
    SelfAttendance, ProjectAttendance, ProjectDailyWage, ProjectAttendanceWage
)


class TestSelfAttendanceModel:
    """Test cases for SelfAttendance model"""
    
    def test_create_self_attendance(self, db_session, test_user):
        """Test creating a self attendance record"""
        attendance = SelfAttendance(
            uuid=uuid4(),
            user_id=test_user.uuid,
            attendance_date=date.today(),
            punch_in_time=datetime.now(),
            punch_in_latitude=28.6139,
            punch_in_longitude=77.2090,
            punch_in_location_address="Test Location",
            assigned_projects='[{"uuid": "test-uuid", "name": "Test Project"}]'
        )
        
        db_session.add(attendance)
        db_session.commit()
        db_session.refresh(attendance)
        
        assert attendance.id is not None
        assert attendance.user_id == test_user.uuid
        assert attendance.attendance_date == date.today()
        assert attendance.punch_in_latitude == 28.6139
        assert attendance.punch_in_longitude == 77.2090
        assert attendance.punch_out_time is None
        assert attendance.is_deleted is False
    
    def test_self_attendance_with_punch_out(self, db_session, test_user):
        """Test self attendance with punch out"""
        punch_in_time = datetime.now()
        punch_out_time = punch_in_time + timedelta(hours=8)
        
        attendance = SelfAttendance(
            uuid=uuid4(),
            user_id=test_user.uuid,
            attendance_date=date.today(),
            punch_in_time=punch_in_time,
            punch_in_latitude=28.6139,
            punch_in_longitude=77.2090,
            punch_out_time=punch_out_time,
            punch_out_latitude=28.6140,
            punch_out_longitude=77.2091
        )
        
        db_session.add(attendance)
        db_session.commit()
        db_session.refresh(attendance)
        
        assert attendance.punch_out_time == punch_out_time
        assert attendance.punch_out_latitude == 28.6140
        assert attendance.punch_out_longitude == 77.2091
    
    def test_self_attendance_unique_constraint(self, db_session, test_user):
        """Test unique constraint on user_id, attendance_date, is_deleted"""
        # Create first attendance
        attendance1 = SelfAttendance(
            uuid=uuid4(),
            user_id=test_user.uuid,
            attendance_date=date.today(),
            punch_in_time=datetime.now(),
            punch_in_latitude=28.6139,
            punch_in_longitude=77.2090
        )
        db_session.add(attendance1)
        db_session.commit()
        
        # Try to create duplicate attendance for same user and date
        attendance2 = SelfAttendance(
            uuid=uuid4(),
            user_id=test_user.uuid,
            attendance_date=date.today(),
            punch_in_time=datetime.now(),
            punch_in_latitude=28.6140,
            punch_in_longitude=77.2091
        )
        db_session.add(attendance2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_self_attendance_repr(self, db_session, test_user):
        """Test string representation of SelfAttendance"""
        attendance = SelfAttendance(
            uuid=uuid4(),
            user_id=test_user.uuid,
            attendance_date=date.today(),
            punch_in_time=datetime.now(),
            punch_in_latitude=28.6139,
            punch_in_longitude=77.2090
        )
        
        repr_str = repr(attendance)
        assert "SelfAttendance" in repr_str
        assert str(test_user.uuid) in repr_str
        assert str(date.today()) in repr_str


class TestProjectAttendanceModel:
    """Test cases for ProjectAttendance model"""
    
    def test_create_project_attendance(self, db_session, test_user, test_project, test_person):
        """Test creating a project attendance record"""
        attendance = ProjectAttendance(
            uuid=uuid4(),
            site_engineer_id=test_user.uuid,
            project_id=test_project.uuid,
            sub_contractor_id=test_person.uuid,
            no_of_labours=10,
            attendance_date=date.today(),
            marked_at=datetime.now(),
            latitude=28.6139,
            longitude=77.2090,
            location_address="Project Site",
            notes="Test attendance"
        )
        
        db_session.add(attendance)
        db_session.commit()
        db_session.refresh(attendance)
        
        assert attendance.id is not None
        assert attendance.site_engineer_id == test_user.uuid
        assert attendance.project_id == test_project.uuid
        assert attendance.sub_contractor_id == test_person.uuid
        assert attendance.no_of_labours == 10
        assert attendance.attendance_date == date.today()
        assert attendance.is_deleted is False
    
    def test_project_attendance_positive_labours_constraint(self, db_session, test_user, test_project, test_person):
        """Test that no_of_labours must be positive"""
        attendance = ProjectAttendance(
            uuid=uuid4(),
            site_engineer_id=test_user.uuid,
            project_id=test_project.uuid,
            sub_contractor_id=test_person.uuid,
            no_of_labours=0,  # Invalid: should be positive
            attendance_date=date.today(),
            marked_at=datetime.now(),
            latitude=28.6139,
            longitude=77.2090
        )
        
        db_session.add(attendance)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_project_attendance_relationships(self, db_session, test_project_attendance):
        """Test relationships in ProjectAttendance model"""
        attendance = test_project_attendance
        
        # Test relationships are properly loaded
        assert attendance.site_engineer is not None
        assert attendance.project is not None
        assert attendance.sub_contractor is not None
        assert attendance.site_engineer.name == "Test User"
        assert attendance.project.name == "Test Project"
        assert attendance.sub_contractor.name == "Test Contractor"


class TestProjectDailyWageModel:
    """Test cases for ProjectDailyWage model"""
    
    def test_create_daily_wage(self, db_session, test_project, test_admin_user):
        """Test creating a daily wage configuration"""
        wage = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=300.0,
            effective_date=date.today(),
            configured_by_user_id=test_admin_user.uuid
        )
        
        db_session.add(wage)
        db_session.commit()
        db_session.refresh(wage)
        
        assert wage.id is not None
        assert wage.project_id == test_project.uuid
        assert wage.daily_wage_rate == 300.0
        assert wage.effective_date == date.today()
        assert wage.configured_by_user_id == test_admin_user.uuid
        assert wage.is_deleted is False
    
    def test_daily_wage_positive_rate_constraint(self, db_session, test_project, test_admin_user):
        """Test that daily_wage_rate must be positive"""
        wage = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=0.0,  # Invalid: should be positive
            effective_date=date.today(),
            configured_by_user_id=test_admin_user.uuid
        )
        
        db_session.add(wage)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_daily_wage_unique_constraint(self, db_session, test_project, test_admin_user):
        """Test unique constraint on project_id, effective_date, is_deleted"""
        # Create first wage config
        wage1 = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=300.0,
            effective_date=date.today(),
            configured_by_user_id=test_admin_user.uuid
        )
        db_session.add(wage1)
        db_session.commit()
        
        # Try to create duplicate wage config for same project and date
        wage2 = ProjectDailyWage(
            uuid=uuid4(),
            project_id=test_project.uuid,
            daily_wage_rate=350.0,
            effective_date=date.today(),
            configured_by_user_id=test_admin_user.uuid
        )
        db_session.add(wage2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestProjectAttendanceWageModel:
    """Test cases for ProjectAttendanceWage model"""
    
    def test_create_wage_calculation(self, db_session, test_project_attendance, test_daily_wage):
        """Test creating a wage calculation"""
        wage_calc = ProjectAttendanceWage(
            uuid=uuid4(),
            project_attendance_id=test_project_attendance.uuid,
            project_daily_wage_id=test_daily_wage.uuid,
            no_of_labours=10,
            daily_wage_rate=300.0,
            total_wage_amount=3000.0,
            calculated_at=datetime.now()
        )
        
        db_session.add(wage_calc)
        db_session.commit()
        db_session.refresh(wage_calc)
        
        assert wage_calc.id is not None
        assert wage_calc.project_attendance_id == test_project_attendance.uuid
        assert wage_calc.project_daily_wage_id == test_daily_wage.uuid
        assert wage_calc.no_of_labours == 10
        assert wage_calc.daily_wage_rate == 300.0
        assert wage_calc.total_wage_amount == 3000.0
        assert wage_calc.is_deleted is False
    
    def test_wage_calculation_unique_constraint(self, db_session, test_project_attendance, test_daily_wage):
        """Test unique constraint on project_attendance_id, is_deleted"""
        # Create first wage calculation
        wage_calc1 = ProjectAttendanceWage(
            uuid=uuid4(),
            project_attendance_id=test_project_attendance.uuid,
            project_daily_wage_id=test_daily_wage.uuid,
            no_of_labours=10,
            daily_wage_rate=300.0,
            total_wage_amount=3000.0,
            calculated_at=datetime.now()
        )
        db_session.add(wage_calc1)
        db_session.commit()
        
        # Try to create duplicate wage calculation for same attendance
        wage_calc2 = ProjectAttendanceWage(
            uuid=uuid4(),
            project_attendance_id=test_project_attendance.uuid,
            project_daily_wage_id=test_daily_wage.uuid,
            no_of_labours=15,
            daily_wage_rate=300.0,
            total_wage_amount=4500.0,
            calculated_at=datetime.now()
        )
        db_session.add(wage_calc2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_wage_calculation_relationships(self, db_session, test_wage_calculation):
        """Test relationships in ProjectAttendanceWage model"""
        wage_calc = test_wage_calculation
        
        # Test relationships are properly loaded
        assert wage_calc.project_attendance is not None
        assert wage_calc.project_daily_wage is not None
        assert wage_calc.project_attendance.no_of_labours == 10
        assert wage_calc.project_daily_wage.daily_wage_rate == 300.0

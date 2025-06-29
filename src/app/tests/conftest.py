"""
Test configuration and fixtures for attendance and wage management module
"""

import pytest
import os
from datetime import datetime, date, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from src.app.database.database import Base, get_db
from src.app.database.models import (
    User, Project, Person, ProjectUserMap,
    SelfAttendance, ProjectAttendance, ProjectDailyWage, ProjectAttendanceWage
)
from src.app.main import app
from src.app.services.auth_service import get_password_hash, create_access_token


# Test database URL - use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test_attendance.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def test_db():
    """Create test database and tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    """Create a fresh database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database dependency override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        uuid=uuid4(),
        name="Test User",
        phone=9876543210,
        password_hash=get_password_hash("testpassword"),
        role="SiteEngineer",
        is_deleted=False,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin_user(db_session):
    """Create a test admin user"""
    user = User(
        uuid=uuid4(),
        name="Test Admin",
        phone=9876543211,
        password_hash=get_password_hash("adminpassword"),
        role="Admin",
        is_deleted=False,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_project(db_session):
    """Create a test project"""
    project = Project(
        uuid=uuid4(),
        name="Test Project",
        description="A test project for attendance",
        location="Test Location",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        estimated_balance=100000.0,
        actual_balance=0.0,
        is_deleted=False
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_person(db_session):
    """Create a test person (sub-contractor)"""
    person = Person(
        uuid=uuid4(),
        name="Test Contractor",
        account_number="1234567890123456",
        ifsc_code="TEST0001234",
        phone_number="9876543212",
        is_deleted=False
    )
    db_session.add(person)
    db_session.commit()
    db_session.refresh(person)
    return person


@pytest.fixture
def test_project_user_map(db_session, test_user, test_project):
    """Create a project-user mapping"""
    mapping = ProjectUserMap(
        uuid=uuid4(),
        user_id=test_user.uuid,
        project_id=test_project.uuid,
        is_deleted=False
    )
    db_session.add(mapping)
    db_session.commit()
    db_session.refresh(mapping)
    return mapping


@pytest.fixture
def test_daily_wage(db_session, test_project, test_admin_user):
    """Create a test daily wage configuration"""
    wage = ProjectDailyWage(
        uuid=uuid4(),
        project_id=test_project.uuid,
        daily_wage_rate=300.0,
        effective_date=date.today(),
        configured_by_user_id=test_admin_user.uuid,
        is_deleted=False
    )
    db_session.add(wage)
    db_session.commit()
    db_session.refresh(wage)
    return wage


@pytest.fixture
def test_self_attendance(db_session, test_user):
    """Create a test self attendance record"""
    attendance = SelfAttendance(
        uuid=uuid4(),
        user_id=test_user.uuid,
        attendance_date=date.today(),
        punch_in_time=datetime.now(),
        punch_in_latitude=28.6139,
        punch_in_longitude=77.2090,
        punch_in_location_address="Test Location",
        assigned_projects='[{"uuid": "test-project-uuid", "name": "Test Project"}]',
        is_deleted=False
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(attendance)
    return attendance


@pytest.fixture
def test_project_attendance(db_session, test_user, test_project, test_person):
    """Create a test project attendance record"""
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
        notes="Test attendance",
        is_deleted=False
    )
    db_session.add(attendance)
    db_session.commit()
    db_session.refresh(attendance)
    return attendance


@pytest.fixture
def test_wage_calculation(db_session, test_project_attendance, test_daily_wage):
    """Create a test wage calculation"""
    wage_calc = ProjectAttendanceWage(
        uuid=uuid4(),
        project_attendance_id=test_project_attendance.uuid,
        project_daily_wage_id=test_daily_wage.uuid,
        no_of_labours=10,
        daily_wage_rate=300.0,
        total_wage_amount=3000.0,
        calculated_at=datetime.now(),
        is_deleted=False
    )
    db_session.add(wage_calc)
    db_session.commit()
    db_session.refresh(wage_calc)
    return wage_calc


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers for test user"""
    token = create_access_token(data={"sub": str(test_user.uuid)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_admin_user):
    """Create authentication headers for admin user"""
    token = create_access_token(data={"sub": str(test_admin_user.uuid)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_coordinates():
    """Sample valid coordinates for testing"""
    return {
        "valid": {
            "latitude": 28.6139,
            "longitude": 77.2090,
            "address": "New Delhi, India"
        },
        "invalid": {
            "latitude": 91.0,  # Invalid latitude
            "longitude": 181.0,  # Invalid longitude
            "address": "Invalid Location"
        }
    }


@pytest.fixture
def sample_attendance_data():
    """Sample attendance data for testing"""
    return {
        "punch_in": {
            "phone": 9876543210,
            "password": "testpassword",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "location_address": "Test Location"
        },
        "punch_out": {
            "phone": 9876543210,
            "password": "testpassword",
            "latitude": 28.6140,
            "longitude": 77.2091,
            "location_address": "Test Location"
        }
    }


@pytest.fixture
def sample_project_attendance_data(test_project, test_person):
    """Sample project attendance data for testing"""
    return {
        "project_id": str(test_project.uuid),
        "sub_contractor_id": str(test_person.uuid),
        "no_of_labours": 15,
        "latitude": 28.6139,
        "longitude": 77.2090,
        "location_address": "Project Site",
        "notes": "Test project attendance"
    }


@pytest.fixture
def sample_wage_data():
    """Sample wage configuration data for testing"""
    return {
        "create": {
            "daily_wage_rate": 350.0,
            "effective_date": str(date.today())
        },
        "update": {
            "daily_wage_rate": 400.0,
            "effective_date": str(date.today() + timedelta(days=1))
        }
    }

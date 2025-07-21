import os
import json
import traceback
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timedelta
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Body,
    status as h_status
)
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
from src.app.database.database import get_db
from src.app.database.models import (
    SelfAttendance,
    ProjectAttendance,
    ProjectDailyWage,
    ProjectAttendanceWage,
    User,
    Project,
    Person,
    ProjectUserMap,
    Log
)
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.attendance_schemas import (
    SelfAttendancePunchIn,
    SelfAttendancePunchOut,
    ProjectAttendanceCreate,
    AttendanceResponse,
    SelfAttendanceResponse,
    SelfAttendanceStatus,
    ProjectAttendanceResponse,
    AttendanceHistoryParams,
    ProjectAttendanceHistoryParams,
    AttendanceHistoryResponse,
    ProjectAttendanceHistoryResponse,
    LocationData,
    ProjectInfo,
    PersonInfo,
    WageCalculationInfo,
    UserInfo,
    ProjectAttendanceSummary,
    DailyAttendanceSummary
)
from src.app.services.auth_service import get_current_user, verify_password
from src.app.services.location_service import LocationService
from src.app.utils.logging_config import get_logger

logger = get_logger(__name__)

attendance_router = APIRouter()


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate latitude and longitude coordinates"""
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def get_user_assigned_projects(user_id: UUID, db: Session) -> List[dict]:
    """Get projects assigned to a user"""
    try:
        project_maps = db.query(ProjectUserMap).filter(
            ProjectUserMap.user_id == user_id,
            ProjectUserMap.is_deleted.is_(False)
        ).all()
        
        projects = []
        for pm in project_maps:
            project = db.query(Project).filter(
                Project.uuid == pm.project_id,
                Project.is_deleted.is_(False)
            ).first()
            if project:
                projects.append({
                    "uuid": str(project.uuid),
                    "name": project.name
                })
        
        return projects
    except Exception as e:
        logger.error(f"Error getting user assigned projects: {str(e)}")
        return []


def authenticate_user_credentials(phone: int, password: str, db: Session) -> Optional[User]:
    """Authenticate user with phone and password"""
    try:
        user = db.query(User).filter(
            User.phone == phone,
            User.is_deleted.is_(False),
            User.is_active.is_(True)
        ).first()
        
        if not user:
            return None
            
        if not verify_password(password, user.password_hash):
            return None
            
        return user
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        return None


def calculate_hours_worked(punch_in: datetime, punch_out: datetime) -> str:
    """Calculate hours worked between punch in and punch out"""
    try:
        if not punch_out:
            return None
        
        time_diff = punch_out - punch_in
        hours = time_diff.total_seconds() / 3600
        return f"{hours:.1f}"
    except Exception as e:
        logger.error(f"Error calculating hours worked: {str(e)}")
        return None


def get_current_hours_worked(punch_in: datetime) -> str:
    """Calculate current hours worked since punch in"""
    try:
        current_time = datetime.now()
        time_diff = current_time - punch_in
        hours = time_diff.total_seconds() / 3600
        return f"{hours:.1f}"
    except Exception as e:
        logger.error(f"Error calculating current hours: {str(e)}")
        return "0.0"


@attendance_router.post("/self/punch-in", tags=["Self Attendance"])
def punch_in_self_attendance(
    attendance_data: SelfAttendancePunchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark self attendance punch in for the current day.
    Requires phone/password authentication and location coordinates.
    """
    try:
        # Authenticate user credentials
        authenticated_user = authenticate_user_credentials(
            attendance_data.phone, 
            attendance_data.password, 
            db
        )
        
        if not authenticated_user:
            return AttendanceResponse(
                data=None,
                message="Invalid phone number or password",
                status_code=401
            ).to_dict()
        
        # Verify authenticated user matches JWT token user
        if authenticated_user.uuid != current_user.uuid:
            return AttendanceResponse(
                data=None,
                message="Authentication mismatch",
                status_code=403
            ).to_dict()
        
        # Validate coordinates
        if not validate_coordinates(attendance_data.latitude, attendance_data.longitude):
            return AttendanceResponse(
                data=None,
                message="Invalid coordinates provided",
                status_code=400
            ).to_dict()
        
        # Check if user already has attendance for today
        today = date.today()
        existing_attendance = db.query(SelfAttendance).filter(
            SelfAttendance.user_id == current_user.uuid,
            SelfAttendance.attendance_date == today,
            SelfAttendance.is_deleted.is_(False)
        ).first()
        
        if existing_attendance:
            return AttendanceResponse(
                data=None,
                message="Attendance already marked for today",
                status_code=400
            ).to_dict()
        
        # Get assigned projects
        assigned_projects = get_user_assigned_projects(current_user.uuid, db)
        
        # Create new attendance record
        new_attendance = SelfAttendance(
            user_id=current_user.uuid,
            attendance_date=today,
            punch_in_time=datetime.now(),
            punch_in_latitude=attendance_data.latitude,
            punch_in_longitude=attendance_data.longitude,
            punch_in_location_address=attendance_data.location_address,
            assigned_projects=json.dumps(assigned_projects) if assigned_projects else None
        )
        
        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)
        
        # Prepare response
        response_data = SelfAttendanceResponse(
            uuid=new_attendance.uuid,
            attendance_date=new_attendance.attendance_date,
            punch_in_time=new_attendance.punch_in_time,
            punch_in_location=LocationData(
                latitude=new_attendance.punch_in_latitude,
                longitude=new_attendance.punch_in_longitude,
                address=new_attendance.punch_in_location_address
            ),
            assigned_projects=[ProjectInfo(**proj) for proj in assigned_projects] if assigned_projects else []
        )
        
        # Log the action
        log_entry = Log(
            user_id=current_user.uuid,
            action="SELF_ATTENDANCE_PUNCH_IN",
            details=f"User {current_user.name} punched in at {new_attendance.punch_in_time}"
        )
        db.add(log_entry)
        db.commit()
        
        return AttendanceResponse(
            data=response_data.model_dump(),
            message="Punch in successful",
            status_code=201
        ).to_dict()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in punch_in_self_attendance: {str(e)}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()


@attendance_router.post("/self/punch-out", tags=["Self Attendance"])
def punch_out_self_attendance(
    attendance_data: SelfAttendancePunchOut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark self attendance punch out for the current day.
    Requires phone/password authentication and location coordinates.
    """
    try:
        # Authenticate user credentials
        authenticated_user = authenticate_user_credentials(
            attendance_data.phone, 
            attendance_data.password, 
            db
        )
        
        if not authenticated_user:
            return AttendanceResponse(
                data=None,
                message="Invalid phone number or password",
                status_code=401
            ).to_dict()
        
        # Verify authenticated user matches JWT token user
        if authenticated_user.uuid != current_user.uuid:
            return AttendanceResponse(
                data=None,
                message="Authentication mismatch",
                status_code=403
            ).to_dict()
        
        # Validate coordinates
        if not validate_coordinates(attendance_data.latitude, attendance_data.longitude):
            return AttendanceResponse(
                data=None,
                message="Invalid coordinates provided",
                status_code=400
            ).to_dict()
        
        # Find today's attendance record
        today = date.today()
        attendance_record = db.query(SelfAttendance).filter(
            SelfAttendance.user_id == current_user.uuid,
            SelfAttendance.attendance_date == today,
            SelfAttendance.is_deleted.is_(False)
        ).first()
        
        if not attendance_record:
            return AttendanceResponse(
                data=None,
                message="No punch in record found for today",
                status_code=400
            ).to_dict()
        
        if attendance_record.punch_out_time:
            return AttendanceResponse(
                data=None,
                message="Already punched out for today",
                status_code=400
            ).to_dict()
        
        # Update attendance record with punch out details
        attendance_record.punch_out_time = datetime.now()
        attendance_record.punch_out_latitude = attendance_data.latitude
        attendance_record.punch_out_longitude = attendance_data.longitude
        attendance_record.punch_out_location_address = attendance_data.location_address
        
        db.commit()
        db.refresh(attendance_record)
        
        # Calculate total hours
        total_hours = calculate_hours_worked(
            attendance_record.punch_in_time,
            attendance_record.punch_out_time
        )
        
        # Parse assigned projects
        assigned_projects = []
        if attendance_record.assigned_projects:
            try:
                assigned_projects = json.loads(attendance_record.assigned_projects)
            except:
                assigned_projects = []
        
        # Prepare response
        response_data = SelfAttendanceResponse(
            uuid=attendance_record.uuid,
            attendance_date=attendance_record.attendance_date,
            punch_in_time=attendance_record.punch_in_time,
            punch_in_location=LocationData(
                latitude=attendance_record.punch_in_latitude,
                longitude=attendance_record.punch_in_longitude,
                address=attendance_record.punch_in_location_address
            ),
            punch_out_time=attendance_record.punch_out_time,
            punch_out_location=LocationData(
                latitude=attendance_record.punch_out_latitude,
                longitude=attendance_record.punch_out_longitude,
                address=attendance_record.punch_out_location_address
            ),
            total_hours=total_hours,
            assigned_projects=[ProjectInfo(**proj) for proj in assigned_projects] if assigned_projects else []
        )
        
        # Log the action
        log_entry = Log(
            user_id=current_user.uuid,
            action="SELF_ATTENDANCE_PUNCH_OUT",
            details=f"User {current_user.name} punched out at {attendance_record.punch_out_time}, total hours: {total_hours}"
        )
        db.add(log_entry)
        db.commit()
        
        return AttendanceResponse(
            data=response_data.model_dump(),
            message="Punch out successful",
            status_code=200
        ).to_dict()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in punch_out_self_attendance: {str(e)}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()


@attendance_router.get("/self/status", tags=["Self Attendance"])
def get_self_attendance_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current self attendance status for today.
    """
    try:
        today = date.today()
        attendance_record = db.query(SelfAttendance).filter(
            SelfAttendance.user_id == current_user.uuid,
            SelfAttendance.attendance_date == today,
            SelfAttendance.is_deleted.is_(False)
        ).first()

        if not attendance_record:
            response_data = SelfAttendanceStatus(
                is_punched_in=False
            )
        else:
            current_hours = None
            if attendance_record.punch_in_time and not attendance_record.punch_out_time:
                current_hours = get_current_hours_worked(attendance_record.punch_in_time)

            response_data = SelfAttendanceStatus(
                uuid=attendance_record.uuid,
                attendance_date=attendance_record.attendance_date,
                is_punched_in=attendance_record.punch_out_time is None,
                punch_in_time=attendance_record.punch_in_time,
                punch_out_time=attendance_record.punch_out_time,
                current_hours=current_hours
            )

        return AttendanceResponse(
            data=response_data.model_dump(),
            message="Current attendance status retrieved successfully",
            status_code=200
        ).to_dict()

    except Exception as e:
        logger.error(f"Error in get_self_attendance_status: {str(e)}")
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()


@attendance_router.get("/self/history", tags=["Self Attendance"])
def get_self_attendance_history(
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get self attendance history with optional date filtering and pagination.
    """
    try:
        query = db.query(SelfAttendance).filter(
            SelfAttendance.user_id == current_user.uuid,
            SelfAttendance.is_deleted.is_(False)
        )

        # Apply date filters
        if start_date:
            query = query.filter(SelfAttendance.attendance_date >= start_date)
        if end_date:
            query = query.filter(SelfAttendance.attendance_date <= end_date)

        # Get total count
        total_count = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        attendances = query.order_by(desc(SelfAttendance.attendance_date)).offset(offset).limit(limit).all()

        # Prepare response data
        attendance_list = []
        for attendance in attendances:
            # Parse assigned projects
            assigned_projects = []
            if attendance.assigned_projects:
                try:
                    assigned_projects = json.loads(attendance.assigned_projects)
                except:
                    assigned_projects = []

            # Calculate total hours if both punch in and out exist
            total_hours = None
            if attendance.punch_out_time:
                total_hours = calculate_hours_worked(attendance.punch_in_time, attendance.punch_out_time)

            attendance_data = SelfAttendanceResponse(
                uuid=attendance.uuid,
                attendance_date=attendance.attendance_date,
                punch_in_time=attendance.punch_in_time,
                punch_in_location=LocationData(
                    latitude=attendance.punch_in_latitude,
                    longitude=attendance.punch_in_longitude,
                    address=attendance.punch_in_location_address
                ),
                punch_out_time=attendance.punch_out_time,
                punch_out_location=LocationData(
                    latitude=attendance.punch_out_latitude,
                    longitude=attendance.punch_out_longitude,
                    address=attendance.punch_out_location_address
                ) if attendance.punch_out_time else None,
                total_hours=total_hours,
                assigned_projects=[ProjectInfo(**proj) for proj in assigned_projects] if assigned_projects else []
            )
            attendance_list.append(attendance_data)

        response_data = AttendanceHistoryResponse(
            attendances=attendance_list,
            total_count=total_count,
            page=page,
            limit=limit
        )

        return AttendanceResponse(
            data=response_data.model_dump(),
            message="Self attendance history retrieved successfully",
            status_code=200
        ).to_dict()

    except Exception as e:
        logger.error(f"Error in get_self_attendance_history: {str(e)}")
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()

"""
Attendance Management Endpoints
Combines self attendance and project attendance functionality
"""

import os
import json
import re
import traceback
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from src.app.utils.timezone_utils import get_ist_now, convert_to_ist, format_ist_datetime, IST
from src.app.schemas import constants
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Body,
    status as h_status,
    UploadFile
)
from fastapi import Form, File, UploadFile, Depends, Response
from fastapi import status
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from pydantic import ValidationError
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
    DailyAttendanceSummary,
    AttendanceStatus,
    ItemListView,
    AttendanceAnalyticsResponse,
    AttendanceAnalyticsData,
    AdminAttendanceAnalyticsRequest
)
from src.app.services.auth_service import get_current_user, verify_password
from src.app.services.wage_service import get_effective_wage_rate, calculate_and_save_wage
from src.app.utils.logging_config import get_logger
from src.app.utils.attendance_utils import (
    get_current_month_working_days,
    calculate_attendance_percentage,
    get_attendance_feedback,
    parse_month_year,
    get_month_date_range,
    get_working_days_in_month
)

logger = get_logger(__name__)

# Create the main attendance router
attendance_router = APIRouter(prefix="/attendance")


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
        
        # Convert both times to IST timezone
        punch_in_ist = convert_to_ist(punch_in)
        punch_out_ist = convert_to_ist(punch_out)
            
        time_diff = punch_out_ist - punch_in_ist
        hours = time_diff.total_seconds() / 3600
        return f"{hours:.1f}"
    except Exception as e:
        logger.error(f"Error calculating hours worked: {str(e)}")
        return None


def get_current_hours_worked(punch_in: datetime) -> str:
    """Calculate current hours worked since punch in"""
    try:
        current_time = get_ist_now()
        punch_in_ist = convert_to_ist(punch_in)
            
        time_diff = current_time - punch_in_ist
        hours = time_diff.total_seconds() / 3600
        return f"{hours:.1f}"
    except Exception as e:
        logger.error(f"Error calculating current hours: {str(e)}")
        return "0.0"


def check_user_project_assignment(user_id: UUID, project_id: UUID, db: Session) -> bool:
    """Check if user is assigned to the project"""
    try:
        assignment = db.query(ProjectUserMap).filter(
            ProjectUserMap.user_id == user_id,
            ProjectUserMap.project_id == project_id,
            ProjectUserMap.is_deleted.is_(False)
        ).first()
        return assignment is not None
    except Exception as e:
        logger.error(f"Error checking user project assignment: {str(e)}")
        return False


def validate_sub_contractor(sub_contractor_id: UUID, db: Session) -> bool:
    """Validate if sub-contractor exists"""
    try:
        contractor = db.query(Person).filter(
            Person.uuid == sub_contractor_id,
            Person.is_deleted.is_(False)
        ).first()
        return contractor is not None
    except Exception as e:
        logger.error(f"Error validating sub-contractor: {str(e)}")
        return False


# Self Attendance Endpoints
@attendance_router.post("/self/punch-in", tags=["Self Attendance"])
def punch_in_self_attendance(
    attendance_data: SelfAttendancePunchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark self attendance punch in for the current day.
    Requires the user to be logged in; uses current_user context for identity.
    """
    try:
        # Validate coordinates
        if not validate_coordinates(attendance_data.latitude, attendance_data.longitude):
            return AttendanceResponse(
                data=None,
                message="Invalid coordinates provided",
                status_code=400
            ).to_dict()

        # Check if user already has attendance for today
        today = date.today()
        existing = db.query(SelfAttendance).filter(
            SelfAttendance.user_id == current_user.uuid,
            SelfAttendance.attendance_date == today,
            SelfAttendance.is_deleted.is_(False)
        ).first()
        if existing:
            return AttendanceResponse(
                data=None,
                message="Attendance already marked for today",
                status_code=400
            ).to_dict()

        # Get assigned projects
        assigned_projects = get_user_assigned_projects(current_user.uuid, db)

        # Create new attendance record
        new_att = SelfAttendance(
            user_id=current_user.uuid,
            attendance_date=today,
            punch_in_time=get_ist_now(),
            punch_in_latitude=attendance_data.latitude,
            punch_in_longitude=attendance_data.longitude,
            punch_in_location_address=attendance_data.location_address,
            assigned_projects=json.dumps(assigned_projects) if assigned_projects else None,
            status=AttendanceStatus.present.value  # Use enum for status,
        )
        db.add(new_att)
        db.commit()
        db.refresh(new_att)

        # Prepare response
        response_data = SelfAttendanceResponse(
            uuid=new_att.uuid,
            user_id=current_user.uuid,
            user_name=current_user.name,
            attendance_date=new_att.attendance_date,
            punch_in_time=new_att.punch_in_time,
            punch_in_location=LocationData(
                latitude=new_att.punch_in_latitude,
                longitude=new_att.punch_in_longitude,
                address=new_att.punch_in_location_address
            ),
            assigned_projects=[ProjectInfo(**proj) for proj in assigned_projects] if assigned_projects else [],
            status=AttendanceStatus.present
        )

        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="PUNCH_IN",
            entity="self_attendance",
            entity_id=new_att.uuid
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
        logger.error(f"Error in punch_in_self_attendance: {e}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {e}",
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
        attendance_record.punch_out_time = get_ist_now(),
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
            user_id=current_user.uuid,
            user_name=current_user.name,
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
            assigned_projects=[ProjectInfo(**proj) for proj in assigned_projects] if assigned_projects else [],
            status=AttendanceStatus(attendance_record.status)  # Adding the required status field
        )

        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="PUNCH_OUT",
            entity="self_attendance",
            entity_id=attendance_record.uuid
            # details=f"User {current_user.name} punched out at {attendance_record.punch_out_time}, total hours: {total_hours}"
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

@attendance_router.post(
    "/mark-day-off",
    tags=["Self Attendance"],
    description="Mark a day off for the logged-in user (or, for Admin/SuperAdmin, another user).",
)
def mark_day_off(
    date_off: date = Form(..., description="Date to mark as off (YYYY-MM-DD)"),
    user_id: Optional[UUID] = Form(
        None,
        description="(Admin/SuperAdmin only) UUID of the user to mark off"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    - **SuperAdmin/Admin** may pass `user_id` to mark someone else’s day off.
    - **All other roles** must not pass `user_id` (they’ll be blocked).
    - Role-based date rules (past/future/today) still apply to whichever user is targeted.
    """
    try:
        today = date.today()

        # figure out whose record we're touching
        if user_id:
            if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
                return AttendanceResponse(
                    data=None,
                    message="Only Admin/SuperAdmin may manage other users’ days off",
                    status_code=403
                ).to_dict()
            target_user_id = user_id
        else:
            target_user_id = current_user.uuid

        # role-based date restrictions still refer to the current_user’s role...
        if current_user.role == UserRole.SITE_ENGINEER:
            if date_off != today:
                return AttendanceResponse(
                    data=None,
                    message="You can only mark the current day as a day off.",
                    status_code=400
                ).to_dict()

        elif current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            if date_off < today:
                return AttendanceResponse(
                    data=None,
                    message="You cannot mark a day off in the past",
                    status_code=400
                ).to_dict()

        # duplicate-check on the target user
        existing = (
            db.query(SelfAttendance)
              .filter(
                  SelfAttendance.user_id == target_user_id,
                  SelfAttendance.attendance_date == date_off,
                  SelfAttendance.is_deleted.is_(False)
              )
              .first()
        )
        if existing:
            return AttendanceResponse(
                data=None,
                message="Attendance already exists for this date",
                status_code=400
            ).to_dict()

        # create
        new_entry = SelfAttendance(
            uuid=uuid4(),
            user_id=target_user_id,
            attendance_date=date_off,
            status="off day"
        )
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        return AttendanceResponse(
            data={"uuid": str(new_entry.uuid), "date": str(date_off)},
            message="Day marked as off successfully",
            status_code=201
        ).to_dict()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in mark_day_off: {e}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message="Internal server error",
            status_code=500
        ).to_dict()
    
@attendance_router.delete(
    "/self/punch-in/cancel/{punch_in_id}", 
    tags=["Self Attendance"]
)
def cancel_self_punch_in(
    punch_in_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel self punch-in within 5 minutes of marking.
    """
    try:
        # Fetch the punch-in entry
        punch_record = db.query(SelfAttendance).filter(
            SelfAttendance.uuid == punch_in_id,
            SelfAttendance.user_id == current_user.uuid,
            SelfAttendance.status == "present",
            SelfAttendance.is_deleted.is_(False)
        ).first()

        if not punch_record:
            return AttendanceResponse(
                data=None,
                message="Punch-in record not found",
                status_code=404
            ).to_dict()

        # Time check: allow cancel only within 5 minutes
        current_time = datetime.now()
        punch_in_time = punch_record.punch_in_time

        if (current_time - punch_in_time) > timedelta(minutes=5):
            return AttendanceResponse(
                data=None,
                message="Cannot cancel punch-in after 5 minutes",
                status_code=400
            ).to_dict()
        
        # Remove duplicate deleted records
        duplicates = (
            db.query(SelfAttendance)
            .filter(
                SelfAttendance.user_id == punch_record.user_id,
                SelfAttendance.attendance_date == punch_record.attendance_date,
                SelfAttendance.is_deleted.is_(True),
                SelfAttendance.id != punch_record.id
            )
            .all()
        )
        for d in duplicates:
            db.delete(d)
        db.commit()

        # Soft delete
        punch_record.is_deleted = True
        db.commit()

        # Log cancellation
        log_entry = Log(
            performed_by=current_user.uuid,
            action="PUNCH_IN_CANCELLED",
            entity="self_attendance",
            entity_id=punch_record.uuid
        )
        db.add(log_entry)
        db.commit()

        return AttendanceResponse(
            data={"punch_in_id": str(punch_record.uuid)},
            message="Punch-in cancelled successfully",
            status_code=200
        ).to_dict()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in cancel_self_punch_in: {str(e)}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()

@attendance_router.delete(
    "/self/day-off/cancel/{day_off_id}",
    tags=["Self Attendance"],
    description="Cancel a previously marked day off (soft delete)",
)
def cancel_self_day_off(
    day_off_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft-delete a user’s “off day” record.
    Only records with status == "off day" and is_deleted == False are cancellable.
    """
    try:
        # Fetch only an off-day record for this user
        off_record = (
            db.query(SelfAttendance)
              .filter(
                  SelfAttendance.uuid == day_off_id,
                  SelfAttendance.user_id == current_user.uuid,
                  SelfAttendance.status == "off day",
                  SelfAttendance.is_deleted.is_(False)
              )
              .first()
        )
        if not off_record:
            return AttendanceResponse(
                data=None,
                message="Day-off record not found or not cancellable",
                status_code=404
            ).to_dict()
        
        # Remove duplicate deleted records
        duplicates = (
            db.query(SelfAttendance)
            .filter(
                SelfAttendance.user_id == off_record.user_id,
                SelfAttendance.attendance_date == off_record.attendance_date,
                SelfAttendance.is_deleted.is_(True),
                SelfAttendance.id != off_record.id
            )
            .all()
        )
        for d in duplicates:
            db.delete(d)
        db.commit()

        # Soft delete
        off_record.is_deleted = True
        db.commit()

        # Log cancellation
        log_entry = Log(
            performed_by=current_user.uuid,
            action="DAY_OFF_CANCELLED",
            entity="self_attendance",
            entity_id=off_record.uuid
        )
        db.add(log_entry)
        db.commit()

        return AttendanceResponse(
            data={"day_off_id": str(off_record.uuid)},
            message="Day off cancelled successfully",
            status_code=200
        ).to_dict()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in cancel_self_day_off: {e}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message="Internal server error",
            status_code=500
        ).to_dict()

@attendance_router.get(
    "/attendance/self/history",
    tags=["Self Attendance"],
)
def get_self_attendance_history(
    db: Session = Depends(get_db),
    user_uuid: Optional[UUID] = Query(None),
    recent: Optional[bool] = Query(False),
    month: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Get self attendance history for the current user, or for all users if admin/super admin.
    """
    try:
        # Build base query with user join
        query = (db.query(SelfAttendance, User)
                .join(User, SelfAttendance.user_id == User.uuid)
                .filter(SelfAttendance.is_deleted.is_(False)))

        # Role-based filtering
        if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            # Non-admins: can only see their own
            query = query.filter(SelfAttendance.user_id == current_user.uuid)
        elif user_uuid:
            # Admin: can filter by any user
            query = query.filter(SelfAttendance.user_id == user_uuid)
        # If admin & no user_uuid, see all

        # Filter by status
        if status:
            query = query.filter(SelfAttendance.status == status)

        # Filter by date
        if date:
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                query = query.filter(SelfAttendance.attendance_date == date_obj)
            except Exception:
                return AttendanceResponse(
                    data=None,
                    message="Invalid date format. Use 'YYYY-MM-DD'.",
                    status_code=400
                ).to_dict()

        # Filter by month
        if month:
            if not re.match(r"^\d{4}-\d{2}$", month):
                return AttendanceResponse(
                    data=None,
                    message="Invalid month format. Use 'YYYY-MM'.",
                    status_code=400
                ).to_dict()
            year, mon = map(int, month.split("-"))
            query = query.filter(
                func.extract('year', SelfAttendance.attendance_date) == year,
                func.extract('month', SelfAttendance.attendance_date) == mon
            )

        # Filter by from_date/to_date
        if from_date:
            try:
                from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
                query = query.filter(SelfAttendance.attendance_date >= from_date_obj)
            except Exception:
                return AttendanceResponse(
                    data=None,
                    message="Invalid from_date format. Use 'YYYY-MM-DD'.",
                    status_code=400
                ).to_dict()
        if to_date:
            try:
                to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
                query = query.filter(SelfAttendance.attendance_date <= to_date_obj)
            except Exception:
                return AttendanceResponse(
                    data=None,
                    message="Invalid to_date format. Use 'YYYY-MM-DD'.",
                    status_code=400
                ).to_dict()

        # Order and fetch
        query = query.order_by(SelfAttendance.attendance_date.desc())

        if recent:
            query = query.limit(5)

        attendance_records = query.all()

        if not attendance_records:
            return AttendanceResponse(
                data=[],
                message="No attendance records found",
                status_code=404
            ).to_dict()

        # Prepare response data
        response_data = []
        for record, user in attendance_records:
            total_hours = None
            if record.punch_in_time and record.punch_out_time:
                total_hours = calculate_hours_worked(
                    record.punch_in_time, record.punch_out_time
                )

            # Safely handle None for location fields
            punch_in_lat = record.punch_in_latitude if record.punch_in_latitude is not None else 0.0
            punch_in_long = record.punch_in_longitude if record.punch_in_longitude is not None else 0.0
            punch_in_addr = record.punch_in_location_address if record.punch_in_location_address is not None else ""
            punch_out_lat = record.punch_out_latitude if record.punch_out_latitude is not None else 0.0
            punch_out_long = record.punch_out_longitude if record.punch_out_longitude is not None else 0.0
            punch_out_addr = record.punch_out_location_address if record.punch_out_location_address is not None else ""

            response_data.append(SelfAttendanceResponse(
                uuid=record.uuid,
                user_id=user.uuid,
                user_name=user.name,
                attendance_date=record.attendance_date,
                punch_in_time=record.punch_in_time,
                punch_in_location=LocationData(
                    latitude=punch_in_lat,
                    longitude=punch_in_long,
                    address=punch_in_addr
                ),
                punch_out_time=record.punch_out_time,
                punch_out_location=LocationData(
                    latitude=punch_out_lat,
                    longitude=punch_out_long,
                    address=punch_out_addr
                ),
                total_hours=total_hours,
                assigned_projects=json.loads(record.assigned_projects) if record.assigned_projects else [],
                status=AttendanceStatus(record.status)
            ).model_dump())

        return AttendanceResponse(
            data=response_data,
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



# @attendance_router.get(
#     "/self/status", 
#     tags=["Self Attendance"]
# )
# def get_self_attendance_status(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Get current self attendance status for today.
#     Returns detailed status information including:
#     - Present: When user has punched in
#     - Off day: When user has marked the day as off
#     - None: When no attendance record exists for today
#     """
#     try:
#         today = date.today()
#         attendance_record = db.query(SelfAttendance).filter(
#             SelfAttendance.user_id == current_user.uuid,
#             SelfAttendance.attendance_date == today,
#             SelfAttendance.is_deleted.is_(False)
#         ).first()

#         if not attendance_record:
#             # No record means absent
#             response_data = SelfAttendanceStatus(
#                 is_punched_in=False,
#                 status=None,
#                 user_id=current_user.uuid,
#                 user_name=current_user.name,
#                 attendance_date=today
#             )
#         else:
#             current_hours = None
#             if attendance_record.status == "off day":
#                 # Handle off day status
#                 response_data = SelfAttendanceStatus(
#                     uuid=attendance_record.uuid,
#                     user_id=current_user.uuid,
#                     user_name=current_user.name,
#                     attendance_date=attendance_record.attendance_date,
#                     is_punched_in=False,
#                     status=AttendanceStatus.off_day
#                 )
#             else:
#                 # Handle present status with punch in/out details
#                 if attendance_record.punch_in_time and attendance_record.punch_out_time:
#                     hours = (attendance_record.punch_out_time - attendance_record.punch_in_time).total_seconds() / 3600
#                     current_hours = f"{float(hours):.2f} hrs"
#                 elif attendance_record.punch_in_time and not attendance_record.punch_out_time:
#                     hours = get_current_hours_worked(attendance_record.punch_in_time)
#                     current_hours = f"{float(hours):.2f} hrs" if hours is not None else None

#                 response_data = SelfAttendanceStatus(
#                     uuid=attendance_record.uuid,
#                     user_id=current_user.uuid,
#                     user_name=current_user.name,
#                     attendance_date=attendance_record.attendance_date,
#                     is_punched_in=attendance_record.punch_out_time is None,
#                     punch_in_time=attendance_record.punch_in_time,
#                     punch_out_time=attendance_record.punch_out_time,
#                     current_hours=current_hours,
#                     status=AttendanceStatus.present
#                 )

#         return AttendanceResponse(
#             data=response_data.model_dump(),
#             message="Current attendance status retrieved successfully",
#             status_code=200
#         ).to_dict()

#     except Exception as e:
#         logger.error(f"Error in get_self_attendance_status: {str(e)}")
#         return AttendanceResponse(
#             data=None,
#             message=f"Internal server error: {str(e)}",
#             status_code=500
#         ).to_dict()

@attendance_router.get(
    "/self/status", 
    tags=["Self Attendance"]
)
def get_self_attendance_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current self attendance status for today only.
    After midnight (new date), no previous-day data will be shown.
    """
    try:
        today = date.today()

        # Fetch record only if it's for today
        attendance_record = db.query(SelfAttendance).filter(
            SelfAttendance.user_id == current_user.uuid,
            SelfAttendance.attendance_date == today,
            SelfAttendance.is_deleted.is_(False)
        ).first()

        # If no attendance exists for today, return null state
        if not attendance_record:
            response_data = SelfAttendanceStatus(
                is_punched_in=False,
                status=None,
                user_id=current_user.uuid,
                user_name=current_user.name,
                attendance_date=today
            )
            return AttendanceResponse(
                data=response_data.model_dump(),
                message="No attendance marked for today",
                status_code=200
            ).to_dict()

        # If it's an OFF day
        if attendance_record.status == AttendanceStatus.off_day:
            response_data = SelfAttendanceStatus(
                uuid=attendance_record.uuid,
                user_id=current_user.uuid,
                user_name=current_user.name,
                attendance_date=today,
                is_punched_in=False,
                status=AttendanceStatus.off_day
            )
            return AttendanceResponse(
                data=response_data.model_dump(),
                message="Off day marked for today",
                status_code=200
            ).to_dict()

        # Present status (punched in or out)
        current_hours = None
        if attendance_record.punch_in_time and attendance_record.punch_out_time:
            hours = (attendance_record.punch_out_time - attendance_record.punch_in_time).total_seconds() / 3600
            current_hours = f"{float(hours):.2f} hrs"
        elif attendance_record.punch_in_time:
            hours = get_current_hours_worked(attendance_record.punch_in_time)
            current_hours = f"{float(hours):.2f} hrs" if hours is not None else None

        response_data = SelfAttendanceStatus(
            uuid=attendance_record.uuid,
            user_id=current_user.uuid,
            user_name=current_user.name,
            attendance_date=today,
            is_punched_in=attendance_record.punch_out_time is None,
            punch_in_time=attendance_record.punch_in_time,
            punch_out_time=attendance_record.punch_out_time,
            current_hours=current_hours,
            status=AttendanceStatus.present
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


@attendance_router.post(
    "/project/attendance",
    tags=["Project Attendance"],
    status_code=201,
    description="""
Mark attendance for a project with optional photo upload.

**Request Body Example:**
```json
{
  "project_id": "df46d83e-ac87-470d-b1e0-758d32e401a6",           // Required: The UUID of the project
  "item_id": "24d2f692-e339-454d-a9c8-73b928e1a649",               // Required: The UUID of the work item
  "sub_contractor_id": "73c7d1a1-d6ee-479e-8564-567707696138",     // Required: The UUID of the sub-contractor
  "no_of_labours": 5,                                              // Required: Number of labours present
  "latitude": 22.572645,                                           // Required: Location latitude
  "longitude": 88.363892,                                          // Required: Location longitude
  "location_address": "Site B, Sector 5, Kolkata",                 // Required: Text address of the attendance location
  "notes": "Finished laying the base layer of brickwork."           // Optional: Any remarks/notes
}
"""
)
def mark_project_attendance(
    attendance: str = Form(..., description="JSON string of ProjectAttendanceCreate"),
    attendance_photo: Optional[UploadFile] = File(None, description="Optional photo of site/labourers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    try:
        # Parse & validate JSON payload
        try:
            payload = json.loads(attendance)
            attendance_data = ProjectAttendanceCreate(**payload)
        except (json.JSONDecodeError, ValidationError) as e:
            response.status_code = 400
            return {"status_code":400, "message":"Invalid attendance data", "details": str(e)}

        # Authorization & business checks (as before)…
        allowed_roles = [
            UserRole.SITE_ENGINEER,
            UserRole.PROJECT_MANAGER,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN
        ]
        if current_user.role not in allowed_roles:
            response.status_code = 403
            return {"status_code":403, "message":"Not authorized to mark project attendance"}

        if not validate_coordinates(attendance_data.latitude, attendance_data.longitude):
            response.status_code = 400
            return {"status_code":400, "message":"Invalid coordinates provided"}

        if current_user.role == UserRole.SITE_ENGINEER:
            ok = check_user_project_assignment(
                current_user.uuid, attendance_data.project_id, db
            )
            if not ok:
                response.status_code = 403
                return {"status_code":403, "message":"Not assigned to this project"}

        project = (
            db.query(Project)
              .filter(
                Project.uuid == attendance_data.project_id,
                Project.is_deleted.is_(False)
              )
              .first()
        )
        if not project:
            response.status_code = 404
            return {"status_code":404, "message":"Project not found"}

        if not validate_sub_contractor(attendance_data.sub_contractor_id, db):
            response.status_code = 404
            return {"status_code":404, "message":"Sub-contractor not found"}

        sub = db.query(Person).filter(
            Person.uuid == attendance_data.sub_contractor_id
        ).first()

        # Handle photo upload
        photo_path = None
        if attendance_photo:
            ext = os.path.splitext(attendance_photo.filename)[1]
            fname = f"Attendance_{str(uuid4())}{ext}"
            upload_dir = "uploads/attendance_photos"
            os.makedirs(upload_dir, exist_ok=True)
            photo_path = os.path.join(upload_dir, fname)
            with open(photo_path, "wb") as buffer:
                buffer.write(attendance_photo.file.read())

        # Create & save attendance record
        today = date.today()
        att = ProjectAttendance(
            site_engineer_id=current_user.uuid,
            project_id=attendance_data.project_id,
            item_id=attendance_data.item_id,
            sub_contractor_id=attendance_data.sub_contractor_id,
            no_of_labours=attendance_data.no_of_labours,
            attendance_date=today,
            marked_at=get_ist_now(),
            latitude=attendance_data.latitude,
            longitude=attendance_data.longitude,
            location_address=attendance_data.location_address,
            notes=attendance_data.notes,
            photo_path=photo_path,
        )
        db.add(att); 
        db.commit(); 
        db.refresh(att)

        # Wage calculation & logging (same as before)…
        wage_calc = calculate_and_save_wage(
            project_id=attendance_data.project_id,
            attendance_id=att.uuid,
            no_of_labours=attendance_data.no_of_labours,
            attendance_date=today,
            db=db
        )

        # Build response using Pydantic model
        location_data = LocationData(
            latitude=att.latitude,
            longitude=att.longitude,
            address=att.location_address
        )

        wage_info = None
        if wage_calc:
            wage_info = WageCalculationInfo(
                uuid=wage_calc.uuid,
                daily_wage_rate=wage_calc.daily_wage_rate,
                total_wage_amount=wage_calc.total_wage_amount,
                wage_config_effective_date=wage_calc.project_daily_wage.effective_date
            )

        result = ProjectAttendanceResponse(
            uuid=att.uuid,
            project=ProjectInfo(uuid=project.uuid, name=project.name),
            item=ItemListView(uuid=att.item_id, name=att.item.name, category=att.item.category),
            sub_contractor=PersonInfo(uuid=sub.uuid, name=sub.name),
            no_of_labours=att.no_of_labours,
            attendance_date=att.attendance_date,
            marked_at=convert_to_ist(att.marked_at),
            location=location_data,
            notes=att.notes,
            photo_path=photo_path and f"{constants.HOST_URL}/{photo_path}",
            wage_calculation=wage_info
        )

        # Log action
        db.add(Log(
            performed_by=current_user.uuid,
            action="PROJECT_ATTENDANCE",
            entity="project_attendance",
            entity_id=att.uuid
        ))
        db.commit()

        return {"status_code":201, "message":"Attendance marked successfully", "data": result}

    except Exception as e:
        db.rollback()
        logger.error(f"Error in mark_project_attendance: {e}", exc_info=True)
        if response:
            response.status_code = 500
        return {"status_code":500, "message":"Internal server error", "details": str(e)}
    
    
@attendance_router.put(
    "/project/attendance/{attendance_id}",
    tags=["Project Attendance"],
    status_code=200,
    description="""
Update project attendance record. Only provided fields will be updated.

**Request Body Example:**
```json
{
  "project_id": "df46d83e-ac87-470d-b1e0-758d32e401a6",           // Optional: The UUID of the project
  "item_id": "24d2f692-e339-454d-a9c8-73b928e1a649",               // Optional: The UUID of the work item
  "sub_contractor_id": "73c7d1a1-d6ee-479e-8564-567707696138",     // Optional: The UUID of the sub-contractor
  "no_of_labours": 5,                                              // Optional: Number of labours present
  "latitude": 22.572645,                                           // Optional: Location latitude
  "longitude": 88.363892,                                          // Optional: Location longitude
  "location_address": "Site B, Sector 5, Kolkata",                 // Optional: Text address of the attendance location
  "notes": "Updated notes for the attendance"                      // Optional: Any remarks/notes
}
"""
)
def update_project_attendance(
    attendance_id: UUID,
    attendance: str = Form(..., description="JSON string with fields to update"),
    attendance_photo: Optional[UploadFile] = File(None, description="Optional new photo of site/labourers"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    try:
        # Fetch existing record
        att = db.query(ProjectAttendance).filter(
            ProjectAttendance.uuid == attendance_id,
            ProjectAttendance.is_deleted.is_(False)
        ).first()

        if not att:
            response.status_code = 404
            return {
                "status_code": 404,
                "message": "Attendance record not found"
            }

        # Parse update data
        try:
            update_data = json.loads(attendance)
        except json.JSONDecodeError as e:
            response.status_code = 400
            return {
                "status_code": 400,
                "message": "Invalid JSON data",
                "details": str(e)
            }

        # Authorization checks
        allowed_roles = [
            UserRole.SITE_ENGINEER,
            UserRole.PROJECT_MANAGER,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN
        ]
        if current_user.role not in allowed_roles:
            response.status_code = 403
            return {
                "status_code": 403,
                "message": "Not authorized to update project attendance"
            }

        # Additional authorization for site engineers
        if current_user.role == UserRole.SITE_ENGINEER:
            # Can only update their own records
            if att.site_engineer_id != current_user.uuid:
                response.status_code = 403
                return {
                    "status_code": 403,
                    "message": "Not authorized to update this attendance record"
                }
            
            # If project_id is being updated, check assignment
            if "project_id" in update_data:
                ok = check_user_project_assignment(
                    current_user.uuid, UUID(update_data["project_id"]), db
                )
                if not ok:
                    response.status_code = 403
                    return {
                        "status_code": 403,
                        "message": "Not assigned to the target project"
                    }

        # Validate updates
        if "project_id" in update_data:
            project = db.query(Project).filter(
                Project.uuid == UUID(update_data["project_id"]),
                Project.is_deleted.is_(False)
            ).first()
            if not project:
                response.status_code = 404
                return {
                    "status_code": 404,
                    "message": "Target project not found"
                }

        if "sub_contractor_id" in update_data:
            if not validate_sub_contractor(UUID(update_data["sub_contractor_id"]), db):
                response.status_code = 404
                return {
                    "status_code": 404,
                    "message": "Target sub-contractor not found"
                }

        if "latitude" in update_data and "longitude" in update_data:
            if not validate_coordinates(
                float(update_data["latitude"]), 
                float(update_data["longitude"])
            ):
                response.status_code = 400
                return {
                    "status_code": 400,
                    "message": "Invalid coordinates provided"
                }

        # Handle photo update if provided
        if attendance_photo:
            # Delete old photo if exists
            if att.photo_path and os.path.exists(att.photo_path):
                try:
                    os.remove(att.photo_path)
                except Exception as e:
                    logger.warning(f"Failed to delete old photo: {e}")

            # Save new photo
            ext = os.path.splitext(attendance_photo.filename)[1]
            fname = f"Attendance_{str(uuid4())}{ext}"
            upload_dir = "uploads/attendance_photos"
            os.makedirs(upload_dir, exist_ok=True)
            photo_path = os.path.join(upload_dir, fname)
            with open(photo_path, "wb") as buffer:
                buffer.write(attendance_photo.file.read())
            att.photo_path = photo_path

        # Update fields
        for key, value in update_data.items():
            if key in [
                "project_id", "item_id", "sub_contractor_id"
            ] and value:
                setattr(att, key, UUID(value))
            elif key in [
                "latitude", "longitude"
            ] and value is not None:
                setattr(att, key, float(value))
            elif key in [
                "no_of_labours"
            ] and value is not None:
                setattr(att, key, int(value))
            elif key in [
                "location_address", "notes"
            ]:
                setattr(att, key, value)

        # Recalculate wages if labour count changed
        if "no_of_labours" in update_data:
            # First, delete existing wage calculation if any
            existing_wages = db.query(ProjectAttendanceWage).filter(
                ProjectAttendanceWage.project_attendance_id == att.uuid
            ).all()
            
            if existing_wages:
                for wage in existing_wages:
                    db.delete(wage)
                db.commit()

            # Now calculate and save new wage
            wage_calc = calculate_and_save_wage(
                project_id=att.project_id,
                attendance_id=att.uuid,
                no_of_labours=att.no_of_labours,
                attendance_date=att.attendance_date,
                db=db
            )

        # Save changes
        db.commit()
        db.refresh(att)

        # Log update
        log_entry = Log(
            performed_by=current_user.uuid,
            action="PROJECT_UPDATED",
            entity="project_attendance",
            entity_id=att.uuid
        )
        db.add(log_entry)
        db.commit()

        # Prepare response
        result = ProjectAttendanceResponse(
            uuid=att.uuid,
            project=ProjectInfo(uuid=att.project.uuid, name=att.project.name),
            item=ItemListView(
                uuid=att.item.uuid,
                name=att.item.name,
                category=att.item.category
            ) if att.item else None,
            sub_contractor=PersonInfo(
                uuid=att.sub_contractor.uuid,
                name=att.sub_contractor.name
            ) if att.sub_contractor else None,
            no_of_labours=att.no_of_labours,
            attendance_date=att.attendance_date,
            marked_at=convert_to_ist(att.marked_at),
            location=LocationData(
                latitude=att.latitude,
                longitude=att.longitude,
                address=att.location_address
            ),
            notes=att.notes,
            photo_path=(
                f"{constants.HOST_URL}/{att.photo_path}" if att.photo_path else None
            ),
            wage_calculation=WageCalculationInfo(
                uuid=att.wage_calculation.uuid,
                daily_wage_rate=att.wage_calculation.daily_wage_rate,
                total_wage_amount=att.wage_calculation.total_wage_amount,
                wage_config_effective_date=att.wage_calculation.project_daily_wage.effective_date
                if att.wage_calculation and att.wage_calculation.project_daily_wage else None
            ) if att.wage_calculation else None
        )

        return {
            "status_code": 200,
            "message": "Attendance updated successfully",
            "data": result
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_project_attendance: {e}", exc_info=True)
        if response:
            response.status_code = 500
        return {
            "status_code": 500,
            "message": "Internal server error",
            "details": str(e)
        }
    


@attendance_router.delete(
    "/project/attendance/{attendance_id}",
    tags=["Project Attendance"],
    status_code=200,
    description="""
Soft-delete a project attendance record by marking it as deleted (does not remove from DB).
"""
)
def delete_project_attendance(
    attendance_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,
):
    try:
        # Fetch the record (make sure it’s not already deleted)
        att = db.query(ProjectAttendance).filter(
            ProjectAttendance.uuid == attendance_id,
            ProjectAttendance.is_deleted.is_(False)
        ).first()

        if not att:
            response.status_code = 404
            return {
                "status_code": 404,
                "message": "Attendance record not found or already deleted"
            }

        # Authorization (optional: restrict to certain roles)
        allowed_roles = [
            UserRole.SITE_ENGINEER,
            UserRole.PROJECT_MANAGER,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN
        ]
        if current_user.role not in allowed_roles:
            response.status_code = 403
            return {
                "status_code": 403,
                "message": "Not authorized to delete project attendance"
            }

        # Soft delete
        att.is_deleted = True
        db.commit()

        # Log action
        db.add(Log(
            performed_by=current_user.uuid,
            action="PROJECT_DELETED",
            entity="project_attendance",
            entity_id=att.uuid
        ))
        db.commit()

        return {
            "status_code": 200,
            "message": "Attendance deleted successfully",
            "data": {"attendance_id": str(att.uuid)}
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error in delete_project_attendance: {e}", exc_info=True)
        if response:
            response.status_code = 500
        return {
            "status_code": 500,
            "message": "Internal server error",
            "details": str(e)
        }


@attendance_router.get("/project/history", tags=["Project Attendance"])
def get_project_attendance_history(
    project_id: Optional[UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    no_of_labours: Optional[int] = Query(None),
    wage_rate: Optional[float] = Query(None),
    sub_contractor_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get project attendance history with optional filtering and pagination.
    Site Engineers can only see their own project attendances.
    """
    try:
        query = db.query(ProjectAttendance).filter(ProjectAttendance.is_deleted.is_(False))

        # Role-based filtering
        if current_user.role == UserRole.SITE_ENGINEER:
            query = query.filter(ProjectAttendance.site_engineer_id == current_user.uuid)
        elif current_user.role == UserRole.PROJECT_MANAGER:
            assigned_projects = db.query(ProjectUserMap.project_id).filter(
                ProjectUserMap.user_id == current_user.uuid,
                ProjectUserMap.is_deleted.is_(False)
            ).subquery()
            query = query.filter(ProjectAttendance.project_id.in_(assigned_projects.select()))

        # Filters
        if project_id:
            query = query.filter(ProjectAttendance.project_id == project_id)
        if start_date:
            query = query.filter(ProjectAttendance.attendance_date >= start_date)
        if end_date:
            query = query.filter(ProjectAttendance.attendance_date <= end_date)
        if no_of_labours is not None:
            query = query.filter(ProjectAttendance.no_of_labours == no_of_labours)
        if sub_contractor_id:
            query = query.filter(ProjectAttendance.sub_contractor_id == sub_contractor_id)
        if wage_rate is not None:
            query = query.join(ProjectAttendanceWage).filter(
                ProjectAttendanceWage.daily_wage_rate == wage_rate
            ).distinct()

        total_count = query.count()
        offset = (page - 1) * limit

        attendances = query.options(
            joinedload(ProjectAttendance.project),
            joinedload(ProjectAttendance.sub_contractor),
            joinedload(ProjectAttendance.site_engineer),
            joinedload(ProjectAttendance.wage_calculation)
        ).order_by(desc(ProjectAttendance.marked_at)).offset(offset).limit(limit).all()

        # Summary helpers
        total_labour_days = 0
        unique_contractors = set()
        attendance_list = []

        for attendance in attendances:
            total_labour_days += attendance.no_of_labours or 0
            unique_contractors.add(attendance.sub_contractor_id)

            wage_info = None
            if attendance.wage_calculation:
                wc = attendance.wage_calculation
                wage_info = WageCalculationInfo(
                    uuid=wc.uuid,
                    daily_wage_rate=wc.daily_wage_rate or 0.0,
                    total_wage_amount=wc.total_wage_amount or 0.0,
                    wage_config_effective_date=wc.project_daily_wage.effective_date if wc.project_daily_wage else None
                )

            attendance_data = ProjectAttendanceResponse(
                uuid=attendance.uuid,
                project=ProjectInfo(
                    uuid=attendance.project.uuid if attendance.project else None,
                    name=attendance.project.name if attendance.project else ""
                ),
                item=ItemListView(
                    uuid=attendance.item.uuid if attendance.item else None,
                    name=attendance.item.name if attendance.item else "",
                    category=attendance.item.category if attendance.item else None    
                ),
                sub_contractor=PersonInfo(
                    uuid=attendance.sub_contractor.uuid if attendance.sub_contractor else None,
                    name=attendance.sub_contractor.name if attendance.sub_contractor else ""
                ),
                no_of_labours=attendance.no_of_labours or 0,
                attendance_date=attendance.attendance_date,
                photo_path=constants.HOST_URL + "/" + attendance.photo_path if attendance.photo_path else None,
                marked_at=convert_to_ist(attendance.marked_at),
                location=LocationData(
                    latitude=attendance.latitude or 0.0,
                    longitude=attendance.longitude or 0.0,
                    address=attendance.location_address or ""
                ),
                notes=attendance.notes or "",
                wage_calculation=wage_info
            )
            attendance_list.append(attendance_data)

        summary = ProjectAttendanceSummary(
            total_labour_days=total_labour_days,
            unique_contractors=len([c for c in unique_contractors if c]),
            average_daily_labours=(total_labour_days / len(attendance_list)) if attendance_list else 0.0
        )

        response_data = ProjectAttendanceHistoryResponse(
            attendances=attendance_list,
            total_count=total_count,
            page=page,
            limit=limit,
            summary=summary
        )

        return AttendanceResponse(
            data=response_data.model_dump(),
            message="Project attendance history retrieved successfully",
            status_code=200
        ).to_dict()

    except Exception as e:
        logger.error(f"Error in get_project_attendance_history: {str(e)}")
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()


@attendance_router.get("/analytics", tags=["Attendance Analytics"])
def get_user_attendance_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get attendance analytics for the current logged-in user for the current month.

    Returns:
        - Attendance percentage for current month
        - Feedback based on attendance record
    """
    try:
        # Validate current user
        if not current_user or not hasattr(current_user, 'uuid'):
            return AttendanceResponse(
                data=None,
                message="Invalid user session",
                status_code=401
            ).to_dict()

        today = date.today()
        current_year = today.year
        current_month = today.month

        # Get total working days in current month
        total_working_days = get_current_month_working_days()

        if total_working_days == 0:
            return AttendanceResponse(
                data=None,
                message="No working days found for current month",
                status_code=400
            ).to_dict()

        # Get start and end dates for current month
        try:
            start_date, end_date = get_month_date_range(current_year, current_month)
        except ValueError as e:
            return AttendanceResponse(
                data=None,
                message=f"Error calculating month range: {str(e)}",
                status_code=400
            ).to_dict()

        # Count present days for the user in current month
        # Present days include: punch in/out records with status 'present' or approved attendance
        try:
            present_days_query = db.query(SelfAttendance).filter(
                SelfAttendance.user_id == current_user.uuid,
                SelfAttendance.attendance_date >= start_date,
                SelfAttendance.attendance_date <= end_date,
                SelfAttendance.is_deleted.is_(False),
                SelfAttendance.status.in_(['present', 'approved'])  # Valid attendance statuses
            )

            present_days = present_days_query.count()
        except Exception as e:
            logger.error(f"Error querying attendance data: {str(e)}")
            return AttendanceResponse(
                data=None,
                message="Error retrieving attendance data",
                status_code=500
            ).to_dict()

        # Calculate attendance percentage
        percentage = calculate_attendance_percentage(present_days, total_working_days)

        # Get feedback based on percentage
        feedback = get_attendance_feedback(percentage)

        # Validate calculated values
        if percentage < 0 or percentage > 100:
            logger.warning(f"Invalid percentage calculated: {percentage}")
            percentage = max(0, min(100, percentage))  # Clamp to valid range

        # Prepare response data
        try:
            analytics_data = AttendanceAnalyticsData(
                current_month={
                    "percentage": int(percentage),  # Convert to integer as per requirement
                    "feedback": feedback
                }
            )

            return AttendanceAnalyticsResponse(
                data=analytics_data,
                message="Attendance Analytics Fetched Successfully.",
                status_code=200
            ).to_dict()
        except Exception as e:
            logger.error(f"Error creating response data: {str(e)}")
            return AttendanceResponse(
                data=None,
                message="Error formatting response data",
                status_code=500
            ).to_dict()

    except Exception as e:
        logger.error(f"Error in get_user_attendance_analytics: {str(e)}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()


@attendance_router.get("/admin/analytics", tags=["Attendance Analytics"])
def get_admin_attendance_analytics(
    month: str = Query(..., description="Month in MM-YYYY format (e.g., '12-2024')"),
    user_id: UUID = Query(..., description="UUID of the user to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get attendance analytics for a specific user and month (Admin/Super Admin only).

    Args:
        month: Month in MM-YYYY format (e.g., "12-2024")
        user_id: UUID of the user to analyze

    Returns:
        - Attendance percentage for specified month
        - Feedback based on attendance record
    """
    try:
        # Validate current user
        if not current_user or not hasattr(current_user, 'uuid') or not hasattr(current_user, 'role'):
            return AttendanceResponse(
                data=None,
                message="Invalid user session",
                status_code=401
            ).to_dict()

        # Check if current user has admin privileges
        if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return AttendanceResponse(
                data=None,
                message="Access denied. Admin or Super Admin privileges required.",
                status_code=403
            ).to_dict()

        # Validate input parameters
        if not month or not month.strip():
            return AttendanceResponse(
                data=None,
                message="Month parameter is required",
                status_code=400
            ).to_dict()

        if not user_id:
            return AttendanceResponse(
                data=None,
                message="User ID parameter is required",
                status_code=400
            ).to_dict()

        # Validate month format
        try:
            target_month, target_year = parse_month_year(month.strip())
        except ValueError as e:
            return AttendanceResponse(
                data=None,
                message=str(e),
                status_code=400
            ).to_dict()

        # Check if target user exists
        target_user = db.query(User).filter(
            User.uuid == user_id,
            User.is_deleted.is_(False),
            User.is_active.is_(True)
        ).first()

        if not target_user:
            return AttendanceResponse(
                data=None,
                message="User not found or inactive",
                status_code=404
            ).to_dict()

        # Get total working days in specified month
        total_working_days = get_working_days_in_month(target_year, target_month)

        if total_working_days == 0:
            return AttendanceResponse(
                data=None,
                message=f"No working days found for {month}",
                status_code=400
            ).to_dict()

        # Get start and end dates for specified month
        try:
            start_date, end_date = get_month_date_range(target_year, target_month)
        except ValueError as e:
            return AttendanceResponse(
                data=None,
                message=f"Error calculating month range: {str(e)}",
                status_code=400
            ).to_dict()

        # Count present days for the target user in specified month
        # Present days include: punch in/out records with status 'present' or approved attendance
        try:
            present_days_query = db.query(SelfAttendance).filter(
                SelfAttendance.user_id == user_id,
                SelfAttendance.attendance_date >= start_date,
                SelfAttendance.attendance_date <= end_date,
                SelfAttendance.is_deleted.is_(False),
                SelfAttendance.status.in_(['present', 'approved'])  # Valid attendance statuses
            )

            present_days = present_days_query.count()
        except Exception as e:
            logger.error(f"Error querying attendance data for user {user_id}: {str(e)}")
            return AttendanceResponse(
                data=None,
                message="Error retrieving attendance data",
                status_code=500
            ).to_dict()

        # Calculate attendance percentage
        percentage = calculate_attendance_percentage(present_days, total_working_days)

        # Get feedback based on percentage
        feedback = get_attendance_feedback(percentage)

        # Validate calculated values
        if percentage < 0 or percentage > 100:
            logger.warning(f"Invalid percentage calculated for user {user_id}: {percentage}")
            percentage = max(0, min(100, percentage))  # Clamp to valid range

        # Prepare response data
        try:
            analytics_data = AttendanceAnalyticsData(
                current_month={
                    "percentage": int(percentage),  # Convert to integer as per requirement
                    "feedback": feedback
                }
            )

            return AttendanceAnalyticsResponse(
                data=analytics_data,
                message="Attendance Analytics Fetched Successfully.",
                status_code=200
            ).to_dict()
        except Exception as e:
            logger.error(f"Error creating response data for user {user_id}: {str(e)}")
            return AttendanceResponse(
                data=None,
                message="Error formatting response data",
                status_code=500
            ).to_dict()

    except Exception as e:
        logger.error(f"Error in get_admin_attendance_analytics: {str(e)}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()



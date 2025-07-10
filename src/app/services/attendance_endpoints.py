"""
Attendance Management Endpoints
Combines self attendance and project attendance functionality
"""

import os
import json
import traceback
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Body,
    status as h_status,
    UploadFile
)
from fastapi import Form, File, UploadFile, Depends
from fastapi import status
from fastapi import APIRouter
from fastapi.responses import JSONResponse
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
    DailyAttendanceSummary,
    AttendanceStatus
)
from src.app.services.auth_service import get_current_user, verify_password
from src.app.services.wage_service import get_effective_wage_rate, calculate_and_save_wage
from src.app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create the main attendance router
attendance_router = APIRouter(prefix="/attendance", tags=["Attendance Management"])


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
            punch_in_time=datetime.now(),
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
            attendance_date=new_att.attendance_date,
            punch_in_time=new_att.punch_in_time,
            punch_in_location=LocationData(
                latitude=new_att.punch_in_latitude,
                longitude=new_att.punch_in_longitude,
                address=new_att.punch_in_location_address
            ),
            assigned_projects=[ProjectInfo(**proj) for proj in assigned_projects] if assigned_projects else []
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
    user_id: UUID | None = Form(
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
                    message="Site engineers may only mark today's day off",
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
            if attendance_record.punch_in_time and attendance_record.punch_out_time:
                hours = (attendance_record.punch_out_time - attendance_record.punch_in_time).total_seconds() / 3600
                current_hours = f"{float(hours):.2f} hrs"
            elif attendance_record.punch_in_time and not attendance_record.punch_out_time:
                hours = get_current_hours_worked(attendance_record.punch_in_time)
                current_hours = f"{float(hours):.2f} hrs" if hours is not None else None




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

@attendance_router.post(
    "/project", 
    tags=["Project Attendance"],
    description="""
**Example `Project_Attandance Data` JSON Format**:
```json
{   
    "project_id": "df46d83e-ac87-470d-b1e0-758d32e401a6",
    "item_id": "73c7d1a1-d6ee-479e-8564-567707696138",  
    "sub_contractor_id": "73c7d1a1-d6ee-479e-8564-567707696138",   
    "no_of_labours": 10,   
    "latitude": 23.0225,   
    "longitude": 72.5714,   
    "location_address": "Site A, Ahmedabad",   
    "notes": "Masonry work completed" 
}
"""
)
def mark_project_attendance(
    data: str = Form(..., description="Project attendance data in JSON format"),
    upload_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Parse and extract values from JSON
        payload = json.load(data)
        project_id        = UUID(payload["project_id"])
        item_id           = UUID(payload["item_id"])
        sub_contractor_id = UUID(payload["sub_contractor_id"])
        no_of_labours     = payload["no_of_labours"]
        latitude          = payload["latitude"]
        longitude         = payload["longitude"]
        location_address  = payload.get("location_address", "")
        notes             = payload.get("notes", "")

        if no_of_labours <= 0:
            return AttendanceResponse(
                data=None,
                message="Number of labours must be a positive integer",
                status_code=400
            ).to_dict()

        # Role check
        allowed_roles = [UserRole.SITE_ENGINEER, UserRole.PROJECT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        if current_user.role not in allowed_roles:
            return AttendanceResponse(
                data=None,
                message="Not authorized to mark project attendance",
                status_code=403
            ).to_dict()

        # Coordinates check
        if not validate_coordinates(latitude, longitude):
            return AttendanceResponse(
                data=None,
                message="Invalid coordinates provided",
                status_code=400
            ).to_dict()

        if current_user.role == UserRole.SITE_ENGINEER:
            if not check_user_project_assignment(current_user.uuid, project_id, db):
                return AttendanceResponse(
                    data=None,
                    message="Not assigned to this project",
                    status_code=403
                ).to_dict()

        # Validate project
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        if not project:
            return AttendanceResponse(
                data=None,
                message="Project not found",
                status_code=404
            ).to_dict()

        # Validate sub-contractor
        if not validate_sub_contractor(sub_contractor_id, db):
            return AttendanceResponse(
                data=None,
                message="Sub-contractor not found",
                status_code=404
            ).to_dict()

        sub_contractor = db.query(Person).filter(
            Person.uuid == sub_contractor_id
        ).first()

        today = date.today()

        # Handle photo upload
        photo_path = None
        if upload_photo:
            ext = os.path.splitext(upload_photo.filename)[1]
            filename = f"ATTENDANCE_{uuid4()}{ext}"
            upload_dir = "uploads/attendance_photos"
            os.makedirs(upload_dir, exist_ok=True)
            photo_path = os.path.join(upload_dir, filename)
            with open(photo_path, "wb") as buffer:
                buffer.write(upload_photo.file.read())

        # Save to DB
        new_attendance = ProjectAttendance(
            site_engineer_id=current_user.uuid,
            project_id=project_id,
            item_id=item_id,
            sub_contractor_id=sub_contractor_id,
            no_of_labours=no_of_labours,
            attendance_date=today,
            marked_at=datetime.now(),
            latitude=latitude,
            longitude=longitude,
            location_address=location_address,
            notes=notes,
            # photo_path=photo_path  # ✅ CORRECT FIELD NAME
        )
        if photo_path:
            setattr(new_attendance, "photo_path", photo_path)

        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)

        # Calculate wages
        wage_calculation = calculate_and_save_wage(
            project_id=project_id,
            attendance_id=new_attendance.uuid,
            no_of_labours=no_of_labours,
            attendance_date=today,
            db=db
        )

        wage_info = None
        if wage_calculation:
            wage_info = WageCalculationInfo(
                uuid=wage_calculation.uuid,
                daily_wage_rate=wage_calculation.daily_wage_rate,
                total_wage_amount=wage_calculation.total_wage_amount,
                wage_config_effective_date=wage_calculation.project_daily_wage.effective_date
            )

        response_data = ProjectAttendanceResponse(
            uuid=new_attendance.uuid,
            project=ProjectInfo(uuid=project.uuid, name=project.name),
            sub_contractor=PersonInfo(uuid=sub_contractor.uuid, name=sub_contractor.name),
            no_of_labours=new_attendance.no_of_labours,
            attendance_date=new_attendance.attendance_date,
            photo_path=new_attendance.photo_path,
            marked_at=new_attendance.marked_at,
            location=LocationData(
                latitude=new_attendance.latitude,
                longitude=new_attendance.longitude,
                address=new_attendance.location_address
            ),
            notes=new_attendance.notes,
            wage_calculation=wage_info
        )

        # Log action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="PROJECT_ATTENDANCE",
            entity="project_attendance",
            entity_id=new_attendance.uuid
        )
        db.add(log_entry)
        db.commit()

        return AttendanceResponse(
            data=response_data.model_dump(),
            message="Project attendance marked successfully with wage calculation",
            status_code=201
        ).to_dict()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in mark_project_attendance: {str(e)}")
        logger.error(traceback.format_exc())
        return AttendanceResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()

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
                sub_contractor=PersonInfo(
                    uuid=attendance.sub_contractor.uuid if attendance.sub_contractor else None,
                    name=attendance.sub_contractor.name if attendance.sub_contractor else ""
                ),
                no_of_labours=attendance.no_of_labours or 0,
                attendance_date=attendance.attendance_date,
                photo_path=attendance.photo_path or "",
                marked_at=attendance.marked_at,
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


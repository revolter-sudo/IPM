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
    ProjectAttendanceCreate,
    AttendanceResponse,
    ProjectAttendanceResponse,
    ProjectAttendanceHistoryParams,
    ProjectAttendanceHistoryResponse,
    LocationData,
    ProjectInfo,
    PersonInfo,
    WageCalculationInfo,
    UserInfo,
    ProjectAttendanceSummary,
    DailyAttendanceSummary
)
from src.app.services.auth_service import get_current_user
from src.app.services.wage_service import get_effective_wage_rate, calculate_and_save_wage
from src.app.utils.logging_config import get_logger

logger = get_logger(__name__)

project_attendance_router = APIRouter()


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate latitude and longitude coordinates"""
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


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


@project_attendance_router.post("/project", tags=["Project Attendance"])
def mark_project_attendance(
    attendance_data: ProjectAttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark project attendance for labours with automatic wage calculation.
    Only Site Engineers can mark project attendance for assigned projects.
    """
    try:
        # Check if user has permission (Site Engineer, Project Manager, Admin, Super Admin)
        allowed_roles = [UserRole.SITE_ENGINEER, UserRole.PROJECT_MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN]
        if current_user.role not in allowed_roles:
            return AttendanceResponse(
                data=None,
                message="Not authorized to mark project attendance",
                status_code=403
            ).to_dict()
        
        # Validate coordinates
        if not validate_coordinates(attendance_data.latitude, attendance_data.longitude):
            return AttendanceResponse(
                data=None,
                message="Invalid coordinates provided",
                status_code=400
            ).to_dict()
        
        # Check if user is assigned to the project (for Site Engineers)
        if current_user.role == UserRole.SITE_ENGINEER:
            if not check_user_project_assignment(current_user.uuid, attendance_data.project_id, db):
                return AttendanceResponse(
                    data=None,
                    message="Not assigned to this project",
                    status_code=403
                ).to_dict()
        
        # Validate project exists
        project = db.query(Project).filter(
            Project.uuid == attendance_data.project_id,
            Project.is_deleted.is_(False)
        ).first()
        
        if not project:
            return AttendanceResponse(
                data=None,
                message="Project not found",
                status_code=404
            ).to_dict()
        
        # Validate sub-contractor exists
        if not validate_sub_contractor(attendance_data.sub_contractor_id, db):
            return AttendanceResponse(
                data=None,
                message="Sub-contractor not found",
                status_code=404
            ).to_dict()
        
        # Get sub-contractor details
        sub_contractor = db.query(Person).filter(
            Person.uuid == attendance_data.sub_contractor_id
        ).first()
        
        # Check if attendance can only be marked for current day
        today = date.today()
        
        # Create new project attendance record
        new_attendance = ProjectAttendance(
            site_engineer_id=current_user.uuid,
            project_id=attendance_data.project_id,
            sub_contractor_id=attendance_data.sub_contractor_id,
            no_of_labours=attendance_data.no_of_labours,
            attendance_date=today,
            marked_at=datetime.now(),
            latitude=attendance_data.latitude,
            longitude=attendance_data.longitude,
            location_address=attendance_data.location_address,
            notes=attendance_data.notes
        )
        
        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)
        
        # Calculate and save wage
        wage_calculation = calculate_and_save_wage(
            project_id=attendance_data.project_id,
            attendance_id=new_attendance.uuid,
            no_of_labours=attendance_data.no_of_labours,
            attendance_date=today,
            db=db
        )
        
        # Prepare response data
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
            project=ProjectInfo(
                uuid=project.uuid,
                name=project.name
            ),
            sub_contractor=PersonInfo(
                uuid=sub_contractor.uuid,
                name=sub_contractor.name
            ),
            no_of_labours=new_attendance.no_of_labours,
            attendance_date=new_attendance.attendance_date,
            marked_at=new_attendance.marked_at,
            location=LocationData(
                latitude=new_attendance.latitude,
                longitude=new_attendance.longitude,
                address=new_attendance.location_address
            ),
            notes=new_attendance.notes,
            wage_calculation=wage_info
        )
        
        # Log the action
        log_entry = Log(
            user_id=current_user.uuid,
            action="PROJECT_ATTENDANCE_MARKED",
            details=f"User {current_user.name} marked attendance for {attendance_data.no_of_labours} labours in project {project.name}"
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


@project_attendance_router.get("/project/history", tags=["Project Attendance"])
def get_project_attendance_history(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    start_date: Optional[date] = Query(None, description="Start date for filtering"),
    end_date: Optional[date] = Query(None, description="End date for filtering"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get project attendance history with optional filtering and pagination.
    Site Engineers can only see their own project attendances.
    """
    try:
        query = db.query(ProjectAttendance).filter(
            ProjectAttendance.is_deleted.is_(False)
        )
        
        # Apply role-based filtering
        if current_user.role == UserRole.SITE_ENGINEER:
            # Site Engineers can only see their own attendances
            query = query.filter(ProjectAttendance.site_engineer_id == current_user.uuid)
        elif current_user.role == UserRole.PROJECT_MANAGER:
            # Project Managers can see attendances for their assigned projects
            assigned_projects = db.query(ProjectUserMap.project_id).filter(
                ProjectUserMap.user_id == current_user.uuid,
                ProjectUserMap.is_deleted.is_(False)
            ).subquery()
            query = query.filter(ProjectAttendance.project_id.in_(assigned_projects))
        # Admins and Super Admins can see all attendances (no additional filter)
        
        # Apply filters
        if project_id:
            query = query.filter(ProjectAttendance.project_id == project_id)
        if start_date:
            query = query.filter(ProjectAttendance.attendance_date >= start_date)
        if end_date:
            query = query.filter(ProjectAttendance.attendance_date <= end_date)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        attendances = query.options(
            joinedload(ProjectAttendance.project),
            joinedload(ProjectAttendance.sub_contractor),
            joinedload(ProjectAttendance.site_engineer),
            joinedload(ProjectAttendance.wage_calculation)
        ).order_by(desc(ProjectAttendance.marked_at)).offset(offset).limit(limit).all()
        
        # Prepare response data
        attendance_list = []
        total_labour_days = 0
        unique_contractors = set()
        
        for attendance in attendances:
            total_labour_days += attendance.no_of_labours
            unique_contractors.add(attendance.sub_contractor_id)
            
            # Get wage calculation info
            wage_info = None
            if attendance.wage_calculation:
                wage_calc = attendance.wage_calculation
                wage_info = WageCalculationInfo(
                    uuid=wage_calc.uuid,
                    daily_wage_rate=wage_calc.daily_wage_rate,
                    total_wage_amount=wage_calc.total_wage_amount,
                    wage_config_effective_date=wage_calc.project_daily_wage.effective_date
                )
            
            attendance_data = ProjectAttendanceResponse(
                uuid=attendance.uuid,
                project=ProjectInfo(
                    uuid=attendance.project.uuid,
                    name=attendance.project.name
                ),
                sub_contractor=PersonInfo(
                    uuid=attendance.sub_contractor.uuid,
                    name=attendance.sub_contractor.name
                ),
                no_of_labours=attendance.no_of_labours,
                attendance_date=attendance.attendance_date,
                marked_at=attendance.marked_at,
                location=LocationData(
                    latitude=attendance.latitude,
                    longitude=attendance.longitude,
                    address=attendance.location_address
                ),
                notes=attendance.notes,
                wage_calculation=wage_info
            )
            attendance_list.append(attendance_data)
        
        # Calculate summary
        summary = ProjectAttendanceSummary(
            total_labour_days=total_labour_days,
            unique_contractors=len(unique_contractors),
            average_daily_labours=total_labour_days / len(attendances) if attendances else 0
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

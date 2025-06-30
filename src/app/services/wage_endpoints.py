"""
Wage Management Endpoints
Handles wage configuration, history, and reporting functionality
"""

import os
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
    ProjectDailyWage,
    ProjectAttendanceWage,
    ProjectAttendance,
    User,
    Project,
    Log
)
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.wage_schemas import (
    WageConfigurationCreate,
    WageConfigurationUpdate,
    WageResponse,
    WageConfigurationResponse,
    WageSummaryParams,
    WageSummaryResponse,
    WageHistoryResponse,
    WageRateHistoryParams,
    WageRateHistoryResponse,
    AttendanceWageDetailsResponse,
    WageCalculationDetail,
    WageSummary,
    WageRateChange,
    MonthlySummary,
    AttendanceInfo,
    WageCalculationInfo,
    WageConfigurationInfo,
    UserInfo
)
from src.app.services.auth_service import get_current_user
from src.app.services.wage_service import (
    check_wage_configuration_permission,
    get_effective_wage_rate,
    calculate_and_save_wage
)
from src.app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create the main wage router
wage_router = APIRouter(prefix="/wage", tags=["Wage Management"])


@wage_router.post("/projects/{project_id}/daily-wage", tags=["Wage Configuration"])
def configure_daily_wage_rate(
    project_id: UUID,
    wage_data: WageConfigurationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Configure daily wage rate for a project.
    Only Admin, Project Manager, and Super Admin can configure wage rates.
    """
    try:
        # Check permissions
        if not check_wage_configuration_permission(current_user.role):
            return WageResponse(
                data=None,
                message="Not authorized to configure wage rates",
                status_code=403
            ).to_dict()
        
        # Validate project exists
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        
        if not project:
            return WageResponse(
                data=None,
                message="Project not found",
                status_code=404
            ).to_dict()
        
        # Set effective date to today if not provided
        effective_date = wage_data.effective_date or date.today()
        
        # Check if wage rate already exists for this project and date
        existing_wage = db.query(ProjectDailyWage).filter(
            ProjectDailyWage.project_id == project_id,
            ProjectDailyWage.effective_date == effective_date,
            ProjectDailyWage.is_deleted.is_(False)
        ).first()
        
        if existing_wage:
            return WageResponse(
                data=None,
                message=f"Wage rate already configured for this project on {effective_date}",
                status_code=400
            ).to_dict()
        
        # Create new wage configuration
        new_wage_config = ProjectDailyWage(
            project_id=project_id,
            daily_wage_rate=wage_data.daily_wage_rate,
            effective_date=effective_date,
            configured_by_user_id=current_user.uuid
        )
        
        db.add(new_wage_config)
        db.commit()
        db.refresh(new_wage_config)
        
        # Prepare response
        response_data = WageConfigurationResponse(
            uuid=new_wage_config.uuid,
            project_id=new_wage_config.project_id,
            daily_wage_rate=new_wage_config.daily_wage_rate,
            effective_date=new_wage_config.effective_date,
            configured_by=UserInfo(
                uuid=current_user.uuid,
                name=current_user.name,
                role=current_user.role
            ),
            created_at=new_wage_config.created_at
        )
        
        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="WAGE_RATE_CONFIGURED",
            entity="project_daily_wage",
            entity_id=new_wage_config.uuid,
            # details=f"User {current_user.name} configured wage rate ₹{wage_data.daily_wage_rate} for project {project.name} effective from {effective_date}"
        )
        db.add(log_entry)
        db.commit()
        
        return WageResponse(
            data=response_data.model_dump(),
            message="Daily wage rate configured successfully",
            status_code=201
        ).to_dict()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error in configure_daily_wage_rate: {str(e)}")
        logger.error(traceback.format_exc())
        return WageResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()


@wage_router.get("/projects/{project_id}/daily-wage", tags=["Wage Configuration"])
def get_current_wage_rate(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current active wage rate for a project.
    """
    try:
        # Validate project exists
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        
        if not project:
            return WageResponse(
                data=None,
                message="Project not found",
                status_code=404
            ).to_dict()
        
        # Get current effective wage rate
        current_wage = get_effective_wage_rate(project_id, date.today(), db)
        
        if not current_wage:
            return WageResponse(
                data=None,
                message="No wage rate configured for this project",
                status_code=404
            ).to_dict()
        
        # Get configured by user details
        configured_by_user = db.query(User).filter(
            User.uuid == current_wage.configured_by_user_id
        ).first()
        
        response_data = WageConfigurationResponse(
            uuid=current_wage.uuid,
            project_id=current_wage.project_id,
            daily_wage_rate=current_wage.daily_wage_rate,
            effective_date=current_wage.effective_date,
            configured_by=UserInfo(
                uuid=configured_by_user.uuid,
                name=configured_by_user.name,
                role=configured_by_user.role
            ),
            created_at=current_wage.created_at
        )
        
        return WageResponse(
            data=response_data.model_dump(),
            message="Current wage rate retrieved successfully",
            status_code=200
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error in get_current_wage_rate: {str(e)}")
        return WageResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()


@wage_router.get("/projects/{project_id}/daily-wage/history", tags=["Wage Configuration"])
def get_wage_rate_history(
    project_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get wage rate history for a project with pagination.
    """
    try:
        # Validate project exists
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        
        if not project:
            return WageResponse(
                data=None,
                message="Project not found",
                status_code=404
            ).to_dict()
        
        # Get wage rate history
        query = db.query(ProjectDailyWage).filter(
            ProjectDailyWage.project_id == project_id,
            ProjectDailyWage.is_deleted.is_(False)
        )
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        wage_rates = query.options(
            joinedload(ProjectDailyWage.configured_by)
        ).order_by(desc(ProjectDailyWage.effective_date)).offset(offset).limit(limit).all()
        
        # Prepare response data
        wage_rate_list = []
        for wage_rate in wage_rates:
            wage_data = WageConfigurationResponse(
                uuid=wage_rate.uuid,
                project_id=wage_rate.project_id,
                daily_wage_rate=wage_rate.daily_wage_rate,
                effective_date=wage_rate.effective_date,
                configured_by=UserInfo(
                    uuid=wage_rate.configured_by.uuid,
                    name=wage_rate.configured_by.name,
                    role=wage_rate.configured_by.role
                ),
                created_at=wage_rate.created_at
            )
            wage_rate_list.append(wage_data)
        
        response_data = WageRateHistoryResponse(
            wage_rates=wage_rate_list,
            total_count=total_count,
            page=page,
            limit=limit
        )
        
        return WageResponse(
            data=response_data.model_dump(),
            message="Wage rate history retrieved successfully",
            status_code=200
        ).to_dict()
        
    except Exception as e:
        logger.error(f"Error in get_wage_rate_history: {str(e)}")
        return WageResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()

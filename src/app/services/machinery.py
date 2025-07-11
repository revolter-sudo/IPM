import traceback
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from fastapi import Depends
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from pydantic import ValidationError
from src.app.database.database import get_db
from src.app.database.models import (
    User,
    Log,
    Machinery,
)
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.machinery_schemas import (
    MachinePunchInRequest, 
    MachineryPunchInResponse, 
    APIResponse, 
    MachinePunchOutRequest, 
    MachineryPunchOutResponse,
    MachineryLogResponse
)
from src.app.services.auth_service import get_current_user
from src.app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create the main attendance router
machinery_router = APIRouter(prefix="/machinery")

# Machinery Punch In API

@machinery_router.post(
    "/machine/start", 
    tags=["Machinery"]
)
def punch_in_machine(
    req: MachinePunchInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark machine start time. Only allows one active usage per machine/project/sub-contractor.
    """
    try:
        # Only certain roles allowed
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SITE_ENGINEER]:
            return APIResponse(
                data=None,
                message="You do not have permission to perform this action.",
                status_code=403
            ).to_dict()

        # Prevent duplicate active machinery log (no end_time)
        exists = db.query(Machinery).filter(
            Machinery.project_id == req.project_id,
            Machinery.sub_contractor_id == req.sub_contractor_id,
            Machinery.item_id == req.item_id,
            Machinery.end_time.is_(None),
            Machinery.is_deleted.is_(False)
        ).first()
        if exists:
            return APIResponse(
                data=None,
                message="Machine already running (active entry exists).",
                status_code=400
            ).to_dict()

        # Create new entry
        new_machinery = Machinery(
            uuid=uuid4(),
            project_id=req.project_id,
            sub_contractor_id=req.sub_contractor_id,
            item_id=req.item_id,
            start_time=datetime.utcnow(),
            created_by=current_user.uuid,
            created_at=datetime.utcnow(),
            is_deleted=False,
        )
        db.add(new_machinery)
        db.commit()
        db.refresh(new_machinery)

        # Prepare response
        resp_data = MachineryPunchInResponse(
            uuid=new_machinery.uuid,
            project_id=new_machinery.project_id,
            sub_contractor_id=new_machinery.sub_contractor_id,
            item_id=new_machinery.item_id,
            start_time=new_machinery.start_time,
            created_by=new_machinery.created_by
        )

        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="MACHINE_PUNCH_IN",
            entity="machinery",
            entity_id=new_machinery.uuid
        )
        db.add(log_entry)
        db.commit()

        return APIResponse(
            data=resp_data.model_dump(),
            message="Machine started successful.",
            status_code=201
        ).to_dict()

    except Exception as e:
        db.rollback()
        # log error
        print("Error in start_machine:", e)
        print(traceback.format_exc())
        return APIResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()
    
# Machinery Punch Out API
@machinery_router.post(
    "/machine/end", 
    tags=["Machinery"]
)
def punch_out_machine(
    req: MachinePunchOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark machine end time by updating end_time for an active machinery log.
    """
    try:
        # Only certain roles allowed
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SITE_ENGINEER]:
            return APIResponse(
                data=None,
                message="You do not have permission to perform this action.",
                status_code=403
            ).to_dict()

        # Find the active machinery log by uuid
        machinery = db.query(Machinery).filter(
            Machinery.uuid == req.uuid,
            Machinery.is_deleted.is_(False)
        ).first()

        if not machinery:
            return APIResponse(
                data=None,
                message="No machinery log found with the given UUID.",
                status_code=404
            ).to_dict()

        if machinery.end_time is not None:
            return APIResponse(
                data=None,
                message="This machine usage has already been ended.",
                status_code=400
            ).to_dict()

        # Mark end time
        machinery.end_time = datetime.utcnow()
        db.add(machinery)
        db.commit()
        db.refresh(machinery)

        # Calculate duration
        duration_minutes = None
        if machinery.start_time and machinery.end_time:
            duration = machinery.end_time - machinery.start_time
            duration_minutes = round(duration.total_seconds() / 60, 2)

        # Prepare response
        resp_data = MachineryPunchOutResponse(
            uuid=machinery.uuid,
            end_time=machinery.end_time,
            duration_minutes=duration_minutes
        )

        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="MACHINE_PUNCH_OUT",
            entity="machinery",
            entity_id=machinery.uuid
        )
        db.add(log_entry)
        db.commit()

        return APIResponse(
            data=resp_data.model_dump(),
            message="Machine end successful.",
            status_code=200
        ).to_dict()

    except Exception as e:
        db.rollback()
        print("Error in end_machine:", e)
        print(traceback.format_exc())
        return APIResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()
    
@machinery_router.delete(
    "/machine/{uuid}",
    tags=["Machinery"]
)
def delete_machine_log(
    uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    cancel a machine log by uuid.(5 minites grace period)
    """
    try:
        #fetch the machinery log
        machinery = db.query(Machinery).filter(
            Machinery.uuid == uuid,
            Machinery.is_deleted.is_(False)
        ).first()

        if not machinery:
            return APIResponse(
                data=None,
                message="No machinery log found with the given UUID.",
                status_code=404
            ).to_dict()
        
        # Time check: allow deletion only within 5 minutes of start
        current_time = datetime.utcnow()
        start_time = machinery.start_time

        time_diff = current_time - start_time
        if time_diff > timedelta(minutes=5):
            return APIResponse(
                data=None,
                message=f"Cannot delete machinery log after 5 minutes of start time. Time elapsed: {int(time_diff.total_seconds() / 60)} minutes",
                status_code=400
            ).to_dict()
        
        #soft delete the machinery log
        machinery.is_deleted = True
        db.commit()

        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="MACHINE_LOG_DELETED",
            entity="machinery",
            entity_id=machinery.uuid
        )
        db.add(log_entry)
        db.commit()

        return APIResponse(
            data=None,
            message="Machinery log deleted successfully.",
            status_code=200
        ).to_dict()
    
    except Exception as e:
        db.rollback()
        print("Error in delete_machine_log:", e)
        print(traceback.format_exc())
        return APIResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()
    
@machinery_router.get(
    "/machine/logs",
    tags=["Machinery"]
)
def get_machine_history(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    sub_contractor_id: Optional[UUID] = Query(None, description="Filter by sub-contractor ID"),
    item_id: Optional[UUID] = Query(None, description="Filter by item ID"),
    created_by: Optional[UUID] = Query(None, description="Filter by user who created the log"),
    month: Optional[int] = Query(None, description="Filter by month (1-12)"),
    from_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="Filter to this date (YYYY-MM-DD)"),
    recent: Optional[bool] = Query(False, description="If true, only return logs from the last 30 days"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get machine usage history with optional filters.
    """
    try:
        query = db.query(Machinery).filter(
            Machinery.is_deleted.is_(False)
        )

        # role-based access control
        if  current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            query = query.filter(
                Machinery.created_by == current_user.uuid
            )

        # Pagination
        offset = (page - 1) * limit
        machinery_logs = (
            query.options(
                joinedload(Machinery.project),
                joinedload(Machinery.sub_contractor),
                joinedload(Machinery.item)
            )
            .order_by(desc(Machinery.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        

        # Apply filters    
        if project_id:
            query = query.filter(Machinery.project_id == project_id)
        if sub_contractor_id:
            query = query.filter(Machinery.sub_contractor_id == sub_contractor_id)
        if item_id:
            query = query.filter(Machinery.item_id == item_id)

        if created_by:
            query = query.filter(Machinery.created_by == created_by)

        if month:
            if month < 1 or month > 12:
                return APIResponse(
                    data=None,
                    message="Month must be between 1 and 12.",
                    status_code=400
                ).to_dict()
            query = query.filter(func.extract('month', Machinery.start_time) == month)
        
        if from_date:
            if not isinstance(from_date, date):
                return APIResponse(
                    data=None,
                    message="Invalid from_date format. Use YYYY-MM-DD.",
                    status_code=400
                ).to_dict()
            query = query.filter(Machinery.start_time >= datetime.combine(from_date, datetime.min.time()))
        
        if to_date:
            if not isinstance(to_date, date):
                return APIResponse(
                    data=None,
                    message="Invalid to_date format. Use YYYY-MM-DD.",
                    status_code=400
                ).to_dict()
            query = query.filter(Machinery.start_time <= datetime.combine(to_date, datetime.max.time()))

        if recent:
            query = query.order_by(desc(Machinery.created_at)).limit(5)


        # Fetch all matching records
        machinery_logs = query.all()

        # Convert SQLAlchemy models to Pydantic models
        logs_data = [MachineryLogResponse.from_orm(log) for log in machinery_logs]

        return APIResponse(
            data={"logs": [log.model_dump() for log in logs_data]},
            message="Machine logs fetched successfully.",
            status_code=200
        ).to_dict()

    except Exception as e:
        print("Error in get_machine_history:", e)
        print(traceback.format_exc())
        return APIResponse(
            data=None,
            message=f"Internal server error: {str(e)}",
            status_code=500
        ).to_dict()
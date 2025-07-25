import traceback
import os
import json
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from fastapi import (
    APIRouter,
    Depends,
    Query,
    File,
    UploadFile,
    Form
)
from src.app.utils.timezone_utils import get_ist_now
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from src.app.database.database import get_db
from src.app.database.models import (
    User,
    Log,
    Machinery,
    MachineryPhotos
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
    tags=["Machinery"],
    status_code=201,
    description="""
Mark machine start time.

**Request:**  
Send as `multipart/form-data`:

- **Field `req`** (stringified JSON):  
```json
{
  "project_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ef",         // Required: UUID of the project
  "sub_contractor_id": "c3d4e5f6-7890-abcd-ef01-345678902bcd",  // Required: UUID of the sub-contractor
  "item_id": "b2c3d4e5-f678-90ab-cdef-2345678901fa",            // Required: UUID of the machinery/item
  "notes": "Starting mixer for slab pour."                       // Optional: Any notes for this usage
}

Field photo (file, optional): Upload a machinery photo if available.

Notes:

Only one "active" (not ended) machinery entry is allowed per machine/project/sub-contractor.

Returns the full record, including generated UUID and saved photo path.
"""
)
def punch_in_machine(
    req: str = Form(..., description="Stringified JSON of MachinePunchInRequest"),
    photos:List[UploadFile] = File(None, description="One or more machinery photos (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark machine start time. Accepts multipart form: 'req' (JSON string), 'photo' (file, optional).
    Only allows one active usage per machine/project/sub-contractor.
    """
    try:
        # Only certain roles allowed
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SITE_ENGINEER]:
            return APIResponse(
                data=None,
                message="You do not have permission to perform this action.",
                status_code=403
            ).to_dict()

        # Parse and validate the JSON
        try:
            data = json.loads(req)
            req_obj = MachinePunchInRequest(**data)
        except Exception as e:
            return APIResponse(
                data=None,
                message=f"Invalid request data: {e}",
                status_code=400
            ).to_dict()

        # Prevent duplicate active machinery log (no end_time)
        exists = db.query(Machinery).filter(
            Machinery.project_id == req_obj.project_id,
            Machinery.sub_contractor_id == req_obj.sub_contractor_id,
            Machinery.item_id == req_obj.item_id,
            Machinery.end_time.is_(None),
            Machinery.is_deleted.is_(False)
        ).first()
        if exists:
            return APIResponse(
                data=None,
                message="Machine already running (active entry exists).",
                status_code=400
            ).to_dict()
        
        # Create new machinery entry first
        new_machinery = Machinery(
            uuid=uuid4(),
            project_id=req_obj.project_id,
            sub_contractor_id=req_obj.sub_contractor_id,
            item_id=req_obj.item_id,
            start_time=datetime.utcnow(),
            notes=req_obj.notes,
            created_by=current_user.uuid,
            created_at=datetime.utcnow(),
            is_deleted=False,
        )
        db.add(new_machinery)
        db.commit()
        db.refresh(new_machinery)

        # Handle photo upload if provided
        photo_paths = []
        if photos:
            upload_dir = "uploads/machinery_photos"
            os.makedirs(upload_dir, exist_ok=True)
            for photo in photos:
                ext = os.path.splitext(photo.filename)[1]
                fname = f"Machinery_{str(uuid4())}{ext}"
                photo_path = os.path.join(upload_dir, fname)
                with open(photo_path, "wb") as buffer:
                    buffer.write(photo.file.read())
                # Save each photo in MachineryPhotos table
                photo_obj = MachineryPhotos(
                    uuid=uuid4(),
                    machinery_id=new_machinery.uuid,
                    photo_path=photo_path
                )
                db.add(photo_obj)
                photo_paths.append(photo_path)
            db.commit()  # Commit photo entries
            
            
            
            



        # Prepare response
        resp_data = {
            "uuid": str(new_machinery.uuid),
            "project_id": str(new_machinery.project_id),
            "sub_contractor_id": str(new_machinery.sub_contractor_id),
            "item_id": str(new_machinery.item_id),
            "start_time": new_machinery.start_time.isoformat(),
            "notes": new_machinery.notes,
            "photo_paths": photo_paths,  # List of uploaded photo paths
            "created_by": str(new_machinery.created_by)
        }

        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="MACHINE_PUNCH_IN",
            entity="machinery",
            entity_id=new_machinery.uuid
        )
        db.add(log_entry)
        db.commit()
        
        current_time = get_ist_now()
        logger.info(f"[{current_user.name}] have started machine at [{current_time}]")
        

        return APIResponse(
            data=resp_data,  # resp_data is already a dictionary, no need for model_dump()
            message="Machine started successfully.",
            status_code=201
        ).to_dict()

    except Exception as e:
        db.rollback()
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
    tags=["Machinery"],
    status_code=200,
    description="""
Mark machine end time and upload one or more end photos.

**Request:**  
- `req`: Stringified JSON with `{ "uuid": "<machinery_uuid>" }`
- `photos`: One or more files (optional), uploaded as `photos`  
"""
)
def punch_out_machine(
    req: str = Form(..., description="Stringified JSON of MachinePunchOutRequest"),
    photos: List[UploadFile] = File(None, description="Optional machinery photos for end time"),
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
        
        # Parse the JSON
        try:
            data = json.loads(req)
            req_obj = MachinePunchOutRequest(**data)
        except Exception as e:
            return APIResponse(
                data=None,
                message=f"Invalid request data: {e}",
                status_code=400
            ).to_dict()

        # Find the active machinery log by uuid
        machinery = db.query(Machinery).filter(
            Machinery.uuid == req_obj.uuid,
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

        # Handle photo upload if provided
        photo_paths = []
        if photos:
            upload_dir = "uploads/machinery_photos"
            os.makedirs(upload_dir, exist_ok=True)
            for photo in photos:
                ext = os.path.splitext(photo.filename)[1]
                fname = f"MachineryEnd_{str(uuid4())}{ext}"
                photo_path = os.path.join(upload_dir, fname)
                with open(photo_path, "wb") as buffer:
                    buffer.write(photo.file.read())
                photo_obj = MachineryPhotos(
                    uuid=uuid4(),
                    machinery_id=machinery.uuid,
                    photo_path=photo_path
                )
                db.add(photo_obj)
                photo_paths.append(photo_path)
            db.commit()  # Commit all new photo records

        # Calculate duration
        duration_str = None
        if machinery.start_time and machinery.end_time:
            duration = machinery.end_time - machinery.start_time
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Prepare response
        resp_data = {
            "uuid": str(machinery.uuid),
            "end_time": machinery.end_time.isoformat(),
            "duration": duration_str,
            "end_photo_paths": photo_paths
        }

        # Log the action
        log_entry = Log(
            performed_by=current_user.uuid,
            action="MACHINE_PUNCH_OUT",
            entity="machinery",
            entity_id=machinery.uuid
        )
        db.add(log_entry)
        db.commit()
        
        current_time = get_ist_now()
        logger.info(f"[{current_user.name}] have stopped machine at [{current_time}]")

        return APIResponse(
            data=resp_data,  # resp_data is already a dictionary
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
        
        logger.info(f"[{current_user.name}] have delete machine logs of [{uuid}]")

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
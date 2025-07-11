from typing import Optional, Any, List
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class MachinePunchInRequest(BaseModel):
    project_id: UUID
    sub_contractor_id: UUID
    item_id: UUID

class MachineryPunchInResponse(BaseModel):
    uuid: UUID
    project_id: UUID
    sub_contractor_id: UUID
    item_id: UUID
    start_time: datetime
    created_by: UUID

class MachinePunchOutRequest(BaseModel):
    uuid: UUID  # UUID of the machinery log to punch out

class MachineryPunchOutResponse(BaseModel):
    uuid: UUID
    end_time: datetime
    duration_minutes: Optional[float] = None  # Optional: Show duration if start_time exists

class MachineryLogResponse(BaseModel):
    uuid: UUID
    project_id: UUID
    sub_contractor_id: UUID
    item_id: UUID
    start_time: datetime
    end_time: Optional[datetime] = None
    created_by: UUID
    created_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True

class APIResponse(BaseModel):
    data: Optional[dict] = None
    message: str
    status_code: int

    def to_dict(self):
        return self.model_dump()
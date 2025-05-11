from typing import Optional, Any, List, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class AdminPanelResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }


class DefaultConfigCreate(BaseModel):
    item_id: UUID
    admin_amount: float


class DefaultConfigUpdate(BaseModel):
    item_id: UUID
    admin_amount: float


class DefaultConfigResponse(BaseModel):
    uuid: UUID
    item_id: UUID
    admin_amount: float
    created_at: datetime

    model_config = {"from_attributes": True}

class ProjectUserMap(BaseModel):
    uuid: UUID
    user_id: UUID
    project_id: UUID

class ProjectItemMap(BaseModel):
    uuid: UUID
    project_id: UUID
    item_id: UUID

class ProjectItemResponse(BaseModel):
    uuid: UUID
    name: Optional[str] = None
    category: Optional[str] = None
    list_tag: Optional[str] = None
    has_additional_info: Optional[bool] = None

class UserItemMapResponse(BaseModel):
    uuid: UUID
    name: Optional[str] = None
    category: Optional[str] = None
    list_tag: Optional[str] = None
    has_additional_info: Optional[bool] = None
    item_balance: float = 0.0


class LogResponse(BaseModel):
    uuid: UUID
    entity: str
    action: str
    entity_id: UUID
    performed_by: UUID
    timestamp: datetime
    performer_name: Optional[str] = None

    model_config = {"from_attributes": True}

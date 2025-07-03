from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AdminPanelResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code,
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


class PaymentStatusAnalytics(BaseModel):
    status: str
    count: int
    total_amount: float
    percentage: float


class ProjectPaymentAnalyticsResponse(BaseModel):
    project_id: UUID
    project_name: str
    total_payments: int
    total_amount: float
    status_analytics: List[PaymentStatusAnalytics]


class ItemAnalytics(BaseModel):
    item_name: str
    estimation: float
    current_expense: float


class ProjectItemAnalyticsResponse(BaseModel):
    project_id: UUID
    project_name: str
    items_analytics: List[ItemAnalytics]


class ProjectUserMap(BaseModel):
    uuid: UUID
    user_id: UUID
    project_id: UUID


class ProjectItemMap(BaseModel):
    uuid: UUID
    project_id: UUID
    item_id: UUID


class ProjectUserItemMapResponse(BaseModel):
    uuid: UUID
    project_id: UUID
    user_id: UUID
    item_id: UUID


class ProjectUserItemMapCreate(BaseModel):
    project_id: UUID
    user_id: UUID
    item_ids: List[UUID]


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


class UserProjectItemResponse(BaseModel):
    item_id: UUID
    name: Optional[str]
    category: Optional[str]
    list_tag: Optional[str]
    has_additional_info: Optional[bool]


class SalaryCreateRequest(BaseModel):
    user_id: UUID
    project_id: UUID
    month: str
    amount: float = Field(default=0.0, ge=0.0)


class SalaryUpdateRequest(BaseModel):
    user_id: UUID
    project_id: UUID
    month: str
    amount: float = Field(default=0.0, ge=0.0)


class SalaryResponse(BaseModel):
    uuid: UUID
    user_id: UUID
    project_id: UUID
    month: str
    amount: float = Field(default=0.0, ge=0.0)

    model_config = {"from_attributes": True}

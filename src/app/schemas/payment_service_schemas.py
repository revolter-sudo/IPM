from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from enum import Enum


class PaymentStatus(Enum):
    approved = "approved"
    declined = "declined"
    pending = "pending"


class PaymentRequest(BaseModel):
    amount: float
    description: Optional[str] = None
    project_id: UUID
    status: PaymentStatus


from pydantic import BaseModel, Field
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


class CreatePerson(BaseModel):
    name: str
    account_number: str = Field(..., min_length=7, max_length=17, description="Account number must be 7 to 17 digits long")
    ifsc_code: str = Field(..., min_length=11, max_length=11, description="IFSC code must be exactly 11 characters long")
    phone_number: str = Field(..., min_length=10, max_length=10, description="Phone number must be exactly 10 digits")

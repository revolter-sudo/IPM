from enum import Enum
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


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
    account_number: str = Field(
        ...,
        min_length=7,
        max_length=17,
        description="Account number must be 7 to 17 digits long",
    )
    ifsc_code: str = Field(
        ...,
        min_length=11,
        max_length=11,
        description="IFSC code must be exactly 11 characters long",
    )
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=10,
        description="Phone number must be exactly 10 digits",
    )


class PersonDetail(BaseModel):
    uuid: UUID
    name: str
    account_number: str
    ifsc_code: str
    phone_number: str


class PaymentsResponse(BaseModel):
    uuid: UUID
    amount: float
    description: Optional[str] = None
    project_id: UUID
    created_by: UUID
    status: str
    remarks: Optional[str] = None
    person: Optional[UUID] = None
    file: Optional[str]


class PaymentServiceResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }

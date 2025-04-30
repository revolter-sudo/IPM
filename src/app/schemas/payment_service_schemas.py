from enum import Enum
from typing import Optional, Any, List, Dict
from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field, field_validator


class PaymentStatus(str, Enum):
    REQUESTED = "requested"
    VERIFIED = "verified"
    APPROVED = "approved"
    TRANSFERRED = "transferred"
    DECLINED = "declined"


class ItemListTag(str, Enum):
    khatabook = "khatabook"
    payment = "payment"


class UpdateItemSchema(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    list_tag: Optional[str] = None
    has_additional_info: Optional[bool] = None


class PaymentRequest(BaseModel):
    amount: float
    description: Optional[str] = None
    project_id: UUID
    status: PaymentStatus


class CreatePerson(BaseModel):
    name: str
    account_number: Optional[str] = Field(
        None,
        min_length=11,
        max_length=16,
        pattern=r'^\d+$',
        description="Account number must be 11 to 16 digits long and contain only numbers",
    )
    ifsc_code: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
        description="IFSC code must be exactly 11 characters long",
    )
    phone_number: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        description="Phone number must be exactly 10 digits",
    )
    upi_number: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        description="upi number must be exactly 10 digits",
    )
    parent_id: Optional[UUID] = None

    @field_validator('account_number')
    def validate_account_number(cls, v):
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("Account number must contain only digits")
        # Additional validation for common Indian bank account number lengths
        if len(v) < 11 or len(v) > 16:
            raise ValueError("Account number must be between 11 and 16 digits")
        return v


class UpdatePerson(BaseModel):
    name: Optional[str] = None
    account_number: Optional[str] = Field(
        None,
        min_length=11,
        max_length=16,
        pattern=r'^\d+$',
        description="Account number must be 11 to 16 digits long and contain only numbers",
    )
    ifsc_code: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
        description="IFSC code must be exactly 11 characters long",
    )
    phone_number: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        description="Phone number must be exactly 10 digits",
    )
    upi_number: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        description="UPI number must be exactly 10 digits",
    )
    parent_id: Optional[UUID] = None

    @field_validator('account_number')
    def validate_account_number(cls, v):
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("Account number must contain only digits")
        # Additional validation for common Indian bank account number lengths
        if len(v) < 11 or len(v) > 16:
            raise ValueError("Account number must be between 11 and 16 digits")
        return v


class PaymentUpdateSchema(BaseModel):
    amount: float = Field(..., description="New payment amount")
    remark: str = Field(..., description="Remark for this update")


class CreatePaymentRequest(BaseModel):
    amount: float
    project_id: UUID
    status: PaymentStatus
    item_uuids: Optional[List[UUID]] = []
    description: Optional[str] = None
    remarks: Optional[str] = None
    person: Optional[UUID] = None
    self_payment: bool  # New Field
    latitude: float
    longitude: float
    priority_id: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 100.5,
                "project_id": "f82481f7-ec85-4790-8868-aa9a24906d36",
                "status": "approved",
                "item_uuids": ["6f3e55da-1734-42d6-90ef-ae1b3e9ef759"],
                "description": "Purchase of materials",
                "remarks": "Urgent requirement",
                "person": "e194159d-ce26-43e1-ace0-db4b00d4c43e",
                "self_payment": True,  # Self-payment flag
                "latitude": 22.5726,
                "longitude": 88.3639,
                "priority_id": "9c4f2ae4-a046-421f-b52f-a50c169165c3"
            }
        }


class PersonDetail(BaseModel):
    uuid: UUID
    name: str
    account_number: str
    ifsc_code: str
    phone_number: str


class StatusDatePair(BaseModel):
    status: str
    date: str  # We'll store a string like "04-03-2025"
    created_by: str


class PaymentsResponse(BaseModel):
    uuid: UUID
    amount: float
    description: Optional[str] = None
    project: Optional[Dict[str, Optional[str]]] = None
    person: Optional[Dict[str, Optional[str]]] = None
    payment_details: Optional[Dict[str, Optional[str]]] = None
    created_by: Optional[Dict[str, Optional[str]]] = None
    files: List[str] = []
    items: List[str] = []
    remarks: Optional[str] = None

    # We'll store status + date pairs in this list
    status_history: List[StatusDatePair]

    # A single "current_status" for the latest Payment.status
    current_status: Optional[str] = None

    created_at: str
    update_remarks: Optional[str] = None
    latitude: float
    longitude: float
    transferred_date: Optional[str] = None
    payment_history: Any = None


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

from enum import Enum
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class ProjectType(str, Enum):
    ROOFTOP = "ROOFTOP"
    INDUSTRIAL = "INDUSTRIAL"


class InquiryCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Name must be between 2 and 100 characters")
    phone_number: str = Field(..., min_length=10, max_length=15, description="Phone number must be between 10 and 15 digits")
    project_type: ProjectType = Field(..., description="Type of project")
    state: str = Field(..., min_length=2, max_length=50, description="State must be between 2 and 50 characters")
    city: str = Field(..., min_length=2, max_length=50, description="City must be between 2 and 50 characters")

    @field_validator("phone_number")
    def validate_phone_number(cls, value):
        # Remove any non-digit characters for validation
        digits_only = ''.join(filter(str.isdigit, value))
        
        if len(digits_only) < 10:
            raise ValueError("Phone number must contain at least 10 digits")
        if len(digits_only) > 15:
            raise ValueError("Phone number must not exceed 15 digits")
        
        # Return the cleaned phone number (digits only)
        return digits_only

    @field_validator("name")
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("Name cannot be empty or just whitespace")
        return value.strip()

    @field_validator("state")
    def validate_state(cls, value):
        if not value.strip():
            raise ValueError("State cannot be empty or just whitespace")
        return value.strip()

    @field_validator("city")
    def validate_city(cls, value):
        if not value.strip():
            raise ValueError("City cannot be empty or just whitespace")
        return value.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "phone_number": "9876543210",
                "project_type": "ROOFTOP",
                "state": "Maharashtra",
                "city": "Mumbai"
            }
        }


class InquiryResponse(BaseModel):
    uuid: UUID
    name: str
    phone_number: str
    project_type: str
    state: str
    city: str
    created_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True


class InquiryServiceResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def model_dump(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }


class InquiryListResponse(BaseModel):
    inquiries: list[InquiryResponse]
    total_count: int
    page: int
    page_size: int

    class Config:
        from_attributes = True

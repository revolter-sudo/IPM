from enum import Enum
from uuid import UUID
from typing import Any
from pydantic import BaseModel, field_validator
from src.app.schemas.payment_service_schemas import CreatePerson


class UserRole(str, Enum):
    SUB_CONTRACTOR = "SubContractor"
    SITE_ENGINEER = "SiteEngineer"
    PROJECT_MANAGER = "ProjectManager"
    ADMIN = "Admin"
    ACCOUNTANT = "Accountant"
    INSPECTOR = "Inspector"
    RECORD_LIVE_PAYMENT = "RecordLivePayment"
    SUPER_ADMIN = "SuperAdmin"


class ForgotPasswordRequest(BaseModel):
    phone: int
    new_password: str


class UserCreate(BaseModel):
    name: str
    phone: int
    password: str
    role: UserRole
    person: CreatePerson

    @field_validator("phone")
    def validate_phone(cls, value):
        if len(str(value)) != 10:
            raise ValueError("Phone number must be between 10")
        return value


class UserLogin(BaseModel):
    phone: int
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    uuid: UUID
    name: str
    phone: int
    role: str
    photo_path: Any

    def to_dict(self):
        """
        Convert the Pydantic model instance into a dictionary.
        """
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "phone": self.phone,
            "role": self.role,
            "photo_path": self.photo_path
        }


class AuthServiceResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }

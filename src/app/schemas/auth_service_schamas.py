from pydantic import BaseModel, field_validator
from uuid import UUID
from enum import Enum


class UserRole(str, Enum):
    SUB_CONTRACTOR = "SubContractor"
    SITE_ENGINEER = "SiteEngineer"
    PROJECT_MANAGER = "ProjectManager"
    ADMIN = "Admin"
    ACCOUNTANT = "Accountant"
    INSPECTOR = "Inspector"
    RECORD_LIVE_PAYMENT = "RecordLivePayment"
    SUPER_ADMIN = "SuperAdmin"


class UserCreate(BaseModel):
    name: str
    phone: int
    password: str
    role: UserRole

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

    def to_dict(self):
        """
        Convert the Pydantic model instance into a dictionary.
        """
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "phone": self.phone,
            "role": self.role,
        }

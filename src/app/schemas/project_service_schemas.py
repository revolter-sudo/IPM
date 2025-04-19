from typing import Optional, Any, List
from uuid import UUID

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    balance: float

    def to_dict(self):
        """
        Convert the Pydantic model instance into a dictionary.
        """
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "balance": self.balance,
        }


class ItemResponse(BaseModel):
    uuid: UUID
    name: str
    category: Optional[str] = None
    list_tag: Optional[str] = None
    has_additional_info: Optional[bool] = False


class ProjectWithItemsResponse(ProjectResponse):
    items: List[ItemResponse] = []


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    balance: int = None


class UpdateProjectSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class BankCreateSchema(BaseModel):
    name: str
    balance: float


class BankEditSchema(BaseModel):
    name: str
    balance: float


class ProjectServiceResponse(BaseModel):
    data: Any = None
    message: str
    status_code: int

    def to_dict(self):
        return {
            "data": self.data,
            "message": self.message,
            "status_code": self.status_code
        }


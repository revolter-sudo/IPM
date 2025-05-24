from typing import Optional, Any, List
from uuid import UUID

from pydantic import BaseModel


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    balance: float  # For backward compatibility
    po_balance: float = 0.0
    estimated_balance: float = 0.0
    actual_balance: float = 0.0
    po_document_path: Optional[str] = None

    def to_dict(self):
        """
        Convert the Pydantic model instance into a dictionary.
        """
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "balance": self.balance,  # For backward compatibility
            "po_balance": self.po_balance,
            "estimated_balance": self.estimated_balance,
            "actual_balance": self.actual_balance,
            "po_document_path": self.po_document_path,
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
    balance: float = 0.0  # For backward compatibility
    po_balance: float = 0.0
    estimated_balance: float = 0.0
    actual_balance: float = 0.0


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


class InvoiceCreateRequest(BaseModel):
    project_id: UUID
    amount: float
    description: Optional[str] = None


class InvoiceResponse(BaseModel):
    uuid: UUID
    project_id: UUID
    amount: float
    description: Optional[str] = None
    file_path: Optional[str] = None
    status: str
    created_at: str


class InvoiceStatusUpdateRequest(BaseModel):
    status: str = "received"


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

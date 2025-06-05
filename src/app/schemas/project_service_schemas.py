from typing import Optional, Any, List
from uuid import UUID
from datetime import date
from pydantic import BaseModel


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
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
            "start_date": self.start_date,
            "end_date": self.end_date,
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
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    balance: float = 0.0  # For backward compatibility
    po_balance: float = 0.0
    estimated_balance: float = 0.0
    actual_balance: float = 0.0


class UpdateProjectSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    po_balance: Optional[float] = None
    estimated_balance: Optional[float] = None
    actual_balance: Optional[float] = None


class BankCreateSchema(BaseModel):
    name: str
    balance: float


class BankEditSchema(BaseModel):
    name: str
    balance: float


class InvoiceCreateRequest(BaseModel):
    project_id: UUID
    client_name: str
    invoice_item: str
    amount: float
    description: Optional[str] = None
    due_date: str  # Format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"


class InvoiceUpdateRequest(BaseModel):
    client_name: Optional[str] = None
    invoice_item: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    due_date: Optional[str] = None  # Format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"


class InvoiceResponse(BaseModel):
    uuid: UUID
    project_id: UUID
    client_name: str
    invoice_item: str
    amount: float
    description: Optional[str] = None
    due_date: str
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

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


class ProjectPORequest(BaseModel):
    """
    Enhanced PO request with explicit file binding support
    """
    po_number: Optional[str] = None
    amount: float
    description: Optional[str] = None
    file_index: Optional[int] = None  # Index of the file to bind to this PO (0-9)
    
    class Config:
        schema_extra = {
            "example": {
                "po_number": "PO001",
                "amount": 1000.0,
                "description": "Purchase order for construction materials",
                "file_index": 0
            }
        }


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
    # New field for multiple POs with file binding
    pos: Optional[List[ProjectPORequest]] = []
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Construction Project Alpha",
                "description": "Main construction project",
                "location": "Downtown Site",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "po_balance": 2000.0,
                "estimated_balance": 2500.0,
                "actual_balance": 1500.0,
                "pos": [
                    {
                        "po_number": "PO001",
                        "amount": 1000.0,
                        "description": "Materials purchase order",
                        "file_index": 0
                    },
                    {
                        "po_number": "PO002",
                        "amount": 1000.0,
                        "description": "Labor purchase order",
                        "file_index": 1
                    }
                ]
            }
        }


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
    project_po_id: Optional[UUID] = None  # Reference to specific PO
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
    payment_status: Optional[str] = None  # not_paid, partially_paid, fully_paid


class InvoicePaymentCreateRequest(BaseModel):
    # invoice_id: UUID
    amount: float
    payment_date: str  # Format: "YYYY-MM-DD"
    description: Optional[str] = None
    payment_method: Optional[str] = None  # cash, bank, cheque, etc.
    reference_number: Optional[str] = None


class InvoicePaymentResponse(BaseModel):
    uuid: UUID
    invoice_id: UUID
    amount: float
    payment_date: str
    description: Optional[str] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    created_at: str


class InvoiceAnalyticsItem(BaseModel):
    invoice_uuid: UUID
    project_name: str
    po_number: Optional[str] = None
    po_amount: float
    invoice_amount: float
    invoice_due_date: str
    payment_status: str  # not_paid, partially_paid, fully_paid
    total_paid_amount: float
    is_late: Optional[bool] = None  # True/False/None based on payment vs end date


class InvoiceAnalyticsResponse(BaseModel):
    project_id: UUID
    project_name: str
    project_end_date: Optional[str] = None
    invoices: List[InvoiceAnalyticsItem] = []


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


# Enhanced response schemas for better PO binding information
class POBindingInfo(BaseModel):
    """Information about PO file binding"""
    file_index: Optional[int] = None
    original_filename: Optional[str] = None
    file_size_bytes: int = 0
    successfully_bound: bool = False


class EnhancedPOResponse(BaseModel):
    """Enhanced PO response with binding information"""
    uuid: UUID
    po_number: Optional[str] = None
    amount: float
    description: Optional[str] = None
    file_path: Optional[str] = None
    has_document: bool = False
    file_binding: POBindingInfo
    created_at: Optional[str] = None


class EnhancedProjectResponse(BaseModel):
    """Enhanced project response with detailed PO binding information"""
    uuid: UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    po_balance: float = 0.0
    estimated_balance: float = 0.0
    actual_balance: float = 0.0
    po_summary: dict = {}
    pos: List[EnhancedPOResponse] = []
from typing import Optional, Any, List
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field


class ProjectResponse(BaseModel):
    uuid: UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    estimated_balance: float = 0.0
    actual_balance: float = 0.0
    created_at: datetime

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
            "estimated_balance": self.estimated_balance,
            "actual_balance": self.actual_balance,
        }


class ItemResponse(BaseModel):
    uuid: UUID
    name: str
    category: Optional[str] = None
    list_tag: Optional[str] = None
    has_additional_info: Optional[bool] = False
    created_at: str

class ItemUpdate(BaseModel):
    item_id: UUID
    item_balance: float

class ProjectItemUpdateRequest(BaseModel):
    items: List[ItemUpdate]

class ProjectItemUpdateResponse(BaseModel):
    status_code: int
    message : str


class ProjectWithItemsResponse(ProjectResponse):
    items: List[ItemResponse] = []


class ProjectPORequest(BaseModel):
    po_number: Optional[str] = None
    amount: float
    description: Optional[str] = None


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    balance: float = 0.0  # For backward compatibility
    estimated_balance: float = 0.0
    actual_balance: float = 0.0
    # New field for multiple POs
    pos: Optional[List[ProjectPORequest]] = []


class UpdateProjectSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
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


class InvoiceItemUpdate(BaseModel):
    item_name: str
    basic_value: float

class InvoiceUpdateRequest(BaseModel):
    client_name: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None  # "YYYY-MM-DD"
    invoice_items: Optional[List[InvoiceItemUpdate]] = None


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

class MultiInvoicePaymentRequest(BaseModel):
    payments: List[InvoicePaymentCreateRequest]


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
    payment_date: List[dict] = []  # "YYYY-MM-DD" or None if no payments
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

class POItemInput(BaseModel):
    item_name: str
    basic_value: float

class ProjectPOUpdateSchema(BaseModel):
    po_number: Optional[str]
    client_name: Optional[str]
    amount: Optional[float]
    description: Optional[str]
    po_date: Optional[str]  # "YYYY-MM-DD"
    items: List[POItemInput] = []

class CompanyInfoCreate(BaseModel):
    years_of_experience: int = Field(..., ge=0)
    no_of_staff: int = Field(..., ge=0)
    user_construction: str
    successfull_installations: str
    logo_photo_url: Optional[str] = None

class CompanyInfoUpdate(BaseModel):
    years_of_experience: Optional[int] = None
    no_of_staff: Optional[int] = None
    user_construction: Optional[str] = None
    successfull_installations: Optional[str] = None
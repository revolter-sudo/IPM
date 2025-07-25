import uuid

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
    Date
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.app.database.database import Base


class Khatabook(Base):
    __tablename__ = "khatabook_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

    amount = Column(Float, nullable=False)
    remarks = Column(Text, nullable=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey("person.uuid"), nullable=False)  # Ensure person_id is required
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    expense_date = Column(TIMESTAMP, nullable=True)  # New field for user-entered date
    payment_mode = Column(String(50), nullable=True)
    entry_type = Column(String(50), nullable=False, default="Debit")  # New field: "Debit" for manual entries, "Credit" for self payments
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    balance_after_entry = Column(Float, nullable=True)
    is_suspicious = Column(Boolean, nullable=False, server_default='false')  # New field to mark entries as suspicious
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.uuid"),
        nullable=True  # <--- optional field
    )

    # Relationships
    person = relationship("Person", foreign_keys=[person_id])
    created_by_user = relationship("User", foreign_keys=[created_by])
    files = relationship("KhatabookFile", back_populates="khatabook_entry", cascade="all, delete-orphan")
    items = relationship("KhatabookItem", back_populates="khatabook_entry", cascade="all, delete-orphan")
    project = relationship("Project", foreign_keys=[project_id], lazy="joined")

    def __repr__(self):
        return f"<Khatabook(id={self.id}, uuid={self.uuid}, amount={self.amount}, expense_date={self.expense_date})>"


class KhatabookFile(Base):
    __tablename__ = "khatabook_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    khatabook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("khatabook_entries.uuid", ondelete="CASCADE"),
        nullable=False
    )
    file_path = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    khatabook_entry = relationship("Khatabook", back_populates="files")
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<KhatabookFile(id={self.id}, file_path={self.file_path})>"


class KhatabookItem(Base):
    __tablename__ = "khatabook_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    khatabook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("khatabook_entries.uuid", ondelete="CASCADE"),
        nullable=False
    )
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.uuid", ondelete="CASCADE"),
        nullable=False
    )

    khatabook_entry = relationship("Khatabook", back_populates="items")
    item = relationship("Item", back_populates="khatabook_items")
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<KhatabookItem(khatabook_id={self.khatabook_id}, item_id={self.item_id})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    phone = Column(BigInteger, unique=False, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    photo_path = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    token_maps = relationship(
        "UserTokenMap",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Relationship to Person
    person = relationship(
        "Person",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    project_user_map = relationship(
        "ProjectUserMap",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    user_items = relationship(
        "UserItemMap",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    project_user_item_map = relationship(
        "ProjectUserItemMap",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Attendance relationships
    self_attendances = relationship(
        "SelfAttendance",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    project_attendances = relationship(
        "ProjectAttendance",
        back_populates="site_engineer",
        cascade="all, delete-orphan"
    )

    configured_wages = relationship(
        "ProjectDailyWage",
        back_populates="configured_by",
        cascade="all, delete-orphan"
    )

    machinery = relationship(
        "Machinery",
        back_populates="created_by_user",
        cascade="all, delete-orphan"
    )


class UserTokenMap(Base):
    __tablename__ = "user_token_map"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fcm_token = Column(String(500), nullable=False)
    device_id = Column(String(255), nullable=True)
    created_at = Column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # Relationship back to User
    user = relationship(
        "User",
        back_populates="token_maps",
    )


class Person(Base):
    __tablename__ = "person"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    name = Column(String(50), nullable=False)
    account_number = Column(String(17), nullable=False)
    ifsc_code = Column(String(11), nullable=False)
    phone_number = Column(String(10), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    upi_number = Column(String(50), nullable=True)
    role = Column(String(30), nullable=True)  # Optional role field using same enum values as User.role
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.uuid"),
        unique=True,
        nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="person")
    parent_id = Column(UUID(as_uuid=True), ForeignKey("person.uuid"), nullable=True)
    parent = relationship("Person", remote_side=[uuid], back_populates="children")
    children = relationship("Person", back_populates="parent", cascade="all, delete-orphan")

    # Attendance relationship
    project_attendances = relationship(
        "ProjectAttendance",
        back_populates="sub_contractor",
        cascade="all, delete-orphan"
    )

    machinery = relationship(
        "Machinery",
        back_populates="sub_contractor",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Person(id={self.id}, name={self.name}, user_id={self.user_id})>"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    # Keeping old fields for backward compatibility, but they'll be deprecated
    # po_balance = Column(Float, nullable=False, default=0.0)
    estimated_balance = Column(Float, nullable=False, default=0.0)
    actual_balance = Column(Float, nullable=False, default=0.0)
    # po_document_path = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    project_user_map = relationship(
        "ProjectUserMap",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    projecct_items = relationship(
        "ProjectItemMap",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    project_invoices = relationship(
        "Invoice",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    project_user_item_map = relationship(
        "ProjectUserItemMap",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    # New relationship for multiple POs
    project_pos = relationship(
        "ProjectPO",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    # Attendance relationships
    project_attendances = relationship(
        "ProjectAttendance",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    daily_wages = relationship(
        "ProjectDailyWage",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    machinery = relationship(
        "Machinery",
        back_populates="project",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(id={self.id}, uuid={self.uuid}, name={self.name})>"


class ProjectPO(Base):
    __tablename__ = "project_pos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False
    )
    po_number = Column(String(100), unique=True, nullable=True)  # Optional PO number
    client_name = Column(String(255), nullable=True)
    po_date = Column(String(50), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=True)  # Path to PO document
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="project_pos")
    invoices = relationship(
        "Invoice",
        back_populates="project_po",
        cascade="all, delete-orphan"
    )
    po_items = relationship("ProjectPOItem", back_populates="project_po", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<ProjectPO(id={self.id}, project_id={self.project_id}, amount={self.amount})>"
    
class ProjectPOItem(Base):
    __tablename__ = "project_po_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    project_po_id = Column(UUID(as_uuid=True), ForeignKey("project_pos.uuid", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(255), nullable=False)
    basic_value = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    project_po = relationship("ProjectPO", back_populates="po_items")



class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    entity = Column(String(255), nullable=False)
    action = Column(String(20), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    performed_by = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    timestamp = Column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            f"<Log(id={self.id}, uuid={self.uuid}, "
            f"entity={self.entity}, action={self.action})>"
        )


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    status = Column(String(20), nullable=False)
    remarks = Column(Text, nullable=True)

    # This is the FK pointing to Person
    person = Column(UUID(as_uuid=True), ForeignKey("person.uuid"), nullable=True)

    # Flag if this payment is "self-payment"
    self_payment = Column(Boolean, nullable=False, default=False)
    decline_remark = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_deleted = Column(Boolean, default=False, nullable=False)
    update_remarks = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    transferred_date = Column(TIMESTAMP, nullable=True)
    priority_id = Column(
        UUID(as_uuid=True),
        ForeignKey("priorities.uuid"),
        nullable=True  # or nullable=False if you want to make it mandatory
    )
    deducted_from_bank_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("balance_details.uuid"),
        nullable=True
    )

    deducted_from_bank = relationship(
        "BalanceDetail",
        foreign_keys=[deducted_from_bank_uuid],
        lazy="joined"
    )
    priority_rel = relationship("Priority", foreign_keys=[priority_id], lazy="joined")

    # NEW RELATIONSHIP: link to Person table for the 'person' FK
    person_rel = relationship("Person", foreign_keys=[person], lazy="joined")

    # Other relationships
    payment_files = relationship(
        "PaymentFile", back_populates="payment", cascade="all, delete-orphan"
    )
    payment_items = relationship(
        "PaymentItem", back_populates="payment", cascade="all, delete-orphan"
    )
    status_entries = relationship(
        "PaymentStatusHistory",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentStatusHistory.created_at"
    )
    edit_histories = relationship(
        "PaymentEditHistory",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentEditHistory.updated_at"
    )

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, self_payment={self.self_payment}, status={self.status})>"


class PaymentEditHistory(Base):
    __tablename__ = "payment_edit_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.uuid", ondelete="CASCADE"), nullable=False)
    old_amount = Column(Float, nullable=False)
    new_amount = Column(Float, nullable=False)
    remarks = Column(Text, nullable=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    # Relationship back to Payment
    payment = relationship("Payment", back_populates="edit_histories")

    def __repr__(self):
        return f"<PaymentEditHistory(old={self.old_amount}, new={self.new_amount}, remarks={self.remarks})>"


class PaymentStatusHistory(Base):
    __tablename__ = "payment_status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.uuid", ondelete="CASCADE"),
        nullable=False
    )
    status = Column(String(20), nullable=False)      # e.g. "requested", "verified", "approved", "done"x``
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationship back to Payment so we can do payment_status_history.payment to navigate
    payment = relationship("Payment", back_populates="status_entries")

    def __repr__(self):
        return (
            f"<PaymentStatusHistory(id={self.id}, "
            f"payment_id={self.payment_id}, status={self.status})>"
        )


class PaymentFile(Base):
    __tablename__ = "payment_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.uuid", ondelete="CASCADE"),
        nullable=False
    )
    file_path = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # NEW: A column to indicate files that came from the /approve endpoint
    is_approval_upload = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    payment = relationship("Payment", back_populates="payment_files")

    def __repr__(self):
        return f"<PaymentFile(id={self.id}, payment_id={self.payment_id}, file_path={self.file_path}, is_approval_upload={self.is_approval_upload})>"


class ProjectBalance(Base):
    __tablename__ = "project_balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False
    )
    adjustment = Column(
        Float, nullable=False
    )  # Positive for additions, negative for deductions
    balance_type = Column(
        String(20), nullable=False, default="actual"
    )  # po, estimated, actual
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ProjectBalance(project_id={self.project_id}, adjustment={self.adjustment}, type={self.balance_type})>"


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True)
    list_tag = Column(String(30), nullable=True)
    has_additional_info = Column(Boolean, nullable=False, default=False)

    # Relationship for payments associated with this item
    payments = relationship("PaymentItem", back_populates="item", cascade="all, delete-orphan")
    khatabook_items = relationship("KhatabookItem", back_populates="item", cascade="all, delete-orphan")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    machinery = relationship("Machinery", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(id={self.id}, name={self.name}, category={self.category})>"

    project_items = relationship(
        "ProjectItemMap",
        back_populates="item",
        cascade="all, delete-orphan"
    )

    project_attendances = relationship(
        "ProjectAttendance",
        back_populates="item",
        cascade="all, delete-orphan"
    )

    user_items = relationship(
        "UserItemMap",
        back_populates="item",
        cascade="all, delete-orphan"
    )

    project_user_item_map = relationship(
        "ProjectUserItemMap",
        back_populates="item",
        cascade="all, delete-orphan"
    )



class PaymentItem(Base):
    __tablename__ = "payment_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.uuid", ondelete="CASCADE"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid", ondelete="CASCADE"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    payment = relationship("Payment", back_populates="payment_items")
    item = relationship("Item", back_populates="payments")

    def __repr__(self):
        return f"<PaymentItem(payment_id={self.payment_id}, item_id={self.item_id})>"


class KhatabookBalance(Base):
    __tablename__ = "khatabook_balance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_uuid = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False, unique=True)
    balance = Column(Float, nullable=False, default=0.0)

    user = relationship("User", foreign_keys=[user_uuid])

    def __repr__(self):
        return f"<KhatabookBalance(id={self.id}, user_uuid={self.user_uuid}, balance={self.balance})>"


class BalanceDetail(Base):
    __tablename__ = "balance_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4
    )
    name = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False)


class Priority(Base):
    __tablename__ = "priorities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    priority = Column(String(50), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Priority(id={self.id}, uuid={self.uuid}, priority={self.priority})>"

from sqlalchemy import UniqueConstraint

class ProjectUserMap(Base):
    __tablename__ = "project_user_map"
    __table_args__ = (
        UniqueConstraint('user_id', 'project_id', name='uq_user_project'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    project = relationship("Project", back_populates="project_user_map")
    user = relationship("User", back_populates="project_user_map")

    def __repr__(self):
        return f"<ProjectUserMap(project_id={self.project_id}, user_id={self.user_id})>"


class ProjectItemMap(Base):
    __tablename__ = "project_item_map"
    __table_args__ = (
        UniqueConstraint('project_id', 'item_id', name='uq_project_item'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    item_balance = Column(Float, nullable=True)  # Changed to nullable=True
    is_deleted = Column(Boolean, nullable=False, default=False)

    project = relationship("Project")
    item = relationship("Item")

    def __repr__(self):
        return f"<ProjectItemMap(project_id={self.project_id}, item_id={self.item_id})>"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False
    )
    # New field: Reference to specific PO
    project_po_id = Column(
        UUID(as_uuid=True), ForeignKey("project_pos.uuid"), nullable=True
    )
    client_name = Column(String(255), nullable=False)
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(String(50), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(TIMESTAMP, nullable=False)
    file_path = Column(String(255), nullable=True)
    # Updated status field to handle new payment statuses
    status = Column(String(20), nullable=False, default="uploaded")
    # New fields for payment tracking
    payment_status = Column(
        String(20), nullable=False, default="not_paid"
    )  # not_paid, partially_paid, fully_paid
    total_paid_amount = Column(Float, nullable=False, default=0.0)
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="project_invoices")
    project_po = relationship("ProjectPO", back_populates="invoices")
    invoice_payments = relationship(
        "InvoicePayment",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    invoice_items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Invoice(id={self.id}, amount={self.amount}, status={self.status})>"
class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.uuid", ondelete="CASCADE"), nullable=False)
    item_name = Column(String(255), nullable=False)
    basic_value = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    invoice = relationship("Invoice", back_populates="invoice_items")

    def __repr__(self):
        return f"<InvoiceItem(invoice_id={self.invoice_id}, item_name={self.item_name}, basic_value={self.basic_value})>"


class InvoicePayment(Base):
    __tablename__ = "invoice_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    invoice_id = Column(
        UUID(as_uuid=True), ForeignKey("invoices.uuid"), nullable=False
    )
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    payment_method = Column(String(50), nullable=True)  # cash, bank, cheque
    reference_number = Column(String(100), nullable=True)  # cheque/txn ref
    bank_uuid = Column(
        UUID(as_uuid=True), ForeignKey("balance_details.uuid"), nullable=True
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_late = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    invoice = relationship("Invoice", back_populates="invoice_payments")
    bank = relationship("BalanceDetail", foreign_keys=[bank_uuid], lazy="joined")

    def __repr__(self):
        return f"<InvoicePayment(id={self.id}, invoice_id={self.invoice_id}, amount={self.amount})>"


class UserItemMap(Base):
    __tablename__ = "user_item_map"
    __table_args__ = (
        UniqueConstraint('user_id', 'item_id', name='uq_user_item'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    item_balance = Column(Float, nullable=True)  # Changed to nullable=True

    user = relationship("User", back_populates="user_items")
    item = relationship("Item", back_populates="user_items")

    def __repr__(self):
        return f"<UserItemMap(user_id={self.user_id}, item_id={self.item_id})>"


class DefaultConfig(Base):
    __tablename__ = "default_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    admin_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    # Relationship to Item
    item = relationship("Item")

    def __repr__(self):
        return f"<DefaultConfig(uuid={self.uuid}, item_id={self.item_id}, admin_amount={self.admin_amount})>"


class ProjectUserItemMap(Base):
    __tablename__ = "project_user_item_map"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    project = relationship("Project")
    user = relationship("User")
    item = relationship("Item")


class UserData(Base):
    __tablename__ = "user_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    email = Column(String(50), nullable=False)
    phone_number = Column(String(20), nullable=False)
    password = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

class Salary(Base):
    __tablename__ = "salary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    month = Column(String(20), nullable=False)  # e.g. "January 2024"
    amount = Column(Float, nullable=False, default=0.0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


class ItemGroups(Base):
    __tablename__ = "item_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    item_groups = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

class ItemGroupMap(Base):
    __tablename__ = "item_group_map"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    item_group_id = Column(UUID(as_uuid=True), ForeignKey("item_groups.uuid"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    item_balance = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    item = relationship("Item")
    item_group = relationship("ItemGroups")

class CompanyInfo(Base):
    __tablename__ = "company_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    years_of_experience = Column(Integer, nullable=False, default=0)
    no_of_staff = Column(Integer, nullable=False, default=0)
    user_construction = Column(String(255), nullable=False, default=False)
    successfull_installations = Column(String(255), nullable=False, default=0)
    logo_photo_url = Column(Text, nullable=True)


class ItemCategories(Base):
    __tablename__ = "item_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    category = Column(String(20), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)

    # user = relationship("User")
    # item = relationship("Item")


class InquiryData(Base):
    __tablename__ = "inquiry_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    # Inquiry details
    name = Column(String(100), nullable=False)
    phone_number = Column(String(15), nullable=False)
    project_type = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)

    # Timestamps and soft delete
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<InquiryData(name={self.name}, phone_number={self.phone_number}, project_type={self.project_type})>"


class SelfAttendance(Base):
    __tablename__ = "self_attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    attendance_date = Column(Date, nullable=True)

    # Punch In Details
    punch_in_time = Column(TIMESTAMP, nullable=True, server_default=func.now())
    punch_in_latitude = Column(Float, nullable=True)
    punch_in_longitude = Column(Float, nullable=True)
    punch_in_location_address = Column(Text, nullable=True)

    # Punch Out Details (can be NULL if user forgets to punch out)
    punch_out_time = Column(TIMESTAMP, nullable=True)
    punch_out_latitude = Column(Float, nullable=True)
    punch_out_longitude = Column(Float, nullable=True)
    punch_out_location_address = Column(Text, nullable=True)

    # Array of project UUIDs user was assigned to at time of punch in
    assigned_projects = Column(Text, nullable=True)  # JSON string
    status = Column(String(20), nullable=False)  # present, absent, off day, etc.
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="self_attendances")

    def __repr__(self):
        return f"<SelfAttendance(user_id={self.user_id}, attendance_date={self.attendance_date}, punch_in_time={self.punch_in_time})>"


class ProjectAttendance(Base):
    __tablename__ = "project_attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    site_engineer_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    sub_contractor_id = Column(UUID(as_uuid=True), ForeignKey("person.uuid"), nullable=False)
    no_of_labours = Column(Integer, nullable=False)
    attendance_date = Column(Date, nullable=False)
    marked_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    photo_path = Column(String(255), nullable=True)

    # Relationships
    site_engineer = relationship("User", back_populates="project_attendances")
    project = relationship("Project", back_populates="project_attendances")
    item = relationship("Item", back_populates="project_attendances")
    sub_contractor = relationship("Person", back_populates="project_attendances")
    wage_calculation = relationship("ProjectAttendanceWage", back_populates="project_attendance", uselist=False)

    def __repr__(self):
        return f"<ProjectAttendance(project_id={self.project_id}, site_engineer_id={self.site_engineer_id}, attendance_date={self.attendance_date})>"


class ProjectDailyWage(Base):
    __tablename__ = "project_daily_wage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    daily_wage_rate = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=False)
    configured_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="daily_wages")
    configured_by = relationship("User", back_populates="configured_wages")
    wage_calculations = relationship("ProjectAttendanceWage", back_populates="project_daily_wage")

    def __repr__(self):
        return f"<ProjectDailyWage(project_id={self.project_id}, daily_wage_rate={self.daily_wage_rate}, effective_date={self.effective_date})>"


class ProjectAttendanceWage(Base):
    __tablename__ = "project_attendance_wage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    project_attendance_id = Column(UUID(as_uuid=True), ForeignKey("project_attendance.uuid"), nullable=False)
    project_daily_wage_id = Column(UUID(as_uuid=True), ForeignKey("project_daily_wage.uuid"), nullable=False)
    no_of_labours = Column(Integer, nullable=False)
    daily_wage_rate = Column(Float, nullable=False)
    total_wage_amount = Column(Float, nullable=False)  # no_of_labours * daily_wage_rate
    calculated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationships
    project_attendance = relationship("ProjectAttendance", back_populates="wage_calculation")
    project_daily_wage = relationship("ProjectDailyWage", back_populates="wage_calculations")

    def __repr__(self):
        return f"<ProjectAttendanceWage(project_attendance_id={self.project_attendance_id}, total_wage_amount={self.total_wage_amount})>"


class Machinery(Base):
    __tablename__ = "machinery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    sub_contractor_id = Column(UUID(as_uuid=True), ForeignKey("person.uuid"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=True)  # Nullable if not yet ended
    notes = Column(Text, nullable=True)
    photo_path = Column(String(255), nullable=True)  # Path to machinery photo
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="machinery")
    sub_contractor = relationship("Person", back_populates="machinery")
    item = relationship("Item", back_populates="machinery")
    created_by_user = relationship("User", foreign_keys=[created_by], back_populates="machinery")
    photos = relationship("MachineryPhotos", back_populates="machinery", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Machinery(id={self.id}, project_id={self.project_id}, item_id={self.item_id}, start_time={self.start_time})>"
    
class MachineryPhotos(Base):
    __tablename__ = "machinery_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    machinery_id = Column(UUID(as_uuid=True), ForeignKey("machinery.uuid"), nullable=False)
    photo_path = Column(String(255), nullable=False)  # Path to the photo
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship back to Machinery
    machinery = relationship("Machinery", back_populates="photos")

    def __repr__(self):
        return f"<MachineryPhotos(id={self.id}, machinery_id={self.machinery_id}, photo_path={self.photo_path})>"
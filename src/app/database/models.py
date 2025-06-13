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

    def __repr__(self):
        return f"<KhatabookItem(khatabook_id={self.khatabook_id}, item_id={self.item_id})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    phone = Column(BigInteger, unique=False, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    photo_path = Column(String(255), nullable=True)

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
    name = Column(String(25), nullable=False)
    account_number = Column(String(17), nullable=False)
    ifsc_code = Column(String(11), nullable=False)
    phone_number = Column(String(10), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    upi_number = Column(String(50), nullable=True)
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
    po_number = Column(String(100), nullable=True)  # Optional PO number
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

    def __repr__(self):
        return f"<ProjectPO(id={self.id}, project_id={self.project_id}, amount={self.amount})>"


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

    def __repr__(self):
        return f"<Item(id={self.id}, name={self.name}, category={self.category})>"

    project_items = relationship(
        "ProjectItemMap",
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

    def __repr__(self):
        return f"<Item(name={self.name})>"


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

    project = relationship("Project", back_populates="project_user_map")
    user = relationship("User", back_populates="project_user_map")

    def __repr__(self):
        return f"<ProjectUserMap(project_id={self.project_id}, user_id={self.user_id})>"


class ProjectItemMap(Base):
    __tablename__ = "project_item_map"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid"), nullable=False)
    item_balance = Column(Float, nullable=True)  # Changed to nullable=True

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
    invoice_item = Column(String(255), nullable=False)
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

    def __repr__(self):
        return f"<Invoice(id={self.id}, amount={self.amount}, status={self.status})>"


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

    project = relationship("Project")
    user = relationship("User")
    item = relationship("Item")

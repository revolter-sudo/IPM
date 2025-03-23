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

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    balance_after_entry = Column(Float, nullable=True)
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
    phone = Column(BigInteger, unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    photo_path = Column(String(255), nullable=True)

    # Relationship to Person
    person = relationship(
        "Person",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
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
    upi_number = Column(String(50), nullable=True)      # New field
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
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Project(id={self.id}, uuid={self.uuid}, name={self.name})>"


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

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_deleted = Column(Boolean, default=False, nullable=False)
    update_remarks = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    transferred_date = Column(TIMESTAMP, nullable=True)

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

    # Relationship back to Payment so we can do payment_status_history.payment to navigate
    payment = relationship("Payment", back_populates="status_entries")

    def __repr__(self):
        return (
            f"<PaymentStatusHistory(id={self.id}, "
            f"payment_id={self.payment_id}, status={self.status})>"
        )


# class PaymentFile(Base):
#     __tablename__ = "payment_files"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.uuid", ondelete="CASCADE"), nullable=False)
#     file_path = Column(String(255), nullable=False)
#     created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

#     # ✅ Correct Relationship
#     payment = relationship("Payment", back_populates="payment_files")

#     def __repr__(self):
#         return f"<PaymentFile(id={self.id}, payment_id={self.payment_id}, file_path={self.file_path})>"

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
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ProjectBalance(project_id={self.project_id}, adjustment={self.adjustment})>"


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True)
    list_tag = Column(String(30), nullable=True)

    # Relationship for payments associated with this item
    payments = relationship("PaymentItem", back_populates="item", cascade="all, delete-orphan")
    khatabook_items = relationship("KhatabookItem", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(id={self.id}, name={self.name}, category={self.category})>"


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.uuid", ondelete="CASCADE"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("items.uuid", ondelete="CASCADE"), nullable=False)

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
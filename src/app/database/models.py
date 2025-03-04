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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    name = Column(String(255), nullable=False)
    phone = Column(BigInteger, unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)


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
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4
    )
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=False
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False
    )
    status = Column(String(20), nullable=False)
    remarks = Column(Text, nullable=True)
    person = Column(
        UUID(as_uuid=True), ForeignKey("person.uuid"), nullable=True
    )
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    is_deleted = Column(Boolean, default=False, nullable=False)
    update_remarks = Column(Text, nullable=True)

    # Relationships
    payment_files = relationship("PaymentFile", back_populates="payment", cascade="all, delete-orphan")
    payment_items = relationship("PaymentItem", back_populates="payment", cascade="all, delete-orphan")
    status_entries = relationship(
        "PaymentStatusHistory",       # reference the model above
        back_populates="payment",     # matches PaymentStatusHistory.payment
        cascade="all, delete-orphan",
        order_by="PaymentStatusHistory.created_at"  # so entries come in chronological order
    )

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status={self.status})>"


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


class PaymentFile(Base):
    __tablename__ = "payment_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.uuid", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # ✅ Correct Relationship
    payment = relationship("Payment", back_populates="payment_files")

    def __repr__(self):
        return f"<PaymentFile(id={self.id}, payment_id={self.payment_id}, file_path={self.file_path})>"


class Person(Base):
    __tablename__ = "person"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    name = Column(String(25), nullable=False)
    account_number = Column(String(17), nullable=False)
    ifsc_code = Column(String(11), nullable=False)
    phone_number = Column(String(10), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("person.uuid"), nullable=True)

    # Relationship definitions
    parent = relationship("Person", remote_side=[uuid], back_populates="children")  # Parent account
    children = relationship("Person", back_populates="parent", cascade="all, delete-orphan")  # Secondary accounts

    def __repr__(self):
        return f"<Person(id={self.id}, name={self.name}, parent_id={self.parent_id})>"


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

    # Relationship for payments associated with this item
    payments = relationship("PaymentItem", back_populates="item", cascade="all, delete-orphan")

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

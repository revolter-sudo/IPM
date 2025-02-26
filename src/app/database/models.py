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

    # Relationships
    payment_files = relationship("PaymentFile", back_populates="payment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount}, status={self.status})>"


class PaymentFile(Base):
    __tablename__ = "payment_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.uuid"),
        nullable=False
    )
    file_path = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    # Relationship
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

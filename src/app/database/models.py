import uuid

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

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

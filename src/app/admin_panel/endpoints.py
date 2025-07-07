import os
import json
from collections import defaultdict
from fastapi import FastAPI, Body, Response
from fastapi_sqlalchemy import DBSessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from src.app.database.database import settings
from src.app.services.auth_service import get_current_user,get_password_hash
from src.app.schemas.auth_service_schamas import UserRole
from src.app.admin_panel.services import (
    create_project_user_mapping,
    create_project_item_mapping,
    create_user_item_mapping,
    create_multiple_user_item_mappings,
    remove_project_item_mapping,
    remove_project_user_mapping,
    remove_user_item_mapping,
    create_default_config_service,
    update_default_config_service,
    sync_project_user_mappings,
    sync_project_item_mappings,
    sync_project_user_item_mappings
)
from src.app.admin_panel.schemas import (
    UserProjectItemResponse,
    PersonToUserCreate
    )
from src.app.schemas.project_service_schemas import (
    ProjectServiceResponse,
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
    InvoiceStatusUpdateRequest,
    InvoicePaymentCreateRequest,
    InvoicePaymentResponse,
    InvoiceAnalyticsResponse,
    InvoiceAnalyticsItem,
    MultiInvoicePaymentRequest,
    ProjectItemUpdateRequest,
    ItemUpdate,
    ProjectItemUpdateResponse
)
from src.app.schemas.payment_service_schemas import PaymentStatus, PaymentServiceResponse
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import and_, func
from fastapi import (
    Depends,
    File,
    Query,
    UploadFile,
    Form,
    Body
)
from src.app.database.models import (
    Log,
    Project,
    User,
    Payment,
    ProjectUserMap,
    Item,
    ProjectItemMap,
    Invoice,
    UserItemMap,
    Khatabook,
    KhatabookItem,
    KhatabookFile,
    Person,
    DefaultConfig,
    PaymentItem,
    ProjectUserItemMap,
    ProjectItemMap,
    UserItemMap,
    ProjectUserMap,
    ProjectPO,
    InvoicePayment,
    InvoiceItem,
    ItemGroups,
    ItemGroupMap,
    Salary,
    InquiryData
)
from sqlalchemy.orm import Session, joinedload
from src.app.schemas import constants
from src.app.admin_panel.services import get_default_config_service
from src.app.database.database import get_db
from src.app.utils.logging_config import get_logger, get_api_logger
from src.app.admin_panel.schemas import (
    AdminPanelResponse,
    DefaultConfigCreate,
    DefaultConfigUpdate,
    ProjectUserItemMapCreate,
    SalaryCreateRequest,
    SalaryUpdateRequest,
    SalaryResponse,
)
from fastapi import HTTPException
from sqlalchemy import select
import uuid


# Initialize loggers
logger = get_logger(__name__)
api_logger = get_api_logger()

admin_app = FastAPI(
    title="Admin API",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

admin_app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)

admin_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://ipm-development.netlify.app",
        "https://inqilab.vercel.app/",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_origin_regex="https://.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


@admin_app.get(
    "/default-config",
    tags=['Default Config'],
    status_code=200,
    description="Get the current default configuration (admin amount and site expense item)"
)
def get_default_config():
    try:
        default_config = get_default_config_service()
        return AdminPanelResponse(
            data=default_config,
            message="Default Config Fetched Successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        logger.error(f"Error in get_default_config API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message="Error in get_default_config API",
            status_code=500
        ).model_dump()


@admin_app.post(
    "/default-config",
    tags=['Default Config'],
    status_code=201,
    description="Create a new default configuration with specified item and admin amount"
)
def create_default_config(
    config_data: DefaultConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:

        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value
        ]:
            return AdminPanelResponse(
                data=None,
                message="Only admin and super admin can create default config",
                status_code=403
            ).model_dump()

        # Check if item exists
        item = db.query(Item).filter(Item.uuid == config_data.item_id).first()
        if not item:
            return AdminPanelResponse(
                data=None,
                message="Item not found",
                status_code=404
            ).model_dump()

        existing_config = db.query(
            DefaultConfig
        ).filter(
            DefaultConfig.is_deleted.is_(False)
        ).first()
        if existing_config:
            return AdminPanelResponse(
                data=None,
                message="Default config already exists. Please update instead.",
                status_code=400
            ).model_dump()

        # Create new default config
        new_config = create_default_config_service(
            item_id=config_data.item_id,
            admin_amount=config_data.admin_amount
        )

        return AdminPanelResponse(
            data={
                "uuid": str(new_config.uuid),
                "item_id": str(new_config.item_id),
                "admin_amount": new_config.admin_amount,
                "created_at": new_config.created_at.isoformat()
            },
            message="Default Config Created Successfully",
            status_code=201
        ).model_dump()
    except Exception as e:
        logger.error(f"Error in create_default_config API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message=f"Error in create_default_config API: {str(e)}",
            status_code=500
        ).model_dump()


@admin_app.put(
    "/default-config",
    tags=['Default Config'],
    status_code=200,
    description="Update the default configuration with new item and admin amount"
)
def update_default_config(
    config_data: DefaultConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Check if user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value
        ]:
            return AdminPanelResponse(
                data=None,
                message="Only admin and super admin can update default config",
                status_code=403
            ).model_dump()

        # Check if item exists
        item = db.query(Item).filter(Item.uuid == config_data.item_id).first()
        if not item:
            return AdminPanelResponse(
                data=None,
                message="Item not found",
                status_code=404
            ).model_dump()

        # Update default config
        updated_config = update_default_config_service(
            item_id=config_data.item_id,
            admin_amount=config_data.admin_amount
        )

        return AdminPanelResponse(
            data={
                "uuid": str(updated_config.uuid),
                "item_id": str(updated_config.item_id),
                "admin_amount": updated_config.admin_amount,
                "created_at": updated_config.created_at.isoformat()
            },
            message="Default Config Updated Successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logger.error(f"Error in update_default_config API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message=f"Error in update_default_config API: {str(e)}",
            status_code=500
        ).model_dump()


@admin_app.post(
    "/project_mapping/{user_id}/{project_id}",
    tags=["admin_panel"],
    description="Map a single user to a project (legacy endpoint)",
    deprecated=True,
)
def map_user_to_project(
    user_id: UUID,
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to assign project to user"
            ).model_dump()

        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        try:
            create_project_user_mapping(db=db, user_id=user_id, project_id=project_id)
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error in create_project_user_mapping: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping user to project: {str(db_error)}"
            ).model_dump()

        return ProjectServiceResponse(
            data=None,
            message="Project assigned to user successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in map_user_to_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while mapping user to project"
        ).model_dump()


@admin_app.post(
    "/project_users_mapping/{project_id}",
    tags=["admin_panel"],
    description="Map multiple users to a project at once (handles both assignment and unassignment)"
)
def map_multiple_users_to_project(
    project_id: UUID,
    user_ids: List[UUID] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Map multiple users to a project at once.

    This API handles both assignment and unassignment:
    - Users in the list that are not already mapped to the project will be assigned
    - Users currently mapped to the project but not in the list will be unassigned

    Request body should be in the format:
    ```json
    {
        "user_ids": ["uuid1", "uuid2", "uuid3"]
    }
    ```
    """
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to assign users to project"
            ).model_dump()

        # Verify project exists
        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Verify all users exist
        user_count = db.query(User).filter(User.uuid.in_(user_ids)).count()
        if user_count != len(user_ids):
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="One or more users not found"
            ).model_dump()

        try:
            result = sync_project_user_mappings(
                db=db,
                project_id=project_id,
                user_ids=user_ids
            )

            return ProjectServiceResponse(
                data={
                    "project_id": str(project_id),
                    "added_count": result["added"],
                    "removed_count": result["removed"],
                    "total_mapped": len(result["mappings"]) + result["removed"]
                },
                message="Users synchronized with project successfully",
                status_code=200
            ).model_dump()
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error in map_multiple_users_to_project: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping users to project: {str(db_error)}"
            ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in map_multiple_users_to_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while mapping users to project"
        ).model_dump()

@admin_app.post(
    "/item_mapping/{item_id}/{project_id}",
    tags=["admin_panel"],
    description="Map a single item to a project (legacy endpoint)",
    deprecated=True,
)
def map_item_to_project(
    item_id: UUID,
    project_id: UUID,
    item_balance: float = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to assign project to user"
            ).model_dump()

        # Check if item exists
        item = db.query(Item).filter(Item.uuid == item_id).first()
        if not item:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Item not found"
            ).model_dump()

        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        try:
            create_project_item_mapping(
                db=db,
                item_id=item_id,
                project_id=project_id,
                item_balance=item_balance
            )
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error in create_project_item_mapping: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping item to project: {str(db_error)}"
            ).model_dump()

        return ProjectServiceResponse(
            data=None,
            message="Item mapped to project successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in map_item_to_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while mapping item to project"
        ).model_dump()


@admin_app.post(
    "/project_items_mapping/{project_id}",
    tags=["admin_panel"],
    description="""
    Map multiple items to a project at once (handles both assignment and unassignment)
    {
        "items_data": [
            {"item_id": "uuid1", "balance": 100.0},
            {"item_id": "uuid2", "balance": 200.0}
        ]
    }
    """
)
def map_multiple_items_to_project(
    project_id: UUID,
    items_data: List[dict] = Body(..., embed=True, description="List of items with their balances"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Map multiple items to a project at once.

    This API handles both assignment and unassignment:
    - Items in the list that are not already mapped to the project will be assigned
    - Items currently mapped to the project but not in the list will be unassigned

    Request body should be in the format:
    ```json
    {
        "items_data": [
            {"item_id": "uuid1", "balance": 100.0},
            {"item_id": "uuid2", "balance": 200.0}
        ]
    }
    ```
    """
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to assign items to project"
            ).model_dump()

        # Verify project exists
        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Extract item IDs for validation
        item_ids = []
        for item_data in items_data:
            try:
                item_id = UUID(item_data.get("item_id"))
                item_ids.append(item_id)
            except (ValueError, TypeError) as e:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"Invalid item data format: {str(e)}"
                ).model_dump()

        # Verify all items exist
        item_count = db.query(Item).filter(Item.uuid.in_(item_ids)).count()
        if item_count != len(item_ids):
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="One or more items not found"
            ).model_dump()

        try:
            # Use the sync function to handle both assignment and unassignment
            result = sync_project_item_mappings(
                db=db,
                item_data_list=items_data,
                project_id=project_id
            )

            return ProjectServiceResponse(
                data={
                    "project_id": str(project_id),
                    "added_count": result["added"],
                    "updated_count": result["updated"],
                    "removed_count": result["removed"],
                    "total_mapped": len(result["mappings"])
                },
                message="Items synchronized with project successfully",
                status_code=200
            ).model_dump()
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error in map_multiple_items_to_project: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping items to project: {str(db_error)}"
            ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in map_multiple_items_to_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while mapping items to project"
        ).model_dump()


@admin_app.post(
    "/user_item_mapping/{user_id}/{item_id}",
    tags=["admin_panel"],
    description="Map a single item to a user (legacy endpoint)",
    deprecated=True,
)
def map_item_to_user(
    user_id: UUID,
    item_id: UUID,
    item_balance: Optional[float] = None,  # Changed to Optional with None default
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to assign items to user"
            ).model_dump()

        # Check if user exists
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Check if item exists
        item = db.query(Item).filter(Item.uuid == item_id).first()
        if not item:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Item not found"
            ).model_dump()

        try:
            create_user_item_mapping(
                db=db,
                user_id=user_id,
                item_id=item_id,
                item_balance=item_balance
            )
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error in create_user_item_mapping: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping item to user: {str(db_error)}"
            ).model_dump()

        return ProjectServiceResponse(
            data=None,
            message="Item assigned to user successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in map_item_to_user API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while mapping item to user"
        ).model_dump()


@admin_app.post(
    "/user_items_mapping/{user_id}",
    tags=["admin_panel"],
    description="Map multiple items to a user at once"
)
def map_multiple_items_to_user(
    user_id: UUID,
    items_data: List[dict] = Body(..., embed=True, description="List of items with their balances"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Map multiple items to a user at once.

    Request body should be in the format:
    ```json
    {
        "items_data": [
            {"item_id": "uuid1", "balance": 100.0},
            {"item_id": "uuid2", "balance": 200.0}
        ]
    }
    ```
    """
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to assign items to user"
            ).model_dump()

        # Verify user exists
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Extract item IDs and balances
        item_ids = []
        item_balances = []

        for item_data in items_data:
            try:
                item_id = UUID(item_data.get("item_id"))
                balance = float(item_data.get("balance", 0.0)) if "balance" in item_data else None
                item_ids.append(item_id)
                item_balances.append(balance)
            except (ValueError, TypeError) as e:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"Invalid item data format: {str(e)}"
                ).model_dump()

        # Verify all items exist
        item_count = db.query(Item).filter(Item.uuid.in_(item_ids)).count()
        if item_count != len(item_ids):
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="One or more items not found"
            ).model_dump()

        try:
            mappings = create_multiple_user_item_mappings(
                db=db,
                user_id=user_id,
                item_ids=item_ids,
                item_balances=item_balances
            )

            return ProjectServiceResponse(
                data={
                    "mapped_count": len(mappings),
                    "user_id": str(user_id)
                },
                message="Items assigned to user successfully",
                status_code=200
            ).model_dump()
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error in map_multiple_items_to_user: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping items to user: {str(db_error)}"
            ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in map_multiple_items_to_user API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while mapping items to user"
        ).model_dump()


@admin_app.delete(
    "/project_item_mapping/{project_id}/{item_id}",
    tags=["admin_panel"],
    description="Remove an item from a project"
)
def remove_item_from_project(
    project_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to remove items from project"
            ).model_dump()

        # Check if project exists
        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Check if item exists
        item = db.query(Item).filter(Item.uuid == item_id).first()
        if not item:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Item not found"
            ).model_dump()

        # Remove the mapping
        result = remove_project_item_mapping(db=db, item_id=item_id, project_id=project_id)

        if not result:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Item is not mapped to this project"
            ).model_dump()

        return ProjectServiceResponse(
            data=None,
            message="Item removed from project successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in remove_item_from_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while removing item from project"
        ).model_dump()


@admin_app.delete(
    "/project_user_mapping/{project_id}/{user_id}",
    tags=["admin_panel"],
    description="Remove a user from a project"
)
def remove_user_from_project(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to remove users from project"
            ).model_dump()

        # Check if project exists
        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Check if user exists
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Remove the mapping
        result = remove_project_user_mapping(db=db, user_id=user_id, project_id=project_id)

        if not result:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User is not mapped to this project"
            ).model_dump()

        return ProjectServiceResponse(
            data=None,
            message="User removed from project successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in remove_user_from_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while removing user from project"
        ).model_dump()


@admin_app.delete(
    "/user_item_mapping/{user_id}/{item_id}",
    tags=["admin_panel"],
    description="Remove an item from a user"
)
def remove_item_from_user(
    user_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to remove items from user"
            ).model_dump()

        # Check if user exists
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Check if item exists
        item = db.query(Item).filter(Item.uuid == item_id).first()
        if not item:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Item not found"
            ).model_dump()

        # Remove the mapping
        result = remove_user_item_mapping(db=db, user_id=user_id, item_id=item_id)

        if not result:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Item is not mapped to this user"
            ).model_dump()

        return ProjectServiceResponse(
            data=None,
            message="Item removed from user successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in remove_item_from_user API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while removing item from user"
        ).model_dump()


@admin_app.get(
    "/user/{user_id}/items",
    tags=["admin_panel"],
    deprecated=True
)
def get_user_items(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Verify user exists
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Get all items mapped to this user
        user_items = (
            db.query(Item, UserItemMap)
            .join(UserItemMap, Item.uuid == UserItemMap.item_id)
            .filter(UserItemMap.user_id == user_id)
            .all()
        )

        items_list = [{
            "uuid": str(item.uuid),
            "name": item.name,
            "category": item.category,
            "list_tag": item.list_tag,
            "has_additional_info": item.has_additional_info,
            "item_balance": item_mapping.item_balance
        } for item, item_mapping in user_items]

        return ProjectServiceResponse(
            data=items_list,
            message="User items fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_user_items API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching user items"
        ).model_dump()


def get_project_items(db: Session, project_id: UUID, current_user: User = None):
    try:
        # Query ProjectItemMap joined with Item to get item UUID and name
        # Use a subquery to handle potential duplicates by taking the most recent mapping
        subquery = (
            db.query(
                ProjectItemMap.project_id,
                ProjectItemMap.item_id,
                func.max(ProjectItemMap.id).label('max_id')
            )
            .filter(ProjectItemMap.project_id == project_id)
            .group_by(ProjectItemMap.project_id, ProjectItemMap.item_id)
            .subquery()
        )

        project_items = (
            db.query(ProjectItemMap, Item)
            .join(subquery, ProjectItemMap.id == subquery.c.max_id)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .all()
        )

        items_list = [
            {
                "uuid": str(item.Item.uuid),
                "name": item.Item.name,
                "category": item.Item.category,
                "remaining_balance": item.ProjectItemMap.item_balance,
                "list_tag": item.Item.list_tag,
                "has_additional_info": item.Item.has_additional_info
            } for item in project_items
        ]

        return {
            "data": items_list,
            "message": "Project items fetched successfully",
            "status_code": 200
        }
    except Exception as e:
        logger.error(f"Error in get_project_items function: {str(e)}")
        return {
            "data": [],
            "message": "An error occurred while fetching project items",
            "status_code": 500
        }

@admin_app.get(
    "/{project_id}/items",
    tags=["admin_panel"]
)
def get_project_items_list(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Query ProjectItemMap joined with Item to get item UUID and name
        # Use a subquery to handle potential duplicates by taking the most recent mapping
        subquery = (
            db.query(
                ProjectItemMap.project_id,
                ProjectItemMap.item_id,
                func.max(ProjectItemMap.id).label('max_id')
            )
            .filter(ProjectItemMap.project_id == project_id)
            .group_by(ProjectItemMap.project_id, ProjectItemMap.item_id)
            .subquery()
        )

        project_items = (
            db.query(ProjectItemMap, Item)
            .join(subquery, ProjectItemMap.id == subquery.c.max_id)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .all()
        )

        items_list = [
            {
                "uuid": str(item.Item.uuid),
                "project_map_uuid": str(item.ProjectItemMap.uuid),
                "name": item.Item.name,
                "category": item.Item.category,
                "remaining_balance": item.ProjectItemMap.item_balance,
                "list_tag": item.Item.list_tag,
                "has_additional_info": item.Item.has_additional_info
            } for item in project_items
        ]

        return ProjectServiceResponse(
            data=items_list,
            message="Project items fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in get_project_items_list API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching project items"
        ).model_dump()


@admin_app.get(
    "/{project_id}/users",
    tags=["admin_panel"]
)
def get_project_users(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:
        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        user_mappings = db.query(ProjectUserMap).filter(ProjectUserMap.project_id == project_id).all()

        user_ids = [mapping.user_id for mapping in user_mappings]
        users = db.query(User).filter(User.uuid.in_(user_ids)).all()

        user_response = []
        for user in users:
            person_data = None
            if user.person:
                person_data = {
                    "uuid": str(user.person.uuid),
                    "name": user.person.name,
                    "account_number": user.person.account_number,
                    "ifsc_code": user.person.ifsc_code,
                    "phone_number": user.person.phone_number,
                    "upi_number": user.person.upi_number
                }
            user_response.append({
                "uuid": str(user.uuid),
                "name": user.name,
                "phone": user.phone,
                "role": user.role,
                "photo_path": user.photo_path,
                "person": person_data
            })

        return ProjectServiceResponse(
            data=user_response,
            message="Project users fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in get_project_users API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching project users"
        ).model_dump()

@admin_app.get(
    "/{user_id}/projects",
    tags=["admin_panel"]
    )
def get_user_projects(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        project_mappings = db.query(ProjectUserMap).filter(ProjectUserMap.user_id == user_id).all()

        project_ids = [mapping.project_id for mapping in project_mappings]
        projects = db.query(Project).filter(Project.uuid.in_(project_ids)).all()

        project_response = []
        for project in projects:
            # Get total balance (for backward compatibility)
            # total_balance = (
            #     db.query(func.sum(ProjectBalance.adjustment))
            #     .filter(ProjectBalance.project_id == project.uuid)
            #     .scalar()
            # ) or 0.0

            # Get PO balance
            # po_balance = project.po_balance if project.po_balance else 0

            # Get estimated balance
            estimated_balance = project.estimated_balance if project.estimated_balance else 0

            # Get actual balance
            actual_balance = project.actual_balance if project.actual_balance else 0

            project_response.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "estimated_balance": estimated_balance,
                "actual_balance": actual_balance
            })
        return ProjectServiceResponse(
            data=project_response,
            message="User projects fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in get_user_projects API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching user projects"
        ).model_dump()

# @admin_app.get(
#     "/user/{user_id}/details",
#     tags=["admin_panel"]
# )
# def get_user_details(
#     user_id: UUID,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     try:
#         # Role check
#         if current_user.role not in [
#             UserRole.SUPER_ADMIN.value,
#             UserRole.ADMIN.value,
#             UserRole.PROJECT_MANAGER.value,
#         ]:
#             return ProjectServiceResponse(
#                 data=None,
#                 status_code=403,
#                 message="Unauthorized to view user details"
#             ).model_dump()

#         # Get user
#         user = db.query(User).filter(User.uuid == user_id).first()
#         if not user:
#             return ProjectServiceResponse(
#                 data=None,
#                 status_code=404,
#                 message="User not found"
#             ).model_dump()

#         # Get account info (Person)
#         person = db.query(Person).filter(Person.user_id == user.uuid).first()
#         account_info = {
#             "name": person.name if person else None,
#             "account_number": person.account_number if person else None,
#             "ifsc_code": person.ifsc_code if person else None,
#             "phone_number": person.phone_number if person else None,
#             "upi_number": person.upi_number if person else None,
#             "parent_id": str(person.parent_id) if person and person.parent_id else None
#         }

#         # Get all projects assigned to the user
#         project_mappings = db.query(ProjectUserMap).filter(ProjectUserMap.user_id == user_id).all()
#         project_ids = [mapping.project_id for mapping in project_mappings]
#         projects = db.query(Project).filter(Project.uuid.in_(project_ids)).all()

#         # For each project, get items mapped to the user (if any)
#         project_dict = {}
#         for project in projects:
#             # Get items for this user in this project
#             item_mappings = (
#                 db.query(Item)
#                 .join(ProjectUserItemMap, Item.uuid == ProjectUserItemMap.item_id)
#                 .filter(ProjectUserItemMap.user_id == user_id, ProjectUserItemMap.project_id == project.uuid)
#                 .all()
#             )
#             items_list = [
#                 {
#                     "uuid": str(item.uuid),
#                     "name": item.name,
#                     "category": item.category,
#                     "list_tag": item.list_tag,
#                     "has_additional_info": item.has_additional_info
#                 }
#                 for item in item_mappings
#             ]
#             project_dict[project.uuid] = {
#                 "uuid": str(project.uuid),
#                 "name": project.name,
#                 "description": project.description,
#                 "location": project.location,
#                 "estimated_balance": project.estimated_balance or 0,
#                 "actual_balance": project.actual_balance or 0,
#                 "items": items_list
#             }

#         user_details = {
#             "uuid": str(user.uuid),
#             "name": user.name,
#             "phone": user.phone,
#             "role": user.role,
#             "account_info": account_info,
#             "projects": list(project_dict.values())
#         }

#         return ProjectServiceResponse(
#             data=user_details,
#             message="User details fetched successfully",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error in get_user_details API: {str(e)}")
#         return ProjectServiceResponse(
#             data=None,
#             status_code=500,
#             message="An error occurred while fetching user details"
#         ).model_dump()


@admin_app.get(
    "/user/{user_id}/details",
    tags=["admin_panel"]
)
def get_user_details(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Allow only privileged roles to use this API
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to view user details"
            ).model_dump()

        # Fetch the target user whose details are being requested
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Fetch account info from Person table
        person = db.query(Person).filter(Person.user_id == user.uuid).first()
        account_info = {
            "name": person.name if person else None,
            "account_number": person.account_number if person else None,
            "ifsc_code": person.ifsc_code if person else None,
            "phone_number": person.phone_number if person else None,
            "upi_number": person.upi_number if person else None,
            "parent_id": str(person.parent_id) if person and person.parent_id else None
        }

        # Fetch projects assigned to the user
        project_mappings = db.query(ProjectUserMap).filter(ProjectUserMap.user_id == user_id).all()
        project_ids = [mapping.project_id for mapping in project_mappings]
        projects = db.query(Project).filter(Project.uuid.in_(project_ids)).all()

        # Determine if user is in privileged role
        privileged_roles = [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
            UserRole.ACCOUNTANT.value,
        ]
        is_privileged = user.role in privileged_roles

        # Fetch project-wise item mappings
        project_dict = {}
        for project in projects:
            if is_privileged:
                # Fetch all items for the project (global project item map)
                item_mappings = (
                    db.query(Item)
                    .join(ProjectItemMap, Item.uuid == ProjectItemMap.item_id)
                    .filter(ProjectItemMap.project_id == project.uuid)
                    .all()
                )
            else:
                # Fetch only items mapped to the user under that project
                item_mappings = (
                    db.query(Item)
                    .join(ProjectUserItemMap, Item.uuid == ProjectUserItemMap.item_id)
                    .filter(
                        ProjectUserItemMap.user_id == user_id,
                        ProjectUserItemMap.project_id == project.uuid
                    )
                    .all()
                )

            items_list = [
                {
                    "uuid": str(item.uuid),
                    "name": item.name,
                    "category": item.category,
                    "list_tag": item.list_tag,
                    "has_additional_info": item.has_additional_info
                }
                for item in item_mappings
            ]

            project_dict[project.uuid] = {
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "estimated_balance": project.estimated_balance or 0,
                "actual_balance": project.actual_balance or 0,
                "items": items_list
            }

        # Final user detail response
        user_details = {
            "uuid": str(user.uuid),
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "account_info": account_info,
            "projects": list(project_dict.values())
        }

        return ProjectServiceResponse(
            data=user_details,
            message="User details fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in get_user_details API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching user details"
        ).model_dump()



@admin_app.get(
    "/user/{user_id}/project-items",
    tags=["admin_panel"],
    description="Get all projects and their assigned items for a specific user",
    deprecated=True
)
def get_user_project_items_old(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Verify user exists
        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Get all projects mapped to this user
        project_mappings = (
            db.query(Project, ProjectUserMap)
            .join(ProjectUserMap, Project.uuid == ProjectUserMap.project_id)
            .filter(ProjectUserMap.user_id == user_id)
            .all()
        )

        projects_list = []
        for project, _ in project_mappings:
            # Get only the items that are mapped to this project
            project_items = (
                db.query(Item, ProjectItemMap)
                .join(ProjectItemMap, Item.uuid == ProjectItemMap.item_id)
                .filter(ProjectItemMap.project_id == project.uuid)
                .all()
            )

            items_list = [{
                "uuid": str(item.uuid),
                "name": item.name,
                "category": item.category,
                "list_tag": item.list_tag,
                "has_additional_info": item.has_additional_info,
                "balance": item_mapping.item_balance
            } for item, item_mapping in project_items]

            # Get project balances
            # total_balance = (
            #     db.query(func.sum(ProjectBalance.adjustment))
            #     .filter(ProjectBalance.project_id == project.uuid)
            #     .scalar()
            # ) or 0.0

            projects_list.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "po_balance": project.po_balance,
                "estimated_balance": project.estimated_balance,
                "actual_balance": project.actual_balance,
                "items_list": items_list  # Renamed to avoid conflict with built-in method
            })

        user_response = {
            "uuid": str(user.uuid),
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "projects": projects_list
        }

        return ProjectServiceResponse(
            data=user_response,
            message="User project items fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in get_user_project_items API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching user project items"
        ).model_dump()


# Invoice APIs
# @admin_app.post(
#     "/invoices",
#     tags=["Invoices"],
#     status_code=201,
#     description="""
#     Upload a new invoice with optional file attachment.

#     Request body should be sent as a form with 'request' field containing a JSON string with the following structure:
#     ```json
#     {
#         "project_id": "123e4567-e89b-12d3-a456-426614174000",
#         "project_po_id": "456e7890-e89b-12d3-a456-426614174001",
#         "client_name": "ABC Company",
#         "invoice_item": "Construction Materials",
#         "amount": 500.0,
#         "description": "Invoice for materials",
#         "due_date": "2025-06-15"
#     }
#     ```

#     The invoice file can be uploaded as a file in the 'invoice_file' field.
#     """
# )
# def upload_invoice(
#     request: str = Form(..., description="JSON string containing invoice details (project_id, amount, description)"),
#     invoice_file: Optional[UploadFile] = File(None, description="Invoice file to upload"),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     Upload a new invoice with optional file attachment.
#     """
#     try:
#         # Parse the request data from form
#         import json
#         request_data = json.loads(request)
#         invoice_request = InvoiceCreateRequest(**request_data)

#         # Verify project exists
#         project = db.query(Project).filter(
#             Project.uuid == invoice_request.project_id,
#             Project.is_deleted.is_(False)
#         ).first()

#         if not project:
#             return ProjectServiceResponse(
#                 data=None,
#                 status_code=404,
#                 message="Project not found"
#             ).model_dump()

#         # Verify PO exists if provided
#         project_po = None
#         if invoice_request.project_po_id:
#             project_po = db.query(ProjectPO).filter(
#                 ProjectPO.uuid == invoice_request.project_po_id,
#                 ProjectPO.project_id == invoice_request.project_id,
#                 ProjectPO.is_deleted.is_(False)
#             ).first()

#             if not project_po:
#                 return ProjectServiceResponse(
#                     data=None,
#                     status_code=404,
#                     message="Project PO not found"
#                 ).model_dump()

#         # Handle invoice file upload if provided
#         file_path = None
#         if invoice_file:
#             upload_dir = "uploads/invoices"
#             os.makedirs(upload_dir, exist_ok=True)

#             # Create a unique filename to avoid collisions
#             file_ext = os.path.splitext(invoice_file.filename)[1]
#             unique_filename = f"Invoice_{str(uuid4())}{file_ext}"
#             file_path = os.path.join(upload_dir, unique_filename)

#             # Save the file
#             with open(file_path, "wb") as buffer:
#                 buffer.write(invoice_file.file.read())

#         # Parse due_date string to datetime
#         from datetime import datetime
#         try:
#             due_date = datetime.strptime(invoice_request.due_date, "%Y-%m-%d")
#         except ValueError:
#             try:
#                 due_date = datetime.strptime(invoice_request.due_date, "%Y-%m-%d %H:%M:%S")
#             except ValueError:
#                 return ProjectServiceResponse(
#                     data=None,
#                     status_code=400,
#                     message="Invalid due_date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
#                 ).model_dump()

#         # Create new invoice
#         new_invoice = Invoice(
#             project_id=invoice_request.project_id,
#             project_po_id=invoice_request.project_po_id,
#             client_name=invoice_request.client_name,
#             invoice_item=invoice_request.invoice_item,
#             amount=invoice_request.amount,
#             description=invoice_request.description,
#             due_date=due_date,
#             file_path=file_path,
#             status="uploaded",
#             payment_status="not_paid",
#             total_paid_amount=0.0,
#             created_by=current_user.uuid
#         )
#         db.add(new_invoice)
#         db.flush()

#         # Create log entry
#         log_entry = Log(
#             uuid=str(uuid4()),
#             entity="Invoice",
#             action="Create",
#             entity_id=new_invoice.uuid,
#             performed_by=current_user.uuid,
#         )
#         db.add(log_entry)
#         db.commit()
#         db.refresh(new_invoice)

#         return ProjectServiceResponse(
#             data={
#                 "uuid": str(new_invoice.uuid),
#                 "project_id": str(new_invoice.project_id),
#                 "client_name": new_invoice.client_name,
#                 "invoice_item": new_invoice.invoice_item,
#                 "amount": new_invoice.amount,
#                 "description": new_invoice.description,
#                 "due_date": new_invoice.due_date.strftime("%Y-%m-%d"),
#                 "file_path": constants.HOST_URL + "/" + new_invoice.file_path if new_invoice.file_path else None,
#                 "status": new_invoice.status,
#                 "created_at": new_invoice.created_at.strftime("%Y-%m-%d %H:%M:%S")
#             },
#             message="Invoice uploaded successfully",
#             status_code=201
#         ).model_dump()
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error in upload_invoice API: {str(e)}")
#         return ProjectServiceResponse(
#             data=None,
#             status_code=500,
#             message=f"An error occurred while uploading invoice: {str(e)}"
#         ).model_dump()

@admin_app.post(
    "/project/{project_id}/po/{po_id}/invoice",
    tags=["Invoices"],
    status_code=201,
    description="""
    Upload a single invoice under a specific project and PO with optional file attachment.

    📌 **Instructions:**
    - `project_id` and `po_id` must be passed in the **URL path**.
    - `invoice` should be a **JSON string**.
    - You may attach a single file using `invoice_file`.

    **Example JSON string for `invoice` field:**
    ```json
    {
    "client_name": "ABC Constructions Pvt Ltd",
    "invoice_number": "INV-2025-0034",
    "invoice_date": "2025-06-14",
    "invoice_items": [
        {
        "item_name": "Steel Bars",
        "basic_value": 300
        },
        {
        "item_name": "Sand",
        "basic_value": 150
        }
    ],
    "amount": 450.0,
    "description": "Material delivery for basement",
    "due_date": "2025-06-25"
    }
    '''
    """
)
def upload_single_invoice_for_po(
    project_id: UUID,
    po_id: UUID,
    invoice: str = Form(..., description="JSON string of invoice object"),
    invoice_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,  # Add this
):
    try:
        try:
            item = json.loads(invoice)
        except json.JSONDecodeError:
            response.status_code = 400
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Invalid JSON in 'invoice' field"
            ).model_dump()

        # Validate project
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        if not project:
            response.status_code = 404
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Validate PO
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).first()
        if not po:
            response.status_code = 404
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found under this project"
            ).model_dump()
        
        # Check if invoice number already exists
        invoice_number = item.get("invoice_number")
        existing_invoice = (
            db.query(Invoice)
            .filter(Invoice.invoice_number == invoice_number)
            .first()
        )
        if existing_invoice:
            response.status_code = 400
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Please enter a unique invoice number. This invoice number already exists."
            ).model_dump()

        # Parse due_date
        try:
            due_date = datetime.strptime(item["due_date"], "%Y-%m-%d")
        except (KeyError, ValueError):
            response.status_code = 400
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Invalid or missing due_date. Use YYYY-MM-DD"
            ).model_dump()

        # Parse invoice_date
        invoice_date = None
        if item.get("invoice_date"):
            try:
                invoice_date = datetime.strptime(item["invoice_date"], "%Y-%m-%d").date()
            except ValueError:
                response.status_code = 400
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message="Invalid invoice_date. Use YYYY-MM-DD"
                ).model_dump()

        # Save file if present
        file_path = None
        if invoice_file:
            ext = os.path.splitext(invoice_file.filename)[1]
            filename = f"Invoice_{str(uuid4())}{ext}"
            upload_dir = "uploads/invoices"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(invoice_file.file.read())

        # Create Invoice
        new_invoice = Invoice(
            project_id=project.uuid,
            project_po_id=po_id,
            client_name=item.get("client_name"),
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            amount=item.get("amount"),
            description=item.get("description"),
            due_date=due_date,
            file_path=file_path,
            status="uploaded",
            payment_status="not_paid",
            total_paid_amount=0.0,
            created_by=current_user.uuid
        )
        db.add(new_invoice)
        db.flush()

        # Add invoice items
        for sub_item in item.get("invoice_items", []):
            name = sub_item.get("item_name")
            value = sub_item.get("basic_value")
            if name and value is not None:
                db.add(InvoiceItem(
                    invoice_id=new_invoice.uuid,
                    item_name=name,
                    basic_value=value
                ))

        # Log entry
        db.add(Log(
            uuid=str(uuid4()),
            entity="Invoice",
            action="Create",
            entity_id=new_invoice.uuid,
            performed_by=current_user.uuid,
        ))

        db.commit()

        # Success—201 status remains default (set in decorator)
        return ProjectServiceResponse(
            data={
                "uuid": str(new_invoice.uuid),
                "client_name": new_invoice.client_name,
                "invoice_number": new_invoice.invoice_number,
                "amount": new_invoice.amount,
                "due_date": new_invoice.due_date.strftime("%Y-%m-%d"),
                "file_path": constants.HOST_URL + "/" + file_path if file_path else None,
            },
            message="Invoice uploaded successfully",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        # Always set 500 in response
        if response:
            response.status_code = 500
        logger.error(f"Error in upload_single_invoice_for_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while uploading the invoice: {str(e)}"
        ).model_dump()

@admin_app.post(
    "/project/{project_id}/po/{po_id}/invoices/batch",
    tags=["Invoices"],
    status_code=201,
    description="""
 **Upload Multiple Invoices Under a Specific PO**

This endpoint allows you to upload multiple invoices for a given project and purchase order (PO), optionally including files.

🛠 **Usage Instructions:**
- `project_id` and `po_id` must be passed in the **URL path**.
- `invoices` should be a **JSON stringified list** of invoice objects.
- You can optionally attach multiple files using `invoice_files` (they must match order of invoices).

 **Example `invoices` JSON string:**
```json
  [
  {
    "client_name": "ABC Constructions Pvt Ltd",
    "invoice_number": "INV-2025-1001",
    "invoice_date": "2025-06-14",
    "invoice_items": [
      {
        "item_name": "Cement",
        "basic_value": 300
      },
      {
        "item_name": "Steel Rods",
        "basic_value": 200
      }
    ],
    "amount": 500.0,
    "description": "Materials for Phase 1",
    "due_date": "2025-06-25"
  },
  {
    "client_name": "XYZ Infra Co.",
    "invoice_number": "INV-2025-1002",
    "invoice_date": "2025-06-16",
    "invoice_items": [
      {
        "item_name": "Bricks",
        "basic_value": 120
      },
      {
        "item_name": "Gravel",
        "basic_value": 180
      }
    ],
    "amount": 300.0,
    "description": "Foundation work supplies",
    "due_date": "2025-06-27"
  }
]
    Attachments:

invoice_files: Optional array of file uploads. Files are matched index-wise with invoices.

📌 Notes:

Do not include project_id or po_id in the invoice objects — they are inferred from the path.

Dates must follow format: YYYY-MM-DD.

"""
)
def upload_multiple_invoices_for_po(
    project_id: UUID,
    po_id: UUID,
    invoices: str = Form(..., description="JSON string list of invoices"),
    invoice_files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    response: Response = None,  # Add response!
):
    try:
        # Parse and validate input
        try:
            invoice_list = json.loads(invoices)
        except json.JSONDecodeError:
            response.status_code = 400
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Invalid JSON in 'invoices' field"
            ).model_dump()

        if not isinstance(invoice_list, list):
            response.status_code = 400
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Invoices must be a list of invoice objects"
            ).model_dump()
        
        # Validate project
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        if not project:
            response.status_code = 404
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Validate PO
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.is_deleted.is_(False),
            ProjectPO.project_id == project_id
        ).first()
        if not po:
            response.status_code = 404
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found under this project"
            ).model_dump()

        # Check for duplicate invoice numbers in DB
        for idx, item in enumerate(invoice_list):
            invoice_number = item.get("invoice_number")
            if not invoice_number:
                response.status_code = 400
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"Missing invoice_number at index {idx}"
                ).model_dump()
            existing_invoice = (
                db.query(Invoice)
                .filter(Invoice.invoice_number == invoice_number)
                .first()
            )
            if existing_invoice:
                response.status_code = 400
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"Please enter a unique invoice number. The invoice number '{invoice_number}' already exists (at index {idx})."
                ).model_dump()

        created_invoices = []

        for index, item in enumerate(invoice_list):
            # Validate and parse due_date
            try:
                due_date = datetime.strptime(item["due_date"], "%Y-%m-%d")
            except (KeyError, ValueError):
                response.status_code = 400
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"Invalid or missing due_date at index {index}. Use YYYY-MM-DD"
                ).model_dump()

            # Parse invoice_date
            invoice_date = None
            if item.get("invoice_date"):
                try:
                    invoice_date = datetime.strptime(item["invoice_date"], "%Y-%m-%d").date()
                except ValueError:
                    response.status_code = 400
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message=f"Invalid invoice_date at index {index}. Use YYYY-MM-DD"
                    ).model_dump()

            # Optional file
            file_path = None
            if invoice_files and len(invoice_files) > index:
                file = invoice_files[index]
                ext = os.path.splitext(file.filename)[1]
                filename = f"Invoice_{str(uuid4())}{ext}"
                upload_dir = "uploads/invoices"
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, filename)
                with open(file_path, "wb") as buffer:
                    buffer.write(file.file.read())

            # Save Invoice
            new_invoice = Invoice(
                project_id=project.uuid,
                project_po_id=po_id,
                client_name=item.get("client_name"),
                invoice_number=item.get("invoice_number"),
                invoice_date=invoice_date,
                amount=item.get("amount"),
                description=item.get("description"),
                due_date=due_date,
                file_path=file_path,
                status="uploaded",
                payment_status="not_paid",
                total_paid_amount=0.0,
                created_by=current_user.uuid
            )
            db.add(new_invoice)
            db.flush()

            # Save Invoice Items
            for sub_item in item.get("invoice_items", []):
                name = sub_item.get("item_name")
                value = sub_item.get("basic_value")
                if name and value is not None:
                    db.add(InvoiceItem(
                        invoice_id=new_invoice.uuid,
                        item_name=name,
                        basic_value=value
                    ))

            # Log entry
            db.add(Log(
                uuid=str(uuid4()),
                entity="Invoice",
                action="Create",
                entity_id=new_invoice.uuid,
                performed_by=current_user.uuid,
            ))

            created_invoices.append({
                "uuid": str(new_invoice.uuid),
                "amount": new_invoice.amount,
                "client_name": new_invoice.client_name,
                "invoice_number": new_invoice.invoice_number,
                "invoice_date": new_invoice.invoice_date.isoformat() if new_invoice.invoice_date else None,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "file_path": constants.HOST_URL + "/" + file_path if file_path else None
            })

        db.commit()

        return ProjectServiceResponse(
            data={"invoices": created_invoices},
            message=f"{len(created_invoices)} invoices uploaded successfully",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        if response:
            response.status_code = 500
        logger.error(f"Error in upload_multiple_invoices_for_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while uploading invoices: {str(e)}"
        ).model_dump()




@admin_app.put(
    "/invoices/{invoice_id}/status",
    tags=["Invoices"],
    description="""
    Update the status of an invoice (e.g., mark as received).

    Request body should contain:
    ```json
    {
        "status": "received"
    }
    ```

    Possible status values: "uploaded", "received"
    """
)
def update_invoice_status(
    invoice_id: UUID,
    status_request: InvoiceStatusUpdateRequest = Body(
        ...,
        description="Status update information",
        example={"status": "received"}
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the status of an invoice (e.g., mark as received).
    """
    try:
        # Verify user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to update invoice status"
            ).model_dump()

        # Find the invoice
        invoice = db.query(Invoice).filter(
            Invoice.uuid == invoice_id,
            Invoice.is_deleted.is_(False)
        ).first()

        if not invoice:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice not found"
            ).model_dump()

        # Update status
        invoice.status = status_request.status

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Invoice",
            action="Status Update",
            entity_id=invoice_id,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data={
                "uuid": str(invoice.uuid),
                "status": invoice.status
            },
            message="Invoice status updated successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_invoice_status API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while updating invoice status: {str(e)}"
        ).model_dump()


@admin_app.get(
    "/invoices",
    tags=["Invoices"]
)
def list_invoices(
    project_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all invoices, optionally filtered by project_id and/or status.
    """
    try:
        query = db.query(Invoice).filter(Invoice.is_deleted.is_(False))

        # Apply filters if provided
        if project_id:
            query = query.filter(Invoice.project_id == project_id)

        if status:
            query = query.filter(Invoice.status == status)

        invoices = query.all()

        invoice_list = []
        for invoice in invoices:
            invoice_list.append({
                "uuid": str(invoice.uuid),
                "project_id": str(invoice.project_id),
                "client_name": invoice.client_name,
                "invoice_items": [
                    {
                        "item_name": item.item_name,
                        "basic_value": item.basic_value
                    } for item in invoice.invoice_items
                ],
                "amount": invoice.amount,
                "description": invoice.description,
                "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else None,
                "file_path": constants.HOST_URL + "/" + invoice.file_path if invoice.file_path else None,
                "status": invoice.status,
                "created_at": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return ProjectServiceResponse(
            data=invoice_list,
            message="Invoices fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in list_invoices API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching invoices: {str(e)}"
        ).model_dump()



@admin_app.get(
    "/invoices/{invoice_id}",
    tags=["Invoices"]
)
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details of a specific invoice.
    """
    try:
        invoice = db.query(Invoice).filter(
            Invoice.uuid == invoice_id,
            Invoice.is_deleted.is_(False)
        ).first()

        if not invoice:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice not found"
            ).model_dump()

        # Get project details
        project = db.query(Project).filter(Project.uuid == invoice.project_id).first()

        return ProjectServiceResponse(
            data={
                "uuid": str(invoice.uuid),
                "project_id": str(invoice.project_id),
                "project_name": project.name if project else None,
                "client_name": invoice.client_name,
                "invoice_items": [
                    {
                        "item_name": item.item_name,
                        "basic_value": item.basic_value
                    } for item in invoice.invoice_items
                ],
                "amount": invoice.amount,
                "description": invoice.description,
                "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else None,
                "file_path": constants.HOST_URL + "/" + invoice.file_path if invoice.file_path else None,
                "status": invoice.status,
                "created_at": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S") if invoice.created_at else None,
                "created_by": str(invoice.created_by)
            },
            message="Invoice fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_invoice API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching invoice: {str(e)}"
        ).model_dump()


@admin_app.put(
    "/invoices/{invoice_id}",
    tags=["Invoices"],
    description="""
    Update invoice information.

    Request body should contain fields to update:
    ```json
    {
        "client_name": "Updated Company",
        "amount": 600.0,
        "description": "Updated",
        "invoice_number": "INV-2023-01-01",
        "invoice_date": "2025-06-15",
        "due_date": "2025-07-15",
        "invoice_items": [
            { "item_name": "Updated Cement", "basic_value": 300 }
        ]
    }
    ```
    """
)
def update_invoice(
    invoice_id: UUID,
    update_request: InvoiceUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # ✅ Role Check
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to update invoice"
            ).model_dump()

        # ✅ Fetch invoice
        invoice = db.query(Invoice).filter(
            Invoice.uuid == invoice_id,
            Invoice.is_deleted.is_(False)
        ).first()

        if not invoice:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice not found"
            ).model_dump()

        # ✅ Update fields
        if update_request.client_name is not None:
            invoice.client_name = update_request.client_name

        if update_request.amount is not None:
            invoice.amount = update_request.amount

        if update_request.description is not None:
            invoice.description = update_request.description

        if update_request.invoice_number is not None:
            invoice.invoice_number = update_request.invoice_number

        if update_request.invoice_date is not None:
            invoice.invoice_date = update_request.invoice_date

        if update_request.due_date is not None:
            try:
                invoice.due_date = datetime.strptime(update_request.due_date, "%Y-%m-%d")
            except ValueError:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message="Invalid due_date format. Use YYYY-MM-DD"
                ).model_dump()

        # ✅ Replace invoice_items if provided
        if update_request.invoice_items is not None:
            # Delete old items
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.uuid).delete()
            # Add new ones
            for item in update_request.invoice_items:
                db.add(InvoiceItem(
                    invoice_id=invoice.uuid,
                    item_name=item.item_name,
                    basic_value=item.basic_value
                ))

        # ✅ Add log
        db.add(Log(
            uuid=str(uuid4()),
            entity="Invoice",
            action="Update",
            entity_id=invoice_id,
            performed_by=current_user.uuid,
        ))

        db.commit()
        db.refresh(invoice)

        return ProjectServiceResponse(
            data={
                "uuid": str(invoice.uuid),
                "project_id": str(invoice.project_id),
                "client_name": invoice.client_name,
                "amount": invoice.amount,
                "description": invoice.description,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else None,
                "invoice_items": [
                    {
                        "item_name": i.item_name,
                        "basic_value": i.basic_value
                    } for i in invoice.invoice_items
                ],
                "file_path": constants.HOST_URL + "/" + invoice.file_path if invoice.file_path else None,
                "status": invoice.status,
                "created_at": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S")
            },
            message="Invoice updated successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_invoice API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while updating invoice: {str(e)}"
        ).model_dump()



@admin_app.delete(
    "/invoices/{invoice_id}",
    tags=["Invoices"],
    description="Soft delete an invoice"
)
def delete_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete an invoice.
    """
    try:
        # Verify user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to delete invoice"
            ).model_dump()

        # Find the invoice
        invoice = db.query(Invoice).filter(
            Invoice.uuid == invoice_id,
            Invoice.is_deleted.is_(False)
        ).first()

        if not invoice:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice not found"
            ).model_dump()

        # Soft delete the invoice
        invoice.is_deleted = True

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Invoice",
            action="Delete",
            entity_id=invoice_id,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data={"deleted_invoice_id": str(invoice_id)},
            message="Invoice deleted successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in delete_invoice API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while deleting invoice: {str(e)}"
        ).model_dump()
    
@admin_app.get(
    "/po/{po_id}/invoices",
    tags=["Invoices"],
    status_code=200,
    description="Get all invoices created against a specific PO"
)
def get_invoices_by_po(
    po_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Validate PO exists
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.is_deleted.is_(False)
        ).first()

        if not po:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found"
            ).model_dump()

        # Optional: permissions check
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to view invoices"
            ).model_dump()

        # Fetch all invoices linked to this PO
        invoices = db.query(Invoice).filter(
            Invoice.project_po_id == po_id,
            Invoice.is_deleted.is_(False)
        ).order_by(Invoice.created_at.desc()).all()


        total_invoice_amount = 0.0
        total_po_paid = 0.0
        invoice_list = []

        
        for inv in invoices:
            total_invoice_amount += inv.amount or 0.0
            if inv.payment_status in ["partially_paid", "fully_paid"]:
                total_po_paid += inv.total_paid_amount or 0.0

            invoice_list.append({
                "uuid": str(inv.uuid),
                "project_id": str(inv.project_id),
                "client_name": inv.client_name,
                "invoice_items": [
                    {
                        "item_name": item.item_name,
                        "basic_value": item.basic_value
                    } for item in inv.invoice_items
                ],
                "amount": inv.amount,
                "description": inv.description,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else None,
                "payment_status": inv.payment_status,
                "total_paid_amount": inv.total_paid_amount,
                "file_url": constants.HOST_URL + "/" + inv.file_path if inv.file_path else None,
                "created_at": inv.created_at.strftime("%Y-%m-%d %H:%M:%S") if inv.created_at else None
            })


        return ProjectServiceResponse(
            data={
                "po_id": str(po_id),
                "total_invoices": len(invoice_list),
                "total_po_paid": total_po_paid,
                "total_created_invoice_pending": total_invoice_amount - total_po_paid,
                "invoice_not_generated_amount": po.amount - total_invoice_amount,
                "invoices": invoice_list
            },
            message="Invoices fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_invoices_by_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching invoices: {str(e)}"
        ).model_dump()




# Invoice Payment APIs
# @admin_app.post(
#     "/invoices/{invoice_id}/payments",
#     tags=["Invoice Payments"],
#     status_code=201,
#     description="""
#     Create a payment record for an invoice.

#     Request body should contain:
#     ```json
#     {
#         "amount": 250.0,
#         "payment_date": "2025-06-15",
#         "description": "Partial payment",
#         "payment_method": "bank",
#         "reference_number": "TXN123456"
#     }
#     ```
#     """
# )
# def create_invoice_payment(
#     invoice_id: UUID,
#     payment_request: InvoicePaymentCreateRequest = Body(
#         ...,
#         description="Payment information",
#         example={
#             "amount": 250.0,
#             "payment_date": "2025-06-15",
#             "description": "Partial payment",
#             "payment_method": "bank",
#             "reference_number": "TXN123456"
#         }
#     ),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     Create a payment record for an invoice.
#     """
#     try:
#         # Verify user has permission
#         if current_user.role not in [
#             UserRole.SUPER_ADMIN.value,
#             UserRole.ADMIN.value,
#             UserRole.ACCOUNTANT.value,
#         ]:
#             return ProjectServiceResponse(
#                 data=None,
#                 status_code=403,
#                 message="Not authorized to create invoice payments"
#             ).model_dump()

#         # Find the invoice
#         invoice = db.query(Invoice).filter(
#             Invoice.uuid == invoice_id,
#             Invoice.is_deleted.is_(False)
#         ).first()

#         if not invoice:
#             return ProjectServiceResponse(
#                 data=None,
#                 status_code=404,
#                 message="Invoice not found"
#             ).model_dump()

#         # Parse payment date
#         from datetime import datetime
#         try:
#             payment_date = datetime.strptime(payment_request.payment_date, "%Y-%m-%d").date()
#         except ValueError:
#             return ProjectServiceResponse(
#                 data=None,
#                 status_code=400,
#                 message="Invalid payment_date format. Use YYYY-MM-DD"
#             ).model_dump()

#         # Create new payment record
#         new_payment = InvoicePayment(
#             invoice_id=invoice_id,
#             amount=payment_request.amount,
#             payment_date=payment_date,
#             description=payment_request.description,
#             payment_method=payment_request.payment_method,
#             reference_number=payment_request.reference_number,
#             created_by=current_user.uuid
#         )
#         db.add(new_payment)
#         db.flush()

#         # Update invoice payment status and total paid amount
#         invoice.total_paid_amount += payment_request.amount

#         # Determine payment status
#         if invoice.total_paid_amount >= invoice.amount:
#             invoice.payment_status = "fully_paid"
#         elif invoice.total_paid_amount > 0:
#             invoice.payment_status = "partially_paid"
#         else:
#             invoice.payment_status = "not_paid"

#         # Create log entry
#         log_entry = Log(
#             uuid=str(uuid4()),
#             entity="InvoicePayment",
#             action="Create",
#             entity_id=new_payment.uuid,
#             performed_by=current_user.uuid,
#         )
#         db.add(log_entry)
#         db.commit()
#         db.refresh(new_payment)

#         return ProjectServiceResponse(
#             data={
#                 "uuid": str(new_payment.uuid),
#                 "invoice_id": str(new_payment.invoice_id),
#                 "amount": new_payment.amount,
#                 "payment_date": new_payment.payment_date.strftime("%Y-%m-%d"),
#                 "description": new_payment.description,
#                 "payment_method": new_payment.payment_method,
#                 "reference_number": new_payment.reference_number,
#                 "created_at": new_payment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
#                 "invoice_payment_status": invoice.payment_status,
#                 "invoice_total_paid": invoice.total_paid_amount
#             },
#             message="Invoice payment created successfully",
#             status_code=201
#         ).model_dump()
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error in create_invoice_payment API: {str(e)}")
#         return ProjectServiceResponse(
#             data=None,
#             status_code=500,
#             message=f"An error occurred while creating invoice payment: {str(e)}"
#         ).model_dump()
    
@admin_app.post(
    "/invoices/{invoice_id}/payments",
    tags=["Invoice Payments"],
    status_code=201,
    description="Create multiple payments for an invoice"
)
def create_multiple_invoice_payments(
    invoice_id: UUID,
    payment_request: MultiInvoicePaymentRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # ✅ Role check
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to create invoice payments"
            ).model_dump()

        # ✅ Get Invoice
        invoice = db.query(Invoice).filter(
            Invoice.uuid == invoice_id,
            Invoice.is_deleted.is_(False)
        ).first()
        if not invoice:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice not found"
            ).model_dump()

        # ✅ Get related project (for checking `end_date`)
        project = db.query(Project).filter(
            Project.uuid == invoice.project_id,
            Project.is_deleted.is_(False)
        ).first()

        created_payments = []

        for payment in payment_request.payments:
            # ✅ Parse payment date
            try:
                payment_date = datetime.strptime(payment.payment_date, "%Y-%m-%d").date()
            except ValueError:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"Invalid payment_date format: {payment.payment_date}"
                ).model_dump()

            # ✅ is_late logic
            is_late = False
            if project and project.end_date and payment_date > project.end_date:
                is_late = True

            # ✅ Create InvoicePayment
            new_payment = InvoicePayment(
                invoice_id=invoice_id,
                amount=payment.amount,
                payment_date=payment_date,
                description=payment.description,
                payment_method=payment.payment_method,
                reference_number=payment.reference_number,
                is_late=is_late,
                created_by=current_user.uuid
            )
            db.add(new_payment)
            db.flush()

            created_payments.append({
                "uuid": str(new_payment.uuid),
                "amount": new_payment.amount,
                "payment_date": new_payment.payment_date.strftime("%Y-%m-%d"),
                "description": new_payment.description,
                "payment_method": new_payment.payment_method,
                "reference_number": new_payment.reference_number,
                "is_late": new_payment.is_late
            })

            # ✅ Update invoice totals
            invoice.total_paid_amount += new_payment.amount
            db.commit()
            db.refresh(invoice)

        # ✅ Update invoice payment status
        if invoice.total_paid_amount >= invoice.amount:
            invoice.payment_status = "fully_paid"
        elif invoice.total_paid_amount > 0 or invoice.total_paid_amount < invoice.amount:
            invoice.payment_status = "partially_paid"
        else:
            invoice.payment_status = "not_paid"

        # ✅ Create Log
        log_entry = Log(
            uuid=str(uuid4()),
            entity="InvoicePayment",
            action="BatchCreate",
            entity_id=invoice_id,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data={
                "invoice_id": str(invoice_id),
                "invoice_payment_status": invoice.payment_status,
                "invoice_total_paid": invoice.total_paid_amount,
                "payments": created_payments
            },
            message=f"{len(created_payments)} payments created successfully",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating multiple payments: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while creating payments: {str(e)}"
        ).model_dump()

@admin_app.get(
    "/invoices/{invoice_id}/payments",
    tags=["Invoice Payments"],
    status_code=200,
    description="Get all payments made for a specific invoice"
)
def get_invoice_payments(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Validate invoice exists
        invoice = db.query(Invoice).filter(
            Invoice.uuid == invoice_id,
            Invoice.is_deleted.is_(False)
        ).first()

        if not invoice:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice not found"
            ).model_dump()

        # Optional: Role check
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to view invoice payments"
            ).model_dump()

        # Get all payments for this invoice
        payments = db.query(InvoicePayment).filter(
            InvoicePayment.invoice_id == invoice_id,
            InvoicePayment.is_deleted.is_(False)
        ).order_by(InvoicePayment.payment_date.desc()).all()

        # Format output
        payment_list = []
        for payment in payments:
            payment_list.append({
                "uuid": str(payment.uuid),
                "amount": payment.amount,
                "payment_date": payment.payment_date.strftime("%Y-%m-%d"),
                "description": payment.description,
                "payment_method": payment.payment_method,
                "reference_number": payment.reference_number,
                "created_at": payment.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return ProjectServiceResponse(
            data={
                "invoice_id": str(invoice_id),
                "invoice_amount": invoice.amount,
                "payment_status": invoice.payment_status,
                "total_paid_amount": invoice.total_paid_amount,
                "remaining_amount": invoice.amount - invoice.total_paid_amount,
                "payments": payment_list
            },
            message="Invoice payments fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_invoice_payments API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching payments: {str(e)}"
        ).model_dump()

# @admin_app.get(
#     "/invoices/{invoice_id}/payments",
#     tags=["Invoice Payments"],
#     description="List all payments for a specific invoice"
# )
# def list_invoice_payments(
#     invoice_id: UUID,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     List all payments for a specific invoice.
#     """
#     try:
#         # Find the invoice
#         invoice = db.query(Invoice).filter(
#             Invoice.uuid == invoice_id,
#             Invoice.is_deleted.is_(False)
#         ).first()

#         if not invoice:
#             return ProjectServiceResponse(
#                 data=None,
#                 status_code=404,
#                 message="Invoice not found"
#             ).model_dump()

#         # Get all payments for this invoice
#         payments = db.query(InvoicePayment).filter(
#             InvoicePayment.invoice_id == invoice_id,
#             InvoicePayment.is_deleted.is_(False)
#         ).order_by(InvoicePayment.payment_date.desc()).all()

#         # Format response
#         payments_list = []
#         for payment in payments:
#             payments_list.append({
#                 "uuid": str(payment.uuid),
#                 "invoice_id": str(payment.invoice_id),
#                 "amount": payment.amount,
#                 "payment_date": payment.payment_date.strftime("%Y-%m-%d"),
#                 "description": payment.description,
#                 "payment_method": payment.payment_method,
#                 "reference_number": payment.reference_number,
#                 "created_at": payment.created_at.strftime("%Y-%m-%d %H:%M:%S")
#             })

#         return ProjectServiceResponse(
#             data={
#                 "invoice_id": str(invoice_id),
#                 "invoice_amount": invoice.amount,
#                 "payment_status": invoice.payment_status,
#                 "total_paid_amount": invoice.total_paid_amount,
#                 "remaining_amount": invoice.amount - invoice.total_paid_amount,
#                 "payments": payments_list
#             },
#             message="Invoice payments fetched successfully",
#             status_code=200
#         ).model_dump()
#     except Exception as e:
#         logger.error(f"Error in list_invoice_payments API: {str(e)}")
#         return ProjectServiceResponse(
#             data=None,
#             status_code=500,
#             message=f"An error occurred while fetching invoice payments: {str(e)}"
#         ).model_dump()
    
@admin_app.delete(
    "/invoices/{invoice_id}/payments/{payment_id}",
    tags=["Invoice Payments"],
    description="Delete a specific payment for an invoice"
)
def delete_invoice_payment(
    invoice_id: UUID,
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete an invoice payment and update invoice totals and status.
    """
    try:
        # Check role
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to delete invoice payments"
            ).model_dump()

        # Get the invoice
        invoice = db.query(Invoice).filter(
            Invoice.uuid == invoice_id,
            Invoice.is_deleted.is_(False)
        ).first()

        if not invoice:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice not found"
            ).model_dump()

        # Get the payment record
        payment = db.query(InvoicePayment).filter(
            InvoicePayment.uuid == payment_id,
            InvoicePayment.invoice_id == invoice_id,
            InvoicePayment.is_deleted.is_(False)
        ).first()

        if not payment:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Invoice payment not found"
            ).model_dump()

        # Soft-delete payment
        payment.is_deleted = True
        invoice.total_paid_amount -= payment.amount

        # Update invoice payment status
        if invoice.total_paid_amount <= 0:
            invoice.total_paid_amount = 0
            invoice.payment_status = "not_paid"
        elif invoice.total_paid_amount >= invoice.amount:
            invoice.payment_status = "fully_paid"
        else:
            invoice.payment_status = "partially_paid"

        # Create audit log
        log_entry = Log(
            uuid=str(uuid4()),
            entity="InvoicePayment",
            action="Delete",
            entity_id=payment.uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data={
                "invoice_id": str(invoice_id),
                "payment_id": str(payment_id),
                "new_invoice_status": invoice.payment_status,
                "total_paid_amount": invoice.total_paid_amount
            },
            message="Invoice payment deleted successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in delete_invoice_payment API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while deleting invoice payment: {str(e)}"
        ).model_dump()

@admin_app.get(
    "/khatabook",
    tags=["Khatabook"],
    description="""
    Get all khatabook entries with optional filtering.

    This endpoint allows admins to view khatabook entries from all users.
    You can filter by amount, date range, item, and user.
    """
)
def get_all_khatabook_entries_admin(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    item_id: Optional[UUID] = Query(None, description="Filter by item ID"),
    person_id: Optional[UUID] = Query(None, description="Filter by person ID"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    start_date: Optional[datetime] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[datetime] = Query(None, description="End date (YYYY-MM-DD)"),
    payment_mode: Optional[str] = Query(None, description="Payment mode"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all khatabook entries with optional filtering.
    Only accessible to admin and super admin users.
    """
    try:
        # Check if user has permission
        if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Only admin and super admin can access all khatabook entries"
            ).model_dump()

        # Base query with all joins
        query = (
            db.query(Khatabook)
            .outerjoin(KhatabookItem, Khatabook.uuid == KhatabookItem.khatabook_id)
            .outerjoin(KhatabookFile, Khatabook.uuid == KhatabookFile.khatabook_id)
            .outerjoin(User, Khatabook.created_by == User.uuid)
            .outerjoin(Person, Khatabook.person_id == Person.uuid)
            .outerjoin(Project, Khatabook.project_id == Project.uuid)
            .filter(Khatabook.is_deleted.is_(False))
            .distinct()
        )

        # Apply filters if provided
        if user_id:
            query = query.filter(Khatabook.created_by == user_id)

        if item_id:
            query = query.filter(KhatabookItem.item_id == item_id)

        if person_id:
            query = query.filter(Khatabook.person_id == person_id)

        if project_id:
            query = query.filter(Khatabook.project_id == project_id)

        if min_amount is not None:
            query = query.filter(Khatabook.amount >= min_amount)

        if max_amount is not None:
            query = query.filter(Khatabook.amount <= max_amount)

        if start_date:
            query = query.filter(Khatabook.expense_date >= start_date)

        if end_date:
            query = query.filter(Khatabook.expense_date <= end_date)

        if payment_mode:
            query = query.filter(Khatabook.payment_mode == payment_mode)

        # Order by most recent first
        query = query.order_by(Khatabook.created_at.desc())

        # Execute query with eager loading of relationships
        entries = (
            query
            .options(
                joinedload(Khatabook.files),
                joinedload(Khatabook.person),
                joinedload(Khatabook.items).joinedload(KhatabookItem.item),
                joinedload(Khatabook.project),
                joinedload(Khatabook.created_by_user)
            )
            .all()
        )

        # Format response
        response_data = []
        for entry in entries:
            # Process files
            file_urls = []
            if entry.files:
                for f in entry.files:
                    filename = os.path.basename(f.file_path)
                    file_url = f"{constants.HOST_URL}/uploads/khatabook_files/{filename}"
                    file_urls.append(file_url)

            # Process items
            items_data = []
            if entry.items:
                for khatabook_item in entry.items:
                    if khatabook_item.item:
                        items_data.append({
                            "uuid": str(khatabook_item.item.uuid),
                            "name": khatabook_item.item.name,
                            "category": khatabook_item.item.category,
                        })
            # Process project info
            project_info = None
            if entry.project:
                project_info = {
                    "uuid": str(entry.project.uuid),
                    "name": entry.project.name
                }

            # Process user info
            user_info = None
            if entry.created_by_user:
                user_info = {
                    "uuid": str(entry.created_by_user.uuid),
                    "name": entry.created_by_user.name,
                    "phone": entry.created_by_user.phone,
                    "role": entry.created_by_user.role
                }

            # Process person info
            person_info = None
            if entry.person:
                person_info = {
                    "uuid": str(entry.person.uuid),
                    "name": entry.person.name,
                    "phone_number": entry.person.phone_number
                }

            # Add entry to response
            response_data.append({
                "uuid": str(entry.uuid),
                "amount": entry.amount,
                "remarks": entry.remarks,
                "balance_after_entry": entry.balance_after_entry,
                "person": person_info,
                "user": user_info,
                "project": project_info,
                "expense_date": entry.expense_date.isoformat() if entry.expense_date else None,
                "created_at": entry.created_at.isoformat(),
                "files": file_urls,
                "items": items_data,
                "is_suspicious": entry.is_suspicious,
                "payment_mode": entry.payment_mode,
                "entry_type": entry.entry_type  # Include entry_type in admin response
            })

        # Calculate totals
        total_amount = sum(entry["amount"] for entry in response_data)

        return ProjectServiceResponse(
            data={
                "total_amount": total_amount,
                "entries_count": len(response_data),
                "entries": response_data
            },
            message="Khatabook entries fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_all_khatabook_entries_admin API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching khatabook entries: {str(e)}"
        ).model_dump()


# @admin_app.get(
#     "/item-analytics",
#     tags=["Analytics"],
#     description="Get item analytics data for all projects (estimation vs current expense)"
# )
# def get_all_item_analytics(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     Get analytics data for all items across all projects.
#     Returns per-project grouped data:
#     - Item name
#     - Estimation (balance added when assigned)
#     - Current expense (sum of transferred payments)
#     - Sorted by estimation descending within each project
#     """
#     try:
#         # Check permissions
#         if current_user.role not in [
#             UserRole.SUPER_ADMIN.value,
#             UserRole.ADMIN.value
#         ]:
#             return AdminPanelResponse(
#                 data=None,
#                 message="Only admin and super admin can access all item analytics",
#                 status_code=403
#             ).model_dump()

#         # Subquery to get latest ProjectItemMap entry per (project, item)
#         subquery = (
#             db.query(
#                 ProjectItemMap.project_id,
#                 ProjectItemMap.item_id,
#                 func.max(ProjectItemMap.id).label('max_id')
#             )
#             .group_by(ProjectItemMap.project_id, ProjectItemMap.item_id)
#             .subquery()
#         )

#         all_items = (
#             db.query(ProjectItemMap, Item, Project)
#             .join(subquery, ProjectItemMap.id == subquery.c.max_id)
#             .join(Item, ProjectItemMap.item_id == Item.uuid)
#             .join(Project, ProjectItemMap.project_id == Project.uuid)
#             .filter(Project.is_deleted.is_(False))
#             .all()
#         )

#         if not all_items:
#             return AdminPanelResponse(
#                 data={"items_analytics": []},
#                 message="No items found in any project",
#                 status_code=200
#             ).model_dump()

#         # Group items per project
#         project_wise_items = defaultdict(list)

#         for project_item, item, project in all_items:
#             estimation = project_item.item_balance or 0.0

#             current_expense = (
#                 db.query(func.sum(Payment.amount))
#                 .join(PaymentItem, Payment.uuid == PaymentItem.payment_id)
#                 .filter(
#                     PaymentItem.item_id == item.uuid,
#                     Payment.project_id == project.uuid,
#                     Payment.status == PaymentStatus.TRANSFERRED.value,
#                     Payment.is_deleted.is_(False),
#                     PaymentItem.is_deleted.is_(False)
#                 )
#                 .scalar() or 0.0
#             )

#             project_wise_items[project.name].append({
#                 "uuid": item.uuid,
#                 "item_name": item.name,
#                 "estimation": estimation,
#                 "current_expense": current_expense
#             })

#         # Sort each project's item list by estimation
#         items_analytics = []
#         for project_name, items in project_wise_items.items():
#             sorted_items = sorted(items, key=lambda x: x["current_expense"], reverse=True)
#             items_analytics.append({
#                 "project_name": project_name,
#                 "items": sorted_items
#             })

#         return AdminPanelResponse(
#             data={"items_analytics": items_analytics},
#             message="Item analytics fetched successfully",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         logger.error(f"Error in get_all_item_analytics API: {str(e)}")
#         return AdminPanelResponse(
#             data=None,
#             message=f"An error occurred while fetching item analytics: {str(e)}",
#             status_code=500
#         ).model_dump()

@admin_app.get(
    "/item-analytics",
    tags=["Analytics"],
    description="Get item analytics data for all projects (estimation vs current expense)"
)
def get_all_item_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analytics data for all items across all projects.
    Returns per-project grouped data:
    - Item name
    - Estimation (balance added when assigned)
    - Current expense (sum of transferred payments)
    - Sorted by expense + estimation descending within each project
    """
    try:
        # Check permissions
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value
        ]:
            return AdminPanelResponse(
                data=None,
                message="Only admin and super admin can access all item analytics",
                status_code=403
            ).model_dump()

        # Subquery to get latest ProjectItemMap entry per (project, item)
        subquery = (
            db.query(
                ProjectItemMap.project_id,
                ProjectItemMap.item_id,
                func.max(ProjectItemMap.id).label('max_id')
            )
            .group_by(ProjectItemMap.project_id, ProjectItemMap.item_id)
            .subquery()
        )

        all_items = (
            db.query(ProjectItemMap, Item, Project)
            .join(subquery, ProjectItemMap.id == subquery.c.max_id)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .join(Project, ProjectItemMap.project_id == Project.uuid)
            .filter(Project.is_deleted.is_(False))
            .all()
        )

        if not all_items:
            return AdminPanelResponse(
                data={"items_analytics": []},
                message="No items found in any project",
                status_code=200
            ).model_dump()

        # Group items per project
        project_wise_items = defaultdict(list)

        for project_item, item, project in all_items:
            estimation = project_item.item_balance or 0.0

            current_expense = (
                db.query(func.sum(Payment.amount))
                .join(PaymentItem, Payment.uuid == PaymentItem.payment_id)
                .filter(
                    PaymentItem.item_id == item.uuid,
                    Payment.project_id == project.uuid,
                    Payment.status == PaymentStatus.TRANSFERRED.value,
                    Payment.is_deleted.is_(False),
                    PaymentItem.is_deleted.is_(False)
                )
                .scalar() or 0.0
            )

            project_wise_items[project.name].append({
                "uuid": item.uuid,
                "item_name": item.name,
                "estimation": estimation,
                "current_expense": current_expense
            })

        # Apply sorting to each project's items
        items_analytics = []
        for project_name, items in project_wise_items.items():
            sorted_items = sorted(
                items,
                key=lambda x: (
                    0 if x["current_expense"] > 0 or x["estimation"] > 0 else 1,
                    -x["current_expense"],
                    -x["estimation"]
                )
            )
            items_analytics.append({
                "project_name": project_name,
                "items": sorted_items
            })

        return AdminPanelResponse(
            data={"items_analytics": items_analytics},
            message="Item analytics fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_all_item_analytics API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message=f"An error occurred while fetching item analytics: {str(e)}",
            status_code=500
        ).model_dump()


# @admin_app.get(
#     "/projects/{project_id}/item-analytics",
#     tags=["Analytics"],
#     description="Get item analytics data for a specific project (estimation vs current expense)"
# )
# def get_project_item_analytics(
#     project_id: UUID,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     Get analytics data for items in a specific project.
#     Returns item name, estimation (balance added when assigned), and current expense (sum of transferred payments).
#     """
#     try:
#         # Check if user has permission
#         if current_user.role not in [
#             UserRole.SUPER_ADMIN.value,
#             UserRole.ADMIN.value,
#             UserRole.PROJECT_MANAGER.value
#         ]:
#             return AdminPanelResponse(
#                 data=None,
#                 message="Only admin, super admin, or project manager can access item analytics",
#                 status_code=403
#             ).model_dump()

#         # Check if project exists
#         project = db.query(Project).filter(Project.uuid == project_id, Project.is_deleted.is_(False)).first()
#         if not project:
#             return AdminPanelResponse(
#                 data=None,
#                 message="Project not found",
#                 status_code=404
#             ).model_dump()

#         # Get all unique items mapped to this project with their balances
#         # Use a subquery to handle potential duplicates by taking the most recent mapping
#         subquery = (
#             db.query(
#                 ProjectItemMap.project_id,
#                 ProjectItemMap.item_id,
#                 func.max(ProjectItemMap.id).label('max_id')
#             )
#             .filter(ProjectItemMap.project_id == project_id)
#             .group_by(ProjectItemMap.project_id, ProjectItemMap.item_id)
#             .subquery()
#         )

#         project_items = (
#             db.query(ProjectItemMap, Item)
#             .join(subquery, ProjectItemMap.id == subquery.c.max_id)
#             .join(Item, ProjectItemMap.item_id == Item.uuid)
#             .all()
#         )

#         if not project_items:
#             # Return empty analytics if no items found
#             return AdminPanelResponse(
#                 data={
#                     "project_id": str(project_id),
#                     "project_name": project.name,
#                     "items_analytics": []
#                 },
#                 message="No items found for this project",
#                 status_code=200
#             ).model_dump()

#         # Prepare items analytics
#         items_analytics = []
#         for project_item, item in project_items:
#             # Get estimation (balance added when assigned)
#             estimation = project_item.item_balance or 0.0

#             # Get current expense (sum of transferred payments for this item)
#             # Use a more direct approach to get the sum of payment amounts
#             current_expense = (
#                 db.query(func.sum(Payment.amount))
#                 .join(PaymentItem, Payment.uuid == PaymentItem.payment_id)
#                 .filter(
#                     PaymentItem.item_id == item.uuid,
#                     Payment.project_id == project_id,
#                     Payment.status == PaymentStatus.TRANSFERRED.value,
#                     Payment.is_deleted.is_(False),
#                     PaymentItem.is_deleted.is_(False)
#                 )
#                 .scalar() or 0.0
#             )

#             items_analytics.append({
#                 "uuid": item.uuid,
#                 "item_name": item.name,
#                 "estimation": estimation,
#                 "current_expense": current_expense
#             })

#         # Prepare response
#         response_data = {
#             "project_id": str(project_id),
#             "project_name": project.name,
#             "items_analytics": items_analytics
#         }

#         return AdminPanelResponse(
#             data=response_data,
#             message="Item analytics fetched successfully",
#             status_code=200
#         ).model_dump()
#     except Exception as e:
#         logger.error(f"Error in get_project_item_analytics API: {str(e)}")
#         return AdminPanelResponse(
#             data=None,
#             message=f"An error occurred while fetching item analytics: {str(e)}",
#             status_code=500
#         ).model_dump()

@admin_app.get(
    "/projects/{project_id}/item-analytics",
    tags=["Analytics"],
    description="Get item analytics data for a specific project (estimation vs current expense)"
)
def get_project_item_analytics(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analytics data for items in a specific project.
    Returns item name, estimation (balance added when assigned), and current expense (sum of transferred payments).
    """
    try:
        # Check if user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            return AdminPanelResponse(
                data=None,
                message="Only admin, super admin, or project manager can access item analytics",
                status_code=403
            ).model_dump()

        # Check if project exists
        project = db.query(Project).filter(Project.uuid == project_id, Project.is_deleted.is_(False)).first()
        if not project:
            return AdminPanelResponse(
                data=None,
                message="Project not found",
                status_code=404
            ).model_dump()

        # Get all unique items mapped to this project with their balances
        subquery = (
            db.query(
                ProjectItemMap.project_id,
                ProjectItemMap.item_id,
                func.max(ProjectItemMap.id).label('max_id')
            )
            .filter(ProjectItemMap.project_id == project_id)
            .group_by(ProjectItemMap.project_id, ProjectItemMap.item_id)
            .subquery()
        )

        project_items = (
            db.query(ProjectItemMap, Item)
            .join(subquery, ProjectItemMap.id == subquery.c.max_id)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .all()
        )

        if not project_items:
            return AdminPanelResponse(
                data={
                    "project_id": str(project_id),
                    "project_name": project.name,
                    "items_analytics": []
                },
                message="No items found for this project",
                status_code=200
            ).model_dump()

        # Prepare items analytics
        items_analytics = []
        for project_item, item in project_items:
            estimation = project_item.item_balance or 0.0

            current_expense = (
                db.query(func.sum(Payment.amount))
                .join(PaymentItem, Payment.uuid == PaymentItem.payment_id)
                .filter(
                    PaymentItem.item_id == item.uuid,
                    Payment.project_id == project_id,
                    Payment.status == PaymentStatus.TRANSFERRED.value,
                    Payment.is_deleted.is_(False),
                    PaymentItem.is_deleted.is_(False)
                )
                .scalar() or 0.0
            )

            items_analytics.append({
                "uuid": item.uuid,
                "item_name": item.name,
                "estimation": estimation,
                "current_expense": current_expense
            })

        # Sort:
        # - first by whether it has any value (non-zero current_expense or estimation)
        # - then by current_expense desc
        # - then by estimation desc
        sorted_items_analytics = sorted(
            items_analytics,
            key=lambda x: (
                0 if x["current_expense"] > 0 or x["estimation"] > 0 else 1,  # 0 = has value, 1 = both zero
                -x["current_expense"],
                -x["estimation"]
            )
        )

        response_data = {
            "project_id": str(project_id),
            "project_name": project.name,
            "items_analytics": sorted_items_analytics
        }

        return AdminPanelResponse(
            data=response_data,
            message="Item analytics fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_project_item_analytics API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message=f"An error occurred while fetching item analytics: {str(e)}",
            status_code=500
        ).model_dump()


@admin_app.get(
    "/projects/{project_id}/payment-analytics",
    tags=["Analytics"],
    description="Get payment analytics data for a specific project (count, amount, percentage by status)"
)
def get_project_payment_analytics(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analytics data for payments in a specific project.
    Returns count, total amount, and percentage of payments by status.
    """
    try:
        # Check if user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            return AdminPanelResponse(
                data=None,
                message="Only admin, super admin, or project manager can access payment analytics",
                status_code=403
            ).model_dump()

        # Check if project exists
        project = db.query(Project).filter(Project.uuid == project_id, Project.is_deleted.is_(False)).first()
        if not project:
            return AdminPanelResponse(
                data=None,
                message="Project not found",
                status_code=404
            ).model_dump()

        # Get all payments for this project
        payments = db.query(Payment).filter(
            Payment.project_id == project_id,
            Payment.is_deleted.is_(False),
        ).all()

        if not payments:
            # Return empty analytics if no payments found
            return AdminPanelResponse(
                data={
                    "project_id": str(project_id),
                    "project_name": project.name,
                    "total_payments": 0,
                    "total_amount": 0.0,
                    "status_analytics": []
                },
                message="No payments found for this project",
                status_code=200
            ).model_dump()

        # Count total payments and calculate total amount
        total_payments = len(payments)
        total_amount = sum(payment.amount for payment in payments)

        # Group payments by status
        status_counts = {}
        status_amounts = {}

        for payment in payments:
            if payment.status not in status_counts:
                status_counts[payment.status] = 0
                status_amounts[payment.status] = 0.0

            status_counts[payment.status] += 1
            status_amounts[payment.status] += payment.amount

        # Calculate percentages and prepare response
        status_analytics = []
        for status in PaymentStatus:
            status_value = status.value
            count = status_counts.get(status_value, 0)
            amount = status_amounts.get(status_value, 0.0)
            percentage = (count / total_payments * 100) if total_payments > 0 else 0.0

            status_analytics.append({
                "status": status_value,
                "count": count,
                "total_amount": amount,
                "percentage": round(percentage, 2)
            })

        # Prepare response
        response_data = {
            "project_id": str(project_id),
            "project_name": project.name,
            "total_payments": total_payments,
            "total_amount": total_amount,
            "status_analytics": status_analytics
        }

        return AdminPanelResponse(
            data=response_data,
            message="Payment analytics fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logger.error(f"Error in get_project_payment_analytics API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message=f"An error occurred while fetching payment analytics: {str(e)}",
            status_code=500
        ).model_dump()


@admin_app.get(
    "/logs",
    tags=["Logs"],
    description="Get all logs of user operations with filtering options"
)
def get_all_logs(
    entity: Optional[str] = Query(None, description="Filter by entity type (e.g., User, Project, Payment)"),
    action: Optional[str] = Query(None, description="Filter by action (e.g., Create, Edit, Delete)"),
    entity_id: Optional[UUID] = Query(None, description="Filter by entity ID"),
    performed_by: Optional[UUID] = Query(None, description="Filter by user who performed the action"),
    start_date: Optional[datetime] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[datetime] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all logs of user operations with filtering options.
    Only admin and super admin can access all logs.
    """
    try:
        # Check if current_user is a dictionary (error response) or a User object
        if isinstance(current_user, dict):
            # If it's a dictionary, it's an error response from get_current_user
            return AdminPanelResponse(
                data=None,
                status_code=current_user.get("status_code", 401),
                message=current_user.get("message", "Authentication error")
            ).model_dump()

        # Check if user has permission
        if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            return AdminPanelResponse(
                data=None,
                status_code=403,
                message="Only admin and super admin can access all logs"
            ).model_dump()

        # Base query
        query = db.query(Log).filter(Log.is_deleted.is_(False))

        # Apply filters
        if entity:
            query = query.filter(Log.entity == entity)

        if action:
            query = query.filter(Log.action == action)

        if entity_id:
            query = query.filter(Log.entity_id == entity_id)

        if performed_by:
            query = query.filter(Log.performed_by == performed_by)

        if start_date:
            query = query.filter(Log.timestamp >= start_date)

        if end_date:
            query = query.filter(Log.timestamp <= end_date)

        # Order by most recent first
        query = query.order_by(Log.timestamp.desc())

        # Execute query
        logs = query.all()

        # Get user information for performed_by
        user_ids = [log.performed_by for log in logs]
        users = db.query(User).filter(User.uuid.in_(user_ids)).all()
        user_map = {str(user.uuid): user.name for user in users}

        # Format response
        logs_list = []
        for log in logs:
            logs_list.append({
                "uuid": str(log.uuid),
                "entity": log.entity,
                "action": log.action,
                "entity_id": str(log.entity_id),
                "performed_by": str(log.performed_by),
                "performer_name": user_map.get(str(log.performed_by), "Unknown"),
                "timestamp": log.timestamp.isoformat()
            })

        return AdminPanelResponse(
            data=logs_list,
            message="Logs fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_all_logs API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching logs: {str(e)}"
        ).model_dump()


@admin_app.get("/items/user-project/{user_id}/{project_id}", tags=["Mappings"], deprecated=True)
def get_user_project_items(
    user_id: UUID,
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            return AdminPanelResponse(
                data=None,
                status_code=403,
                message="Only admin, super admin, or project manager can access user project items"
            ).model_dump()

        # Subquery using select() to avoid SAWarning
        project_items_subq = (
            select(ProjectItemMap.item_id)
            .where(ProjectItemMap.project_id == project_id)
        )

        # JOIN using Item.uuid (UUID match)
        items = (
            db.query(Item)
            .join(UserItemMap, UserItemMap.item_id == Item.uuid)
            .filter(
                UserItemMap.user_id == user_id,
                UserItemMap.item_id.in_(project_items_subq)
            )
            .all()
        )

        return AdminPanelResponse(
            data=[{"uuid": item.uuid, "name": item.name} for item in items],
            status_code=200,
            message="Items assigned to user in project fetched successfully"
        ).model_dump()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@admin_app.post(
    "/project-user-item-map",
    tags=["Mappings"],
    description="""
    Synchronize items mapped to a user under a project.

    This API handles both assignment and unassignment:
    - Items in the list that are not already mapped to the user will be
      assigned
    - Items currently mapped to the user but not in the list will be unassigned

    Request body should be in the format:
    ```json
    {
        "project_id": "uuid",
        "user_id": "uuid",
        "item_ids": ["item_uuid1", "item_uuid2"]
    }
    ```
    """
)
def sync_project_user_item_map(
    payload: ProjectUserItemMapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [
        UserRole.SUPER_ADMIN.value,
        UserRole.ADMIN.value,
        UserRole.PROJECT_MANAGER.value
    ]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Check if user is assigned to the project
    user_assigned = db.query(ProjectUserMap).filter_by(
        project_id=payload.project_id,
        user_id=payload.user_id
    ).first()

    if not user_assigned:
        raise HTTPException(
            status_code=400,
            detail="User is not assigned to the selected project. Please assign the user first."
        )

    # Check which items are actually assigned to this project
    assigned_item_ids = {
        row.item_id for row in db.query(ProjectItemMap.item_id).filter_by(
            project_id=payload.project_id
        ).all()
    }

    invalid_items = [
        str(item_id) for item_id in payload.item_ids
        if item_id not in assigned_item_ids
    ]
    if invalid_items:
        raise HTTPException(
            status_code=400,
            detail=(
                f"The following items are not assigned to the project: "
                f"{', '.join(invalid_items)}"
            )
        )

    # Use sync function to handle both assignment and unassignment
    try:
        result = sync_project_user_item_mappings(
            db=db,
            project_id=payload.project_id,
            user_id=payload.user_id,
            item_ids=payload.item_ids
        )

        return {
            "status_code": 200,
            "message": (
                f"Items synchronized successfully. Added: {result['added']}, "
                f"Removed: {result['removed']}"
            ),
            "data": {
                "project_id": str(payload.project_id),
                "user_id": str(payload.user_id),
                "added_count": result["added"],
                "removed_count": result["removed"],
                "total_mapped": len(result["mappings"]),
                "mappings": [
                    {
                        "uuid": str(m.uuid),
                        "project_id": str(m.project_id),
                        "user_id": str(m.user_id),
                        "item_id": str(m.item_id)
                    } for m in result["mappings"]
                ]
            }
        }
    except Exception as db_error:
        db.rollback()
        logger.error(f"Database error in sync_project_user_item_mappings: {str(db_error)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error while synchronizing items: {str(db_error)}"
        )


# @admin_app.get(
#     "/project-user-item-map/{project_id}/{user_id}",
#     tags=["Mappings"],
#     description="Get all items mapped to a user under a specific project"
# )
# def get_project_user_item_mappings(
#     project_id: UUID,
#     user_id: UUID,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     # 🔐 Role check
#     if current_user.role not in [
#         UserRole.SUPER_ADMIN.value,
#         UserRole.ADMIN.value,
#         UserRole.PROJECT_MANAGER.value
#     ]:
#         raise HTTPException(status_code=403, detail="Unauthorized")

#     # ✅ Check if user is assigned to the project
#     user_assigned = db.query(ProjectUserMap).filter_by(
#         project_id=project_id,
#         user_id=user_id
#     ).first()

#     if not user_assigned:
#         raise HTTPException(
#             status_code=400,
#             detail="User is not assigned to the selected project."
#         )

#     # ✅ Fetch item mappings safely
#     mappings = (
#         db.query(ProjectUserItemMap)
#         .join(Item, ProjectUserItemMap.item_id == Item.uuid)
#         .filter(
#             ProjectUserItemMap.project_id == project_id,
#             ProjectUserItemMap.user_id == user_id
#         )
#         .all()
#     )

#     return {
#         "status_code": 200,
#         "project_id": str(project_id),
#         "user_id": str(user_id),
#         "items": [
#             {
#                 "uuid": m.uuid,
#                 "item_id": m.item_id,
#                 "item_name": m.item.name if m.item else None,
#                 "item_category": m.item.category if m.item else None,
#                 "item_list_tag": m.item.list_tag if m.item else None,
#                 "item_has_additional_info": (
#                     m.item.has_additional_info if m.item else None
#                 )
#             } for m in mappings
#         ],
#         "count": len(mappings)
#     }

@admin_app.get(
    "/project-item-view/{project_id}/{user_id}",
    tags=["Mappings"],
    description="Get items visible to current user under a specific project."
)
def view_project_items_for_user(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.uuid == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Authorized roles who can see all items
    privileged_roles = [
        UserRole.SUPER_ADMIN.value,
        UserRole.ADMIN.value,
        UserRole.PROJECT_MANAGER.value,
        UserRole.ACCOUNTANT.value,
    ]

    if user.role in privileged_roles:
        # Show all items assigned to the project
        project_items = (
            db.query(ProjectItemMap)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .filter(ProjectItemMap.project_id == project_id)
            .all()
        )
        response = {
            "status_code": 200,
            "project_id": str(project_id),
            "user_id": str(user_id),
            "items": [
                {
                    "uuid": m.uuid,
                    "item_id": m.item_id,
                    "item_name": m.item.name if m.item else None,
                    "item_category": m.item.category if m.item else None,
                    "item_list_tag": m.item.list_tag if m.item else None,
                    "item_has_additional_info": m.item.has_additional_info if m.item else None
                }
                for m in project_items
            ],
            "count": len(project_items)
        }
    else:
        # Show only items mapped to this user
        project_items = (
            db.query(ProjectUserItemMap)
            .join(Item, ProjectUserItemMap.item_id == Item.uuid)
            .filter(
                ProjectUserItemMap.project_id == project_id,
                ProjectUserItemMap.user_id == user_id
            )
            .all()
        )
        response = {
            "status_code": 200,
            "project_id": str(project_id),
            "user_id": str(user_id),
            "items": [
                {
                    "uuid": m.uuid,
                    "item_id": m.item_id,
                    "item_name": m.item.name if m.item else None,
                    "item_category": m.item.category if m.item else None,
                    "item_list_tag": m.item.list_tag if m.item else None,
                    "item_has_additional_info": m.item.has_additional_info if m.item else None
                }
                for m in project_items
            ],
            "count": len(project_items)
        }
    return AdminPanelResponse(
        data=response,
        message="Project User Items Fetched Successfully.",
        status_code=200
    ).model_dump()

@admin_app.put(
    "/projects/{project_id}/items",
    tags=["update_items_balance"]
)

def update_project_items(
    project_id: UUID, 
    payload: ProjectItemUpdateRequest, 
    db: Session = Depends(get_db)
):
    updated_items = []
    for item in payload.items:
        mapping = db.query(ProjectItemMap).filter_by(project_id=project_id, item_id=item.item_id).first()
        if not mapping:
            raise HTTPException(
                status_code=404, detail=f"Item {item.item_id} not mapped to project {project_id}")
        
        mapping.item_balance = item.item_balance
        updated_items.append(str(item.item_id))

    db.commit()
    return ProjectItemUpdateResponse(
        status_code=200,
        message="Project Items Updated Successfully.",
    )


# Invoice Analytics API
@admin_app.get(
    "/projects/{project_id}/invoice-analytics",
    tags=["Invoice Analytics"],
    description="""
    Get invoice analytics for a project with is_late flag based on payment dates vs project end date.

    The is_late flag logic:
    - True: Invoice payment is paid after project end date OR not yet paid and project end date has passed
    - False: Invoice payment is paid before project end date
    - None: Not yet paid and project end date has not passed
    """
)
def get_project_invoice_analytics(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get invoice analytics for a project with is_late flag.
    """
    try:
        # Verify user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to view invoice analytics"
            ).model_dump()

        # Find the project
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()

        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Get all invoices for this project
        invoices = db.query(Invoice).filter(
            Invoice.project_id == project_id,
            Invoice.is_deleted.is_(False)
        ).all()

        # Get all POs for this project
        project_pos = db.query(ProjectPO).filter(
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).all()

        # Create PO lookup
        po_lookup = {po.uuid: po for po in project_pos}

        # Process each invoice
        invoice_analytics = []
        from datetime import date
        today = date.today()

        for invoice in invoices:
            # Get PO details
            po_number = None
            po_amount = 0.0
            if invoice.project_po_id and invoice.project_po_id in po_lookup:
                po = po_lookup[invoice.project_po_id]
                po_number = po.po_number
                po_amount = po.amount

            # Get all payments for this invoice to determine latest payment date
            payments = db.query(InvoicePayment).filter(
                InvoicePayment.invoice_id == invoice.uuid,
                InvoicePayment.is_deleted.is_(False)
            ).order_by(InvoicePayment.payment_date.desc()).all()

            # Prepare list of all payments for this invoice
            payment_list = [
                {
                    "amount": payment.amount,
                    "date": payment.payment_date.strftime("%Y-%m-%d") if payment.payment_date else None
                }
                for payment in payments
            ]

            # Determine latest payment date
            latest_payment_date_str = None
            if payments:
                latest_payment_date = max(payment.payment_date for payment in payments)
                latest_payment_date_str = latest_payment_date.strftime("%Y-%m-%d")


            # Determine is_late flag
            is_late = None
            if project.end_date:
                if invoice.payment_status == "fully_paid" and payments:
                    # Check if any payment was made after project end date
                    latest_payment_date = max(payment.payment_date for payment in payments)
                    is_late = latest_payment_date > project.end_date
                elif invoice.payment_status == "partially_paid" and payments:
                    # For partially paid, check if the latest payment was after end date
                    latest_payment_date = max(payment.payment_date for payment in payments)
                    is_late = latest_payment_date > project.end_date
                elif invoice.payment_status == "not_paid":
                    # Not paid and project end date has passed
                    is_late = today > project.end_date
                else:
                    is_late = None

            invoice_analytics.append(InvoiceAnalyticsItem(
                invoice_uuid=invoice.uuid,
                project_name=project.name,
                po_number=po_number,
                po_amount=po_amount,
                invoice_amount=invoice.amount,
                invoice_due_date=invoice.due_date.strftime("%Y-%m-%d"),
                payment_status=invoice.payment_status,
                total_paid_amount=invoice.total_paid_amount,
                payment_date=payment_list,
                is_late=is_late
            ))

        # Create response
        analytics_response = InvoiceAnalyticsResponse(
            project_id=project_id,
            project_name=project.name,
            project_end_date=project.end_date.strftime("%Y-%m-%d") if project.end_date else None,
            invoices=invoice_analytics, 
        )

        return ProjectServiceResponse(
            data=analytics_response.model_dump(),
            message="Invoice analytics fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_project_invoice_analytics API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching invoice analytics: {str(e)}"
        ).model_dump()


@admin_app.get(
        "/project-stats", 
        tags=["Dashboard"], 
        description="Dashboard stats: projects, items, revenue, active users"
    )
def get_dashboard_project_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        from datetime import datetime, timedelta

        # Authorization
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
        ]:
            raise HTTPException(status_code=403, detail="Unauthorized")

        today = datetime.utcnow()
        last_31_days = today - timedelta(days=31)

        # ───── Total Projects ─────
        total_projects = db.query(Project).filter(Project.is_deleted.is_(False)).count()
        recent_projects = db.query(Project).filter(
            Project.is_deleted.is_(False),
            Project.created_at >= last_31_days
        ).count()

        # ───── Total Items ─────
        total_items = db.query(Item).count()
        recent_items = db.query(Item).filter(Item.created_at >= last_31_days).count()

        # ───── Total Revenue ─────
        total_revenue = db.query(func.coalesce(func.sum(InvoicePayment.amount), 0)).filter(
            InvoicePayment.is_deleted.is_(False)
        ).scalar()
        recent_revenue = db.query(func.coalesce(func.sum(InvoicePayment.amount), 0)).filter(
            InvoicePayment.payment_date >= last_31_days,
            InvoicePayment.is_deleted.is_(False)
        ).scalar()

        # Growth %
        growth_percent = None
        if total_revenue and recent_revenue:
            past_revenue = total_revenue - recent_revenue
            if past_revenue > 0:
                growth_percent = round((recent_revenue / past_revenue) * 100, 2)
            else:
                growth_percent = 100.0  # If no past revenue but current exists

        # ───── Active Users ─────
        active_users = db.query(User).filter(User.is_active.is_(True)).count()
        new_users = db.query(User).filter(
            User.is_active.is_(True),
            User.created_at >= last_31_days
        ).count()

        return ProjectServiceResponse(
            data={
                "projects": {
                    "total": total_projects,
                    "last_31_days": recent_projects
                },
                "items": {
                    "total": total_items,
                    "last_31_days": recent_items
                },
                "revenue": {
                    "total": total_revenue,
                    "last_31_days": recent_revenue,
                    "growth_percent": growth_percent
                },
                "active_users": {
                    "total": active_users,
                    "last_31_days": new_users
                }
            },
            message="Dashboard stats fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_dashboard_project_stats API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            message="An error occurred while fetching dashboard stats",
            status_code=500
        ).model_dump()
    


@admin_app.post(
    "/item-groups/{group_uuid}/map-items",
    tags=["admin_panel"],
    status_code=200,
    description=
    "Map items to an item group by UUID.\n\n"
    "### Request Body Format:\n"
    "{\n"
    '  "items": [\n'
    '    {\n'
    '      "item_id": "item1_uuid",\n'
    '      "item_value": 5000\n'
    '    },\n'
    '    {\n'
    '      "item_id": "item2_uuid",\n'
    '      "item_value": 6000\n'
    '    }\n'
    "  ]\n"
    "}\n\n"
    "- `item_id`: UUID of the item you want to map\n"
    "- `item_value`: Numeric value or balance associated with the item\n"
    "- All existing items not in this list will remain unaffected (no unmapping done)"

)
def map_items_to_item_group(
    group_uuid: UUID,
    payload: dict = Body(...,),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:

        # Authorization
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        
        items_data = payload.get("items", [])

        if not items_data:
            return PaymentServiceResponse(
                data=None,
                message="Item list is empty.",
                status_code=400
            ).model_dump()

        group = db.query(ItemGroups).filter(
            ItemGroups.uuid == group_uuid,
            ItemGroups.is_deleted == False
        ).first()

        if not group:
            return PaymentServiceResponse(
                data=None,
                message="Item group not found.",
                status_code=404
            ).model_dump()

        added, updated = 0, 0
        mapped_uuids = []

        for item_entry in items_data:
            item_id_str = item_entry.get("item_id")
            item_value = item_entry.get("item_value")

            try:
                item_uuid = UUID(item_id_str)
            except Exception:
                return PaymentServiceResponse(
                    data=None,
                    message=f"Invalid item_id: {item_id_str}",
                    status_code=400
                ).model_dump()

            item = db.query(Item).filter(Item.uuid == item_uuid).first()
            if not item:
                return PaymentServiceResponse(
                    data=None,
                    message=f"Item not found: {item_id_str}",
                    status_code=404
                ).model_dump()

            mapped_uuids.append(str(item_uuid))

            existing_map = db.query(ItemGroupMap).filter(
                ItemGroupMap.item_group_id == group_uuid,
                ItemGroupMap.item_id == item_uuid
            ).first()

            if existing_map:
                existing_map.item_balance = item_value
                existing_map.is_deleted = False
                updated += 1
            else:
                new_map = ItemGroupMap(
                    uuid=uuid.uuid4(),
                    item_group_id=group_uuid,
                    item_id=item_uuid,
                    item_balance=item_value
                )
                db.add(new_map)
                added += 1

        db.commit()

        return PaymentServiceResponse(
            data={
                "group_uuid": str(group_uuid),
                "total_items": len(items_data),
                "added": added,
                "updated": updated,
                "mapped_item_ids": mapped_uuids
            },
            message="Items mapped to group successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error mapping items to group: {str(e)}",
            status_code=500
        ).model_dump()


# @admin_app.get(
#     "/item-groups/{group_uuid}/items",
#     tags=["Item Groups"],
#     status_code=200,
#     description="Fetch all items mapped to a specific item group UUID."
# )
# def get_items_by_group(
#     group_uuid: UUID,
#     db: Session = Depends(get_db)
# ):
#     try:
#         # 1. Verify the group exists
#         group = db.query(ItemGroups).filter(
#             ItemGroups.uuid == group_uuid,
#             ItemGroups.is_deleted == False
#         ).first()

#         if not group:
#             return PaymentServiceResponse(
#                 data=None,
#                 message="Item group not found.",
#                 status_code=404
#             ).model_dump()

#         # 2. Fetch all non-deleted mappings for this group
#         item_maps = db.query(ItemGroupMap).filter(
#             ItemGroupMap.item_group_id == group_uuid,
#             ItemGroupMap.is_deleted == False
#         ).all()

#         if not item_maps:
#             return PaymentServiceResponse(
#                 data=[],
#                 message="No items mapped to this group.",
#                 status_code=200
#             ).model_dump()

#         item_ids = [mapping.item_id for mapping in item_maps]

#         # 3. Fetch full item details
#         items = db.query(Item).filter(Item.uuid.in_(item_ids)).all()

#         result = []
#         for item in items:
#             # Fetch all groups for each item
#             group_mappings = db.query(ItemGroupMap, ItemGroups).join(ItemGroups, ItemGroupMap.item_group_id == ItemGroups.uuid).filter(
#                 ItemGroupMap.item_id == item.uuid,
#                 ItemGroupMap.is_deleted == False,
#                 ItemGroups.is_deleted == False
#             ).all()

#             associated_groups = [
#                 {
#                     "group_id": str(g.uuid),
#                     "group_name": g.item_groups
#                 }
#                 for _, g in group_mappings
#             ] if group_mappings else None

#             result.append({
#                 "uuid": str(item.uuid),
#                 "name": item.name,
#                 "category": item.category,
#                 "list_tag": item.list_tag,
#                 "has_additional_info": item.has_additional_info,
#                 "created_at": item.created_at,
#                 "associated_groups": associated_groups
#             })

#         return PaymentServiceResponse(
#             data=result,
#             message="Items mapped to this group fetched successfully.",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         return PaymentServiceResponse(
#             data=None,
#             message=f"Error fetching group items: {str(e)}",
#             status_code=500
#         ).model_dump()

@admin_app.get(
    "/item-groups/{group_uuid}/items",
    tags=["admin_panel"],
    status_code=200,
    description="Fetch all items mapped to a specific item group UUID including item value (balance)."
)
def get_items_by_group(
    group_uuid: UUID,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    try:

        # Authorization
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Validate group
        group = db.query(ItemGroups).filter(
            ItemGroups.uuid == group_uuid,
            ItemGroups.is_deleted == False
        ).first()

        if not group:
            return PaymentServiceResponse(
                data=None,
                message="Item group not found.",
                status_code=404
            ).model_dump()

        # Get item mappings
        mappings = db.query(ItemGroupMap).filter(
            ItemGroupMap.item_group_id == group_uuid,
            ItemGroupMap.is_deleted == False
        ).all()

        if not mappings:
            return PaymentServiceResponse(
                data={
                    "group_id": str(group.uuid),
                    "group_name": group.item_groups,
                    "total_items": 0,
                    "items": []
                },
                message="No items mapped to this group.",
                status_code=200
            ).model_dump()

        item_data = []
        for map_obj in mappings:
            item = db.query(Item).filter(Item.uuid == map_obj.item_id).first()
            if item:
                item_data.append({
                    "uuid": str(item.uuid),
                    "name": item.name,
                    "category": item.category,
                    "list_tag": item.list_tag,
                    "has_additional_info": item.has_additional_info,
                    "created_at": item.created_at,
                    "item_value": map_obj.item_balance
                })

        return PaymentServiceResponse(
            data={
                "group_id": str(group.uuid),
                "group_name": group.item_groups,
                "total_items": len(item_data),
                "items": item_data
            },
            message="Items in the group fetched successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        return PaymentServiceResponse(
            data=None,
            message=f"Error fetching group items: {str(e)}",
            status_code=500
        ).model_dump()

@admin_app.delete(
    "/item-groups/{group_uuid}/items/{item_uuid}",
    tags=["admin_panel"],
    status_code=200,
    description="Soft delete (unmap) an item from a specific item group by marking the mapping as deleted."
)
def unmap_item_from_group(
    group_uuid: UUID,
    item_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:

        # Authorization
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Check mapping exists
        mapping = db.query(ItemGroupMap).filter(
            ItemGroupMap.item_group_id == group_uuid,
            ItemGroupMap.item_id == item_uuid,
            ItemGroupMap.is_deleted == False
        ).first()

        if not mapping:
            return PaymentServiceResponse(
                data=None,
                message="Mapping not found or already deleted.",
                status_code=404
            ).model_dump()

        # Perform soft delete
        mapping.is_deleted = True
        db.commit()

        return PaymentServiceResponse(
            data={
                "group_id": str(group_uuid),
                "item_id": str(item_uuid)
            },
            message="Item successfully unmapped from group.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error unmapping item from group: {str(e)}",
            status_code=500
        ).model_dump()

@admin_app.post(
    "/salary",
    tags=["Salary"],
    status_code=201,
)
def create_salary(
    payload: SalaryCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Authorization
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value
        ]:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Validate user and project existence
        user = db.query(User).filter(User.uuid == payload.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        project = db.query(Project).filter(Project.uuid == payload.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
         # Prevent duplicate entry
        exists = db.query(Salary).filter(
            Salary.user_id == payload.user_id,
            Salary.project_id == payload.project_id,
            Salary.month == payload.month,
            Salary.is_deleted == False
        ).first()
        if exists:
            raise HTTPException(status_code=409, detail="Salary already exists for this user and month")
        
        # Create new salary record
        salary = Salary(
            uuid=uuid4(),
            user_id=payload.user_id,
            project_id=payload.project_id,
            month=payload.month,
            amount=payload.amount,
            created_by=current_user.uuid
        )
        db.add(salary)
        db.commit()
        db.refresh(salary)

        return ProjectServiceResponse(
            data=SalaryResponse(
                uuid=salary.uuid,
                user_id=salary.user_id,
                project_id=salary.project_id,
                month=salary.month,
                amount=salary.amount
            ),
            message="Salary data recorded successfully.",
            status_code=201
        )
    except Exception as e:
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            message=f"Failed to create salary: {str(e)}",
            status_code=500
        ).model_dump()

@admin_app.put(
    "/salary/{salary_uuid}",
    tags=["Salary"],
    status_code=200,
    description="Update an existing salary record by UUID."
)
def update_salary(
    salary_id: UUID,
    payload: SalaryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try : 
        # Verify user role
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to update invoice status"
            ).model_dump()
        
        # Fetch the salary record
        salary = db.query(Salary).filter(
            Salary.uuid == salary_id,
            Salary.is_deleted == False
        ).first()

        if not salary:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Salary record not found"
            ).model_dump()
        
        # Update fields
        salary.user_id = payload.user_id
        salary.project_id = payload.project_id
        salary.amount = payload.amount
        salary.month = payload.month

        db.commit()

        return {
            "data": None,
            "message": "Salary Data Updated Successfully.",
            "status_code": 201,
        }

    except Exception as e:
        db.rollback()
        return {
            "data": None,
            "message": f"Error updating salary: {str(e)}",
            "status_code": 500,
        }


@admin_app.get(
    "/salary",
    tags=["Salary"],
    description="Get all salary records with optional filters (user, project, month, amount).",
)
def get_all_salary(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    month: Optional[str] = Query(None, description="Filter by month name e.g. 'June 2025'"),
    amount: Optional[float] = Query(None, description="Filter by exact salary amount"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Role validation
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Build base query with joins
        query = (
            db.query(
                Salary.uuid,
                Salary.user_id,
                User.name.label("user_name"),
                Salary.project_id,
                Project.name.label("project_name"),
                Salary.amount,
                Salary.month
            )
            .join(User, Salary.user_id == User.uuid)
            .join(Project, Salary.project_id == Project.uuid)
            .filter(Salary.is_deleted == False)
        )

        # Apply filters
        if user_id:
            query = query.filter(Salary.user_id == user_id)
        if project_id:
            query = query.filter(Salary.project_id == project_id)
        if month:
            query = query.filter(Salary.month == month)
        if amount is not None:
            query = query.filter(Salary.amount == amount)

        result = query.all()

        # Format response
        data = []
        for row in result:
            data.append({
                "uuid": str(row.uuid),
                "user_id": str(row.user_id),
                "user_name": row.user_name,
                "project_id": str(row.project_id),
                "project_name": row.project_name,
                "amount": row.amount,
                "month": row.month
            })

        return {
            "data": data,
            "message": "Salary Records Fetched Successfully.",
            "status_code": 200
        }

    except Exception as e:
        return {
            "data": None,
            "message": f"Error fetching salary records: {str(e)}",
            "status_code": 500
        }

@admin_app.delete(
    "/salary/{salary_id}",
    tags=["Salary"],
    description="Soft delete a salary record by ID.",
)
def delete_salary_record(
    salary_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # 🛡️ Role-based access control
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
        ]:
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # 🔍 Fetch salary record
        salary = db.query(Salary).filter(Salary.uuid == salary_id, Salary.is_deleted == False).first()
        if not salary:
            raise HTTPException(status_code=404, detail="Salary record not found.")

        # 🗑️ Soft delete
        salary.is_deleted = True
        db.commit()

        return {
            "data": None,
            "message": "Salary Record Deleted Successfully.",
            "status_code": 200,
        }

    except Exception as e:
        db.rollback()
        return {
            "data": None,
            "message": f"Error deleting salary: {str(e)}",
            "status_code": 500,
        }

@admin_app.post(
    "/{person_uuid}/upgrade-to-user",
    status_code=201,
    tags=["Person"],
    description="Upgrade an existing person to a user (creates a User and links to person)."
)
def upgrade_person_to_user(
    person_uuid: UUID,
    payload: PersonToUserCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Optional: Only allow admin/superadmin
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(status_code=403, detail="Only admin/superadmin allowed.")

    # Fetch person
    person = db.query(Person).filter(Person.uuid == person_uuid, Person.is_deleted.is_(False)).first()

    if not person:
        raise HTTPException(status_code=404, detail="Person not found.")
    
    # Prevent upgrading secondary accounts to user
    if getattr(person, "is_secondary_account", False) or getattr(person, "parent_id", None) is not None:
        raise HTTPException(status_code=400, detail="Cannot upgrade a secondary account person to user.")

    # Check if person already has user
    if person.user_id:
        raise HTTPException(status_code=400, detail="This person is already linked to a user.")

    # Check phone/email duplicate in User
    existing_user = db.query(User).filter(User.phone == payload.phone, User.is_deleted.is_(False)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="A user with this phone already exists.")

    # Hash the password
    hashed_password = get_password_hash(payload.password)

    # Create User
    new_user = User(
        name=payload.name,
        phone=payload.phone,
        password_hash=hashed_password,
        role=payload.role,
        is_active=True,
        is_deleted=False
    )
    db.add(new_user)
    db.flush()  # To get new_user.uuid

    # Link person to user
    person.user_id = new_user.uuid
    db.commit()
    db.refresh(person)
    db.refresh(new_user)

    return {
        "status": "success",
        "message": "Person upgraded to User successfully.",
        "person": {
            "uuid": str(person.uuid),
            "name": person.name,
            "user_id": str(person.user_id),
            "account_number" : str(person.account_number),
            "ifsc_code" : str(person.ifsc_code)
        },
        "user": {
            "uuid": str(new_user.uuid),
            "name": new_user.name,
            "phone": new_user.phone,
            "role": new_user.role
        }
    }
import os
from fastapi import FastAPI, Body
from fastapi_sqlalchemy import DBSessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from src.app.database.database import settings
from src.app.services.auth_service import get_current_user
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
from src.app.schemas.project_service_schemas import (
    ProjectServiceResponse,
    InvoiceCreateRequest,
    InvoiceUpdateRequest,
    InvoiceStatusUpdateRequest,
    InvoicePaymentCreateRequest,
    InvoicePaymentResponse,
    InvoiceAnalyticsResponse,
    InvoiceAnalyticsItem
)
from src.app.schemas.payment_service_schemas import PaymentStatus
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
    InvoicePayment
)
from sqlalchemy.orm import Session, joinedload
from src.app.schemas import constants
from src.app.admin_panel.services import get_default_config_service
from src.app.database.database import get_db
import logging
from src.app.admin_panel.schemas import (
    AdminPanelResponse,
    DefaultConfigCreate,
    DefaultConfigUpdate,
    ProjectUserItemMapCreate,
)
from fastapi import HTTPException
from sqlalchemy import select


logging.basicConfig(level=logging.INFO)

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
        logging.error(f"Error in get_default_config API: {str(e)}")
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
        logging.error(f"Error in create_default_config API: {str(e)}")
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
        logging.error(f"Error in update_default_config API: {str(e)}")
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
            logging.error(f"Database error in create_project_user_mapping: {str(db_error)}")
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
        logging.error(f"Error in map_user_to_project API: {str(e)}")
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
            logging.error(f"Database error in map_multiple_users_to_project: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping users to project: {str(db_error)}"
            ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in map_multiple_users_to_project API: {str(e)}")
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
            logging.error(f"Database error in create_project_item_mapping: {str(db_error)}")
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
        logging.error(f"Error in map_item_to_project API: {str(e)}")
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
            logging.error(f"Database error in map_multiple_items_to_project: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping items to project: {str(db_error)}"
            ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in map_multiple_items_to_project API: {str(e)}")
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
            logging.error(f"Database error in create_user_item_mapping: {str(db_error)}")
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
        logging.error(f"Error in map_item_to_user API: {str(e)}")
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
            logging.error(f"Database error in map_multiple_items_to_user: {str(db_error)}")
            return ProjectServiceResponse(
                data=None,
                status_code=500,
                message=f"Database error while mapping items to user: {str(db_error)}"
            ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in map_multiple_items_to_user API: {str(e)}")
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
        logging.error(f"Error in remove_item_from_project API: {str(e)}")
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
        logging.error(f"Error in remove_user_from_project API: {str(e)}")
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
        logging.error(f"Error in remove_item_from_user API: {str(e)}")
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
        logging.error(f"Error in get_user_items API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching user items"
        ).model_dump()


def get_project_items(db: Session, project_id: UUID, current_user: User = None):
    try:
        # Query ProjectItemMap joined with Item to get item UUID and name
        project_items = (
            db.query(ProjectItemMap, Item)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .filter(ProjectItemMap.project_id == project_id)
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
        logging.error(f"Error in get_project_items function: {str(e)}")
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
        project_items = (
            db.query(ProjectItemMap, Item)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .filter(ProjectItemMap.project_id == project_id)
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

        return ProjectServiceResponse(
            data=items_list,
            message="Project items fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in get_project_items_list API: {str(e)}")
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
        logging.error(f"Error in get_project_users API: {str(e)}")
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
            po_balance = project.po_balance if project.po_balance else 0

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
                "po_balance": po_balance,
                "estimated_balance": estimated_balance,
                "actual_balance": actual_balance,
                "po_document_path": project.po_document_path
            })
        return ProjectServiceResponse(
            data=project_response,
            message="User projects fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in get_user_projects API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching user projects"
        ).model_dump()

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

        user = db.query(User).filter(User.uuid == user_id).first()
        if not user:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Get all projects mapped to this user
        project_mappings = (
            db.query(Project, ProjectUserItemMap)
            .join(ProjectUserItemMap, Project.uuid == ProjectUserMap.project_id)
            .filter(ProjectUserMap.user_id == user_id)
            .all()
        )

        projects_list = []
        for project, mapping in project_mappings:
            # Get items with their balances for each project
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
                "item_balance": item_mapping.item_balance
            } for item, item_mapping in project_items]

            # Get total balance (for backward compatibility)
            # total_balance = (
            #     db.query(func.sum(ProjectBalance.adjustment))
            #     .filter(ProjectBalance.project_id == project.uuid)
            #     .scalar()
            # ) or 0.0

            # Get PO balance
            po_balance = project.po_balance if project.po_balance else 0

            # Get estimated balance
            estimated_balance = project.estimated_balance if project.estimated_balance else 0

            # Get actual balance
            actual_balance = project.actual_balance if project.actual_balance else 0

            projects_list.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "po_balance": po_balance,
                "estimated_balance": estimated_balance,
                "actual_balance": actual_balance,
                "po_document_path": project.po_document_path,
                "items": items_list
            })

        user_details = {
            "uuid": str(user.uuid),
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "projects": projects_list
        }

        return ProjectServiceResponse(
            data=user_details,
            message="User details fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logging.error(f"Error in get_user_details API: {str(e)}")
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
        logging.error(f"Error in get_user_project_items API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching user project items"
        ).model_dump()


# Invoice APIs
@admin_app.post(
    "/invoices",
    tags=["Invoices"],
    status_code=201,
    description="""
    Upload a new invoice with optional file attachment.

    Request body should be sent as a form with 'request' field containing a JSON string with the following structure:
    ```json
    {
        "project_id": "123e4567-e89b-12d3-a456-426614174000",
        "project_po_id": "456e7890-e89b-12d3-a456-426614174001",
        "client_name": "ABC Company",
        "invoice_item": "Construction Materials",
        "amount": 500.0,
        "description": "Invoice for materials",
        "due_date": "2025-06-15"
    }
    ```

    The invoice file can be uploaded as a file in the 'invoice_file' field.
    """
)
def upload_invoice(
    request: str = Form(..., description="JSON string containing invoice details (project_id, amount, description)"),
    invoice_file: Optional[UploadFile] = File(None, description="Invoice file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a new invoice with optional file attachment.
    """
    try:
        # Parse the request data from form
        import json
        request_data = json.loads(request)
        invoice_request = InvoiceCreateRequest(**request_data)

        # Verify project exists
        project = db.query(Project).filter(
            Project.uuid == invoice_request.project_id,
            Project.is_deleted.is_(False)
        ).first()

        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Verify PO exists if provided
        project_po = None
        if invoice_request.project_po_id:
            project_po = db.query(ProjectPO).filter(
                ProjectPO.uuid == invoice_request.project_po_id,
                ProjectPO.project_id == invoice_request.project_id,
                ProjectPO.is_deleted.is_(False)
            ).first()

            if not project_po:
                return ProjectServiceResponse(
                    data=None,
                    status_code=404,
                    message="Project PO not found"
                ).model_dump()

        # Handle invoice file upload if provided
        file_path = None
        if invoice_file:
            upload_dir = "uploads/invoices"
            os.makedirs(upload_dir, exist_ok=True)

            # Create a unique filename to avoid collisions
            file_ext = os.path.splitext(invoice_file.filename)[1]
            unique_filename = f"Invoice_{str(uuid4())}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)

            # Save the file
            with open(file_path, "wb") as buffer:
                buffer.write(invoice_file.file.read())

        # Parse due_date string to datetime
        from datetime import datetime
        try:
            due_date = datetime.strptime(invoice_request.due_date, "%Y-%m-%d")
        except ValueError:
            try:
                due_date = datetime.strptime(invoice_request.due_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message="Invalid due_date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
                ).model_dump()

        # Create new invoice
        new_invoice = Invoice(
            project_id=invoice_request.project_id,
            project_po_id=invoice_request.project_po_id,
            client_name=invoice_request.client_name,
            invoice_item=invoice_request.invoice_item,
            amount=invoice_request.amount,
            description=invoice_request.description,
            due_date=due_date,
            file_path=file_path,
            status="uploaded",
            payment_status="not_paid",
            total_paid_amount=0.0,
            created_by=current_user.uuid
        )
        db.add(new_invoice)
        db.flush()

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Invoice",
            action="Create",
            entity_id=new_invoice.uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(new_invoice)

        return ProjectServiceResponse(
            data={
                "uuid": str(new_invoice.uuid),
                "project_id": str(new_invoice.project_id),
                "client_name": new_invoice.client_name,
                "invoice_item": new_invoice.invoice_item,
                "amount": new_invoice.amount,
                "description": new_invoice.description,
                "due_date": new_invoice.due_date.strftime("%Y-%m-%d"),
                "file_path": constants.HOST_URL + "/" + new_invoice.file_path if new_invoice.file_path else None,
                "status": new_invoice.status,
                "created_at": new_invoice.created_at.strftime("%Y-%m-%d %H:%M:%S")
            },
            message="Invoice uploaded successfully",
            status_code=201
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in upload_invoice API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while uploading invoice: {str(e)}"
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
        logging.error(f"Error in update_invoice_status API: {str(e)}")
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

        # Format response
        invoice_list = []
        for invoice in invoices:
            invoice_list.append({
                "uuid": str(invoice.uuid),
                "project_id": str(invoice.project_id),
                "client_name": invoice.client_name,
                "invoice_item": invoice.invoice_item,
                "amount": invoice.amount,
                "description": invoice.description,
                "due_date": invoice.due_date.strftime("%Y-%m-%d"),
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
        logging.error(f"Error in list_invoices API: {str(e)}")
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
                "invoice_item": invoice.invoice_item,
                "amount": invoice.amount,
                "description": invoice.description,
                "due_date": invoice.due_date.strftime("%Y-%m-%d"),
                "file_path": constants.HOST_URL + "/" + invoice.file_path if invoice.file_path else None,
                "status": invoice.status,
                "created_at": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "created_by": str(invoice.created_by)
            },
            message="Invoice fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_invoice API: {str(e)}")
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

    Request body should contain the fields to update:
    ```json
    {
        "client_name": "Updated Company Name",
        "invoice_item": "Updated Item",
        "amount": 600.0,
        "description": "Updated description",
        "due_date": "2025-07-15"
    }
    ```

    All fields are optional - only provided fields will be updated.
    """
)
def update_invoice(
    invoice_id: UUID,
    update_request: InvoiceUpdateRequest = Body(
        ...,
        description="Invoice update information"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update invoice information.
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
                message="Not authorized to update invoice"
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

        # Update fields if provided
        if update_request.client_name is not None:
            invoice.client_name = update_request.client_name

        if update_request.invoice_item is not None:
            invoice.invoice_item = update_request.invoice_item

        if update_request.amount is not None:
            invoice.amount = update_request.amount

        if update_request.description is not None:
            invoice.description = update_request.description

        if update_request.due_date is not None:
            # Parse due_date string to datetime
            from datetime import datetime
            try:
                due_date = datetime.strptime(update_request.due_date, "%Y-%m-%d")
            except ValueError:
                try:
                    due_date = datetime.strptime(update_request.due_date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message="Invalid due_date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
                    ).model_dump()
            invoice.due_date = due_date

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Invoice",
            action="Update",
            entity_id=invoice_id,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(invoice)

        return ProjectServiceResponse(
            data={
                "uuid": str(invoice.uuid),
                "project_id": str(invoice.project_id),
                "client_name": invoice.client_name,
                "invoice_item": invoice.invoice_item,
                "amount": invoice.amount,
                "description": invoice.description,
                "due_date": invoice.due_date.strftime("%Y-%m-%d"),
                "file_path": constants.HOST_URL + "/" + invoice.file_path if invoice.file_path else None,
                "status": invoice.status,
                "created_at": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S")
            },
            message="Invoice updated successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in update_invoice API: {str(e)}")
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
        logging.error(f"Error in delete_invoice API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while deleting invoice: {str(e)}"
        ).model_dump()


# Invoice Payment APIs
@admin_app.post(
    "/invoices/{invoice_id}/payments",
    tags=["Invoice Payments"],
    status_code=201,
    description="""
    Create a payment record for an invoice.

    Request body should contain:
    ```json
    {
        "amount": 250.0,
        "payment_date": "2025-06-15",
        "description": "Partial payment",
        "payment_method": "bank",
        "reference_number": "TXN123456"
    }
    ```
    """
)
def create_invoice_payment(
    invoice_id: UUID,
    payment_request: InvoicePaymentCreateRequest = Body(
        ...,
        description="Payment information",
        example={
            "amount": 250.0,
            "payment_date": "2025-06-15",
            "description": "Partial payment",
            "payment_method": "bank",
            "reference_number": "TXN123456"
        }
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a payment record for an invoice.
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
                message="Not authorized to create invoice payments"
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

        # Parse payment date
        from datetime import datetime
        try:
            payment_date = datetime.strptime(payment_request.payment_date, "%Y-%m-%d").date()
        except ValueError:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Invalid payment_date format. Use YYYY-MM-DD"
            ).model_dump()

        # Create new payment record
        new_payment = InvoicePayment(
            invoice_id=invoice_id,
            amount=payment_request.amount,
            payment_date=payment_date,
            description=payment_request.description,
            payment_method=payment_request.payment_method,
            reference_number=payment_request.reference_number,
            created_by=current_user.uuid
        )
        db.add(new_payment)
        db.flush()

        # Update invoice payment status and total paid amount
        invoice.total_paid_amount += payment_request.amount

        # Determine payment status
        if invoice.total_paid_amount >= invoice.amount:
            invoice.payment_status = "fully_paid"
        elif invoice.total_paid_amount > 0:
            invoice.payment_status = "partially_paid"
        else:
            invoice.payment_status = "not_paid"

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="InvoicePayment",
            action="Create",
            entity_id=new_payment.uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(new_payment)

        return ProjectServiceResponse(
            data={
                "uuid": str(new_payment.uuid),
                "invoice_id": str(new_payment.invoice_id),
                "amount": new_payment.amount,
                "payment_date": new_payment.payment_date.strftime("%Y-%m-%d"),
                "description": new_payment.description,
                "payment_method": new_payment.payment_method,
                "reference_number": new_payment.reference_number,
                "created_at": new_payment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "invoice_payment_status": invoice.payment_status,
                "invoice_total_paid": invoice.total_paid_amount
            },
            message="Invoice payment created successfully",
            status_code=201
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in create_invoice_payment API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while creating invoice payment: {str(e)}"
        ).model_dump()


@admin_app.get(
    "/invoices/{invoice_id}/payments",
    tags=["Invoice Payments"],
    description="List all payments for a specific invoice"
)
def list_invoice_payments(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all payments for a specific invoice.
    """
    try:
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

        # Get all payments for this invoice
        payments = db.query(InvoicePayment).filter(
            InvoicePayment.invoice_id == invoice_id,
            InvoicePayment.is_deleted.is_(False)
        ).order_by(InvoicePayment.payment_date.desc()).all()

        # Format response
        payments_list = []
        for payment in payments:
            payments_list.append({
                "uuid": str(payment.uuid),
                "invoice_id": str(payment.invoice_id),
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
                "payments": payments_list
            },
            message="Invoice payments fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in list_invoice_payments API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching invoice payments: {str(e)}"
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
        logging.error(f"Error in get_all_khatabook_entries_admin API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching khatabook entries: {str(e)}"
        ).model_dump()


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
    Returns item name, estimation (balance added when assigned), and current expense (sum of transferred payments).
    """
    try:
        # Check if user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value
        ]:
            return AdminPanelResponse(
                data=None,
                message="Only admin and super admin can access all item analytics",
                status_code=403
            ).model_dump()

        # Get all items with their balances from all projects
        all_items = (
            db.query(ProjectItemMap, Item, Project)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .join(Project, ProjectItemMap.project_id == Project.uuid)
            .filter(Project.is_deleted.is_(False))
            .all()
        )

        if not all_items:
            # Return empty analytics if no items found
            return AdminPanelResponse(
                data={
                    "items_analytics": []
                },
                message="No items found in any project",
                status_code=200
            ).model_dump()

        # Prepare items analytics
        items_analytics = []
        for project_item, item, project in all_items:
            # Get estimation (balance added when assigned)
            estimation = project_item.item_balance or 0.0

            # Get current expense (sum of transferred payments for this item)
            # First, get all payment items for this item in this project
            payment_items = (
                db.query(PaymentItem)
                .join(Payment, PaymentItem.payment_id == Payment.uuid)
                .filter(
                    PaymentItem.item_id == item.uuid,
                    Payment.project_id == project.uuid,
                    Payment.status == PaymentStatus.TRANSFERRED.value,
                    Payment.is_deleted.is_(False),
                    PaymentItem.is_deleted.is_(False)
                )
                .all()
            )

            # Get the payment amounts
            payment_ids = [pi.payment_id for pi in payment_items]
            current_expense = 0.0
            if payment_ids:
                current_expense = (
                    db.query(func.sum(Payment.amount))
                    .filter(
                        Payment.uuid.in_(payment_ids),
                        Payment.status == PaymentStatus.TRANSFERRED.value,
                        Payment.is_deleted.is_(False)
                    )
                    .scalar() or 0.0
                )

            items_analytics.append({
                "item_name": item.name,
                "project_name": project.name,
                "estimation": estimation,
                "current_expense": current_expense
            })

        # Prepare response
        response_data = {
            "items_analytics": items_analytics
        }

        return AdminPanelResponse(
            data=response_data,
            message="Item analytics fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_all_item_analytics API: {str(e)}")
        return AdminPanelResponse(
            data=None,
            message=f"An error occurred while fetching item analytics: {str(e)}",
            status_code=500
        ).model_dump()


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

        # Get all items mapped to this project with their balances
        project_items = (
            db.query(ProjectItemMap, Item)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .filter(ProjectItemMap.project_id == project_id)
            .all()
        )

        if not project_items:
            # Return empty analytics if no items found
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
            # Get estimation (balance added when assigned)
            estimation = project_item.item_balance or 0.0

            # Get current expense (sum of transferred payments for this item)
            # First, get all payment items for this item in this project
            payment_items = (
                db.query(PaymentItem)
                .join(Payment, PaymentItem.payment_id == Payment.uuid)
                .filter(
                    PaymentItem.item_id == item.uuid,
                    Payment.project_id == project_id,
                    Payment.status == PaymentStatus.TRANSFERRED.value,
                    Payment.is_deleted.is_(False),
                    PaymentItem.is_deleted.is_(False)
                )
                .all()
            )

            # Get the payment amounts
            payment_ids = [pi.payment_id for pi in payment_items]
            current_expense = 0.0
            if payment_ids:
                current_expense = (
                    db.query(func.sum(Payment.amount))
                    .filter(
                        Payment.uuid.in_(payment_ids),
                        Payment.status == PaymentStatus.TRANSFERRED.value,
                        Payment.is_deleted.is_(False)
                    )
                    .scalar() or 0.0
                )

            items_analytics.append({
                "item_name": item.name,
                "estimation": estimation,
                "current_expense": current_expense
            })

        # Prepare response
        response_data = {
            "project_id": str(project_id),
            "project_name": project.name,
            "items_analytics": items_analytics
        }

        return AdminPanelResponse(
            data=response_data,
            message="Item analytics fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_project_item_analytics API: {str(e)}")
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
            Payment.is_deleted.is_(False)
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
        logging.error(f"Error in get_project_payment_analytics API: {str(e)}")
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
        logging.error(f"Error in get_all_logs API: {str(e)}")
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
        logging.error(f"Database error in sync_project_user_item_mappings: {str(db_error)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error while synchronizing items: {str(db_error)}"
        )


@admin_app.get(
    "/project-user-item-map/{project_id}/{user_id}",
    tags=["Mappings"],
    description="Get all items mapped to a user under a specific project"
)
def get_project_user_item_mappings(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 🔐 Role check
    if current_user.role not in [
        UserRole.SUPER_ADMIN.value,
        UserRole.ADMIN.value,
        UserRole.PROJECT_MANAGER.value
    ]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # ✅ Check if user is assigned to the project
    user_assigned = db.query(ProjectUserMap).filter_by(
        project_id=project_id,
        user_id=user_id
    ).first()

    if not user_assigned:
        raise HTTPException(
            status_code=400,
            detail="User is not assigned to the selected project."
        )

    # ✅ Fetch item mappings safely
    mappings = (
        db.query(ProjectUserItemMap)
        .join(Item, ProjectUserItemMap.item_id == Item.uuid)
        .filter(
            ProjectUserItemMap.project_id == project_id,
            ProjectUserItemMap.user_id == user_id
        )
        .all()
    )

    return {
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
                "item_has_additional_info": (
                    m.item.has_additional_info if m.item else None
                )
            } for m in mappings
        ],
        "count": len(mappings)
    }


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

            # Get latest payment date for this invoice
            latest_payment = db.query(InvoicePayment).filter(
                InvoicePayment.invoice_id == invoice.uuid,
                InvoicePayment.is_deleted.is_(False)
            ).order_by(InvoicePayment.payment_date.desc()).first()

            # Determine is_late flag
            is_late = None
            if project.end_date:
                if invoice.payment_status == "fully_paid" and latest_payment:
                    # Paid - check if payment was after project end date
                    is_late = latest_payment.payment_date > project.end_date
                elif invoice.payment_status in ["not_paid", "partially_paid"]:
                    # Not fully paid - check if project end date has passed
                    if today > project.end_date:
                        is_late = True
                    else:
                        is_late = None  # Not yet late

            invoice_analytics.append(InvoiceAnalyticsItem(
                invoice_uuid=invoice.uuid,
                project_name=project.name,
                po_number=po_number,
                po_amount=po_amount,
                invoice_amount=invoice.amount,
                invoice_due_date=invoice.due_date.strftime("%Y-%m-%d"),
                payment_status=invoice.payment_status,
                total_paid_amount=invoice.total_paid_amount,
                is_late=is_late
            ))

        # Create response
        analytics_response = InvoiceAnalyticsResponse(
            project_id=project_id,
            project_name=project.name,
            project_end_date=project.end_date.strftime("%Y-%m-%d") if project.end_date else None,
            invoices=invoice_analytics
        )

        return ProjectServiceResponse(
            data=analytics_response.model_dump(),
            message="Invoice analytics fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in get_project_invoice_analytics API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching invoice analytics: {str(e)}"
        ).model_dump()
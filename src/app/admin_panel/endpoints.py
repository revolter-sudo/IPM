import os
import traceback
from fastapi import FastAPI, Body, HTTPException
from fastapi_sqlalchemy import DBSessionMiddleware
from src.app.database.database import settings
from src.app.services.auth_service import get_current_user
from src.app.schemas.auth_service_schamas import UserRole
from src.app.admin_panel.services import create_project_user_mapping
from src.app.schemas.project_service_schemas import (
    ProjectServiceResponse,
    InvoiceCreateRequest,
    InvoiceResponse,
    InvoiceStatusUpdateRequest
)
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import and_, func
from fastapi import (
    APIRouter,
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
    ProjectBalance,
    User,
    BalanceDetail,
    Payment,
    ProjectUserMap,
    Item,
    ProjectItemMap,
    Invoice,
    UserItemMap,
    Khatabook,
    KhatabookItem,
    KhatabookFile,
    Person
)
from sqlalchemy.orm import Session, joinedload
from src.app.schemas import constants
from src.app.admin_panel.services import get_default_config_service, create_project_item_mapping, create_user_item_mapping
from src.app.database.database import get_db, SessionLocal
import logging
from src.app.admin_panel.schemas import AdminPanelResponse
logging.basicConfig(level=logging.INFO)

admin_app = FastAPI(
    title="Admin API",
    docs_url="/docs",          # docs within this sub-app will be at /admin/docs
    openapi_url="/openapi.json"
)

# If you need DB access in the admin sub-app, add DBSessionMiddleware again:
admin_app.add_middleware(DBSessionMiddleware, db_url=settings.DATABASE_URL)


# @admin_app.post(
#     "/default-config",
#     tags=['Default Config'],
#     status_code=201
# )
# def create_default_config

@admin_app.get(
    "/default-config",
    tags=['Default Config'],
    status_code=200,
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
    "/project_mapping/{user_id}/{project_id}",
    tags=["admin_panel"]
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
    "/item_mapping/{item_id}/{project_id}",
    tags=["admin_panel"]
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
    "/user_item_mapping/{user_id}/{item_id}",
    tags=["admin_panel"]
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


@admin_app.get(
    "/user/{user_id}/items",
    tags=["admin_panel"]
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


def get_project_items(db: Session, project_id: UUID):
    return db.query(ProjectItemMap).filter(ProjectItemMap.project_id == project_id).all()

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
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to view project items"
            ).model_dump()

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
            total_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(ProjectBalance.project_id == project.uuid)
                .scalar()
            ) or 0.0

            # Get PO balance
            po_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(
                    ProjectBalance.project_id == project.uuid,
                    ProjectBalance.balance_type == "po"
                )
                .scalar()
            ) or project.po_balance

            # Get estimated balance
            estimated_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(
                    ProjectBalance.project_id == project.uuid,
                    ProjectBalance.balance_type == "estimated"
                )
                .scalar()
            ) or project.estimated_balance

            # Get actual balance
            actual_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(
                    ProjectBalance.project_id == project.uuid,
                    ProjectBalance.balance_type == "actual"
                )
                .scalar()
            ) or project.actual_balance

            project_response.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "balance": total_balance,  # For backward compatibility
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
            db.query(Project, ProjectUserMap)
            .join(ProjectUserMap, Project.uuid == ProjectUserMap.project_id)
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
            total_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(ProjectBalance.project_id == project.uuid)
                .scalar()
            ) or 0.0

            # Get PO balance
            po_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(
                    ProjectBalance.project_id == project.uuid,
                    ProjectBalance.balance_type == "po"
                )
                .scalar()
            ) or project.po_balance

            # Get estimated balance
            estimated_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(
                    ProjectBalance.project_id == project.uuid,
                    ProjectBalance.balance_type == "estimated"
                )
                .scalar()
            ) or project.estimated_balance

            # Get actual balance
            actual_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(
                    ProjectBalance.project_id == project.uuid,
                    ProjectBalance.balance_type == "actual"
                )
                .scalar()
            ) or project.actual_balance

            projects_list.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "balance": total_balance,  # For backward compatibility
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
    description="Get all projects and their assigned items for a specific user"
)
def get_user_project_items(
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
            total_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(ProjectBalance.project_id == project.uuid)
                .scalar()
            ) or 0.0

            projects_list.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "balance": total_balance,
                "po_balance": project.po_balance,
                "estimated_balance": project.estimated_balance,
                "actual_balance": project.actual_balance,
                "items": items_list
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
        "amount": 500.0,
        "description": "Invoice for materials"
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

        # Handle invoice file upload if provided
        file_path = None
        if invoice_file:
            upload_dir = "uploads/invoices"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, f"Invoice_{str(uuid4())}_{invoice_file.filename}")
            with open(file_path, "wb") as buffer:
                buffer.write(invoice_file.file.read())

        # Create new invoice
        new_invoice = Invoice(
            project_id=invoice_request.project_id,
            amount=invoice_request.amount,
            description=invoice_request.description,
            file_path=file_path,
            status="uploaded",
            created_by=current_user.uuid
        )
        db.add(new_invoice)

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
                "amount": new_invoice.amount,
                "description": new_invoice.description,
                "file_path": new_invoice.file_path,
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
                "amount": invoice.amount,
                "description": invoice.description,
                "file_path": invoice.file_path,
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
                "amount": invoice.amount,
                "description": invoice.description,
                "file_path": invoice.file_path,
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
                "payment_mode": entry.payment_mode
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

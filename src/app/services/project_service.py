import logging
import os
import json
from uuid import UUID, uuid4
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from decimal import Decimal

from src.app.database.database import get_db
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
    PaymentItem
)
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.project_service_schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectServiceResponse,
    UpdateProjectSchema,
    BankCreateSchema,
    BankEditSchema,
    InvoiceCreateRequest,
    InvoiceResponse,
    InvoiceStatusUpdateRequest
)
from src.app.services.auth_service import get_current_user

project_router = APIRouter(prefix="/projects")

balance_router = APIRouter(prefix="")


def create_project_balance_entry(
    db, current_user, project_id: UUID, adjustment: float,
    description: str = None, balance_type: str = "actual"
):
    balance_entry = ProjectBalance(
        project_id=project_id,
        adjustment=adjustment,
        description=description,
        balance_type=balance_type
    )
    db.add(balance_entry)
    # log_entry = Log(
    #         uuid=str(uuid4()),
    #         entity="Project",
    #         action="Aded Project Balance",
    #         entity_id=project_id,
    #         performed_by=current_user.uuid,
    #     )
    # db.add(log_entry)
    db.commit()
    db.refresh(balance_entry)


@project_router.put(
        "/update-balance",
        tags=["Projects"],
        deprecated=True
    )
def update_project_balance(
    project_uuid: UUID,
    new_balance: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project_balance = (
            db.query(ProjectBalance)
            .filter(ProjectBalance.project_id == project_uuid)
            .order_by(ProjectBalance.id.asc())
            .first()
        )
        if not project_balance:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project balance not found"
            ).model_dump()

        # Update project balance
        project_balance.adjustment = new_balance
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Payment",
            action="Update",
            entity_id=project_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        total_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(ProjectBalance.project_id == project_uuid)
            .scalar()
        ) or 0.0
        return ProjectServiceResponse(
            data=total_balance,
            message="Project balance updated successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching project details: {str(e)}"
        ).model_dump()


@project_router.get("/balance", tags=["Projects"])
def get_project_balance(project_uuid: UUID, db: Session = Depends(get_db)):
    try:
        project = (
            db.query(Project).filter(Project.uuid == project_uuid).first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        total_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(ProjectBalance.project_id == project_uuid)
            .scalar()
        ) or 0.0

        response = {"project_uuid": project_uuid, "balance": total_balance}
        return ProjectServiceResponse(
            data=response,
            message="Project balance fetched successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching project details: {str(e)}"
        ).model_dump()


@project_router.put(
        "/adjust-balance",
        tags=["Projects"],
        deprecated=True
    )
def adjust_project_balance(
    project_uuid: UUID,
    adjustment: float,
    description: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = (
            db.query(Project).filter(Project.uuid == project_uuid).first()
        )
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to adjust balance"
            ).model_dump()

        create_project_balance_entry(db=db, project_id=project_uuid, adjustment=adjustment, description=description, current_user=current_user)
        return ProjectServiceResponse(
            data=None,
            message="Project balance adjusted successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching project details: {str(e)}"
        ).model_dump()


@project_router.post(
    "/create", status_code=status.HTTP_201_CREATED, tags=["Projects"],
    description="""
    Create a new project with optional PO document upload.

    Request body should be sent as a form with 'request' field containing a JSON string with the following structure:
    ```json
    {
        "name": "Project Name",
        "description": "Project Description",
        "location": "Project Location",
        "po_balance": 1000.0,
        "estimated_balance": 1500.0,
        "actual_balance": 500.0
    }
    ```

    The PO document can be uploaded as a file in the 'po_document' field.
    """
)
def create_project(
    request: str = Form(..., description="JSON string containing project details (name, description, location, po_balance, estimated_balance, actual_balance)"),
    po_document: Optional[UploadFile] = File(None, description="PO document file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Parse the request data from form
        request_data = json.loads(request)
        project_request = ProjectCreateRequest(**request_data)

        logging.info(f"Create project request received: {project_request}")
        # Fix: current_user might be dict, access role accordingly
        user_role = current_user.role if hasattr(current_user, 'role') else current_user.get('role')
        logging.info(f"Current user role: {user_role}")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message=constants.CAN_NOT_CREATE_PROJECT
            ).model_dump()

        project_uuid = str(uuid4())

        # Handle PO document upload if provided
        po_document_path = None
        if po_document:
            upload_dir = constants.UPLOAD_DIR
            os.makedirs(upload_dir, exist_ok=True)

            # Create a unique filename with UUID to avoid collisions
            file_ext = os.path.splitext(po_document.filename)[1]
            unique_filename = f"PO_{project_uuid}_{str(uuid4())}{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)

            # Save the file
            with open(file_path, "wb") as buffer:
                buffer.write(po_document.file.read())
            po_document_path = file_path

        # Create new project with all balance types
        new_project = Project(
            uuid=project_uuid,
            name=project_request.name,
            description=project_request.description,
            location=project_request.location,
            po_balance=project_request.po_balance,
            estimated_balance=project_request.estimated_balance,
            actual_balance=project_request.actual_balance,
            po_document_path=po_document_path
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        # Initialize project balances with the given amounts
        # PO Balance
        if project_request.po_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.po_balance,
                description="Initial PO balance",
                current_user=current_user,
                balance_type="po"
            )

        # Estimated Balance
        if project_request.estimated_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.estimated_balance,
                description="Initial estimated balance",
                current_user=current_user,
                balance_type="estimated"
            )

        # Actual Balance
        if project_request.actual_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.actual_balance,
                description="Initial actual balance",
                current_user=current_user,
                balance_type="actual"
            )

        # Create a log entry for project creation
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Project",
            action="Create",
            entity_id=project_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data={
                "uuid": str(new_project.uuid),
                "name": new_project.name,
                "description": new_project.description,
                "location": new_project.location,
                "po_balance": new_project.po_balance,
                "estimated_balance": new_project.estimated_balance,
                "actual_balance": new_project.actual_balance,
                "po_document_path": new_project.po_document_path
            },
            message="Project Created Successfully",
            status_code=201
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in create_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while creating project: {str(e)}"
        ).model_dump()


@project_router.get("", status_code=status.HTTP_200_OK, tags=["Projects"])
def list_all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all projects visible to the current user.

    • Super-Admin / Admin → every non-deleted project
    • Everyone else      → only projects they’re mapped to (ProjectUserMap)

    Response schema
    ----------------
    [
        {
            "uuid": <project-uuid>,
            "name": "<project-name>",
            "description": "<project-description>",
            "location": "<project-location>",
            "balance": <current_balance_float>,  # For backward compatibility
            "po_balance": <po_balance_float>,
            "estimated_balance": <estimated_balance_float>,
            "actual_balance": <actual_balance_float>,
            "po_document_path": <po_document_path_string>,
            "items_count": <total_number_of_items_in_project>,
            "exceeding_items": {
                "count": <number_of_items_exceeding_estimation>,
                "items": [
                    {
                        "item_name": "<item-name>",
                        "estimation": <estimation_amount>,
                        "current_expense": <current_expense_amount>
                    },
                    ...
                ]
            }
        },
        ...
    ]
    """
    try:
        # 1. Base project list depending on role
        if current_user.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, UserRole.ACCOUNTANT.value]:
            projects = db.query(
                Project
            ).filter(
                Project.is_deleted.is_(False)
            ).order_by(Project.id.desc()).all()
        else:
            projects = (
                db.query(Project)
                .join(
                    ProjectUserMap,
                    Project.uuid == ProjectUserMap.project_id
                )
                .filter(
                    Project.is_deleted.is_(False),
                    ProjectUserMap.user_id == current_user.uuid,
                )
                .order_by(Project.id.desc())
                .all()
            )

        # 2. Build response with all balance types
        projects_response_data = []
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

            # Get all items mapped to this project with their balances
            project_items = (
                db.query(ProjectItemMap, Item)
                .join(Item, ProjectItemMap.item_id == Item.uuid)
                .filter(ProjectItemMap.project_id == project.uuid)
                .all()
            )

            # Count total items
            items_count = len(project_items)

            # Find items where current expense exceeds estimation
            exceeding_items = []
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
                        Payment.project_id == project.uuid,
                        Payment.status == 'transferred',
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
                            Payment.status == 'transferred',
                            Payment.is_deleted.is_(False)
                        )
                        .scalar() or 0.0
                    )

                # Check if current expense exceeds estimation
                if current_expense > estimation:
                    exceeding_items.append({
                        "item_name": item.name,
                        "estimation": estimation,
                        "current_expense": current_expense
                    })

            projects_response_data.append(
                {
                    "uuid": project.uuid,
                    "name": project.name,
                    "description": project.description,
                    "location": project.location,
                    "balance": total_balance,  # For backward compatibility
                    "po_balance": po_balance,
                    "estimated_balance": estimated_balance,
                    "actual_balance": actual_balance,
                    "po_document_path": constants.HOST_URL + "/" + project.po_document_path,
                    "items_count": items_count,
                    "exceeding_items": {
                        "count": len(exceeding_items),
                        "items": exceeding_items
                    }
                }
            )

        return ProjectServiceResponse(
            data=projects_response_data,
            message="Projects fetched successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in list_all_projects API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching project details."
        ).model_dump()


@project_router.get(
    "/project", status_code=status.HTTP_200_OK, tags=["Projects"]
)
def get_project_info(project_uuid: UUID, db: Session = Depends(get_db)):
    try:
        project = (
            db.query(Project)
            .filter(
                and_(
                    Project.uuid == project_uuid, Project.is_deleted.is_(False)
                )
            )
            .first()
        )
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message=constants.PROJECT_NOT_FOUND
            ).model_dump()

        # Get total balance (for backward compatibility)
        total_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(ProjectBalance.project_id == project_uuid)
            .scalar()
        ) or 0.0

        # Get PO balance
        po_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(
                ProjectBalance.project_id == project_uuid,
                ProjectBalance.balance_type == "po"
            )
            .scalar()
        ) or project.po_balance

        # Get estimated balance
        estimated_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(
                ProjectBalance.project_id == project_uuid,
                ProjectBalance.balance_type == "estimated"
            )
            .scalar()
        ) or project.estimated_balance

        # Get actual balance
        actual_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(
                ProjectBalance.project_id == project_uuid,
                ProjectBalance.balance_type == "actual"
            )
            .scalar()
        ) or project.actual_balance

        project_response_data = ProjectResponse(
            uuid=project.uuid,
            description=project.description,
            name=project.name,
            location=project.location,
            balance=total_balance,
            po_balance=po_balance,
            estimated_balance=estimated_balance,
            actual_balance=actual_balance,
            po_document_path=project.po_document_path
        ).model_dump()
        return ProjectServiceResponse(
            data=project_response_data,
            message="Project info fetched successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_project_info API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching project details: {str(e)}"
        ).model_dump()



@project_router.put("/{project_uuid}", tags=["Projects"], status_code=200)
def update_project(
    project_uuid: UUID,
    payload: UpdateProjectSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing Project's details:
      - name
      - description
      - location

    Returns 404 if project not found.
    """
    try:
        project = (
            db.query(Project)
            .filter(Project.uuid == project_uuid, Project.is_deleted.is_(False))
            .first()
        )
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Example: Only Admin, SuperAdmin, or PM can update a project
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="You are not authorized to update projects"
            ).model_dump()

        # Update fields if provided
        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.description = payload.description
        if payload.location is not None:
            project.location = payload.location

        # Optionally add a log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Project",
            action="Update",
            entity_id=project_uuid,
            performed_by=current_user.uuid
        )
        db.add(log_entry)

        db.commit()
        db.refresh(project)

        return ProjectServiceResponse(
            data={
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location
            },
            message="Project updated successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while updating project: {str(e)}"
        ).model_dump()


def get_total_transferred_payments_sum(db):
    total_sum = db.query(func.sum(Payment.amount))\
                  .filter(Payment.status == 'transferred', Payment.is_deleted.is_(False))\
                  .scalar()
    if total_sum:
        return total_sum
    else:
        return 0.0


@balance_router.post("/bank", tags=["Bank Balance"])
def add_bank(
    bank_data: BankCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new bank/cash entry.
    Only Accountant or Super Admin can do this.
    """
    try:
        if current_user.role not in [UserRole.ACCOUNTANT.value, UserRole.SUPER_ADMIN.value]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Only Accountant or Super Admin can add bank balance"
            ).model_dump()

        new_bank = BalanceDetail(
            name=bank_data.name,
            balance=bank_data.balance
        )
        db.add(new_bank)
        db.commit()
        db.refresh(new_bank)

        response_data = {
            "uuid": str(new_bank.uuid),
            "name": new_bank.name,
            "balance": new_bank.balance
        }
        return ProjectServiceResponse(
            data=response_data,
            status_code=201,
            message="Bank created successfully"
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in add_bank: {e}")
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while creating bank"
        ).model_dump()


@balance_router.put("/bank/{bank_uuid}", tags=["Bank Balance"])
def edit_bank(
    bank_uuid: UUID,
    bank_data: BankEditSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Edit an existing bank/cash entry.
    Only Accountant or Super Admin can do this.
    """
    try:
        if current_user.role not in [UserRole.ACCOUNTANT.value, UserRole.SUPER_ADMIN.value]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Only Accountant or Super Admin can update bank balance"
            ).model_dump()

        bank_obj = db.query(BalanceDetail).filter(BalanceDetail.uuid == bank_uuid).first()
        if not bank_obj:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message=f"No bank found with uuid={bank_uuid}"
            ).model_dump()

        bank_obj.name = bank_data.name
        bank_obj.balance = bank_data.balance
        db.commit()
        db.refresh(bank_obj)

        response_data = {
            "uuid": str(bank_obj.uuid),
            "name": bank_obj.name,
            "balance": bank_obj.balance
        }
        return ProjectServiceResponse(
            data=response_data,
            status_code=200,
            message="Bank updated successfully"
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in edit_bank: {e}")
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while updating bank"
        ).model_dump()


@balance_router.get("/balance", tags=["Bank Balance"])
def get_bank_balance(
    bank_uuid: Optional[UUID] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    If 'bank_uuid' is given, return that specific bank's details;
    otherwise, return all banks/cash accounts.
    Everyone can view this, or restrict as needed.
    """
    try:
        query = db.query(BalanceDetail)
        if bank_uuid:
            query = query.filter(BalanceDetail.uuid == bank_uuid)

        results = query.all()
        if not results:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="No bank balance found (check bank_uuid?)"
            ).model_dump()

        # Build a list of dict
        data_out = []
        for b in results:
            data_out.append({
                "uuid": str(b.uuid),
                "name": b.name,
                "balance": b.balance
            })

        return ProjectServiceResponse(
            data=data_out,
            status_code=200,
            message="Bank Balance(s) fetched successfully."
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in get_bank_balance API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while getting bank balances"
        ).model_dump()


@balance_router.delete(
        "/bank/{bank_uuid}",
        status_code=status.HTTP_200_OK,
        tags=["Bank Balance"]
)
def delete_bank(
    bank_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ProjectServiceResponse:
    try:
        if current_user.role not in [UserRole.ACCOUNTANT.value, UserRole.SUPER_ADMIN.value]:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Only Accountant or Super Admin can delete bank data"
            ).model_dump()

        bank_data = db.query(
            BalanceDetail
        ).filter(
            BalanceDetail.uuid == bank_uuid
        ).first()

        if not bank_data:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Bank Not Found"
            ).model_dump()

        db.delete(bank_data)
        db.commit()

        return ProjectServiceResponse(
            data=None,
            status_code=200,
            message="Bank Deleted Successfully"
        ).model_dump()

    except Exception as e:
        db.rollback()
        logging.error(f"Error in delete_bank API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while deleting bank"
        ).model_dump()


@project_router.delete("/{project_uuid}", status_code=status.HTTP_200_OK, tags=["Projects"])
def delete_project(
    project_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = (
            db.query(
                Project
            ).filter(
                Project.uuid == project_uuid,
                Project.is_deleted.is_(False)
            ).first()
        )
        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to delete project"
            ).model_dump()

        project.is_deleted = True
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Project",
            action="Delete",
            entity_id=project_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data=None,
            message="Project deleted successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in delete_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while deleting the project"
        ).model_dump()

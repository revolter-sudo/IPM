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
    PaymentItem,
    ProjectPO,
    InvoicePayment
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


@project_router.get(
        "/balance",
        tags=["Projects"],
        deprecated=True
    )
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
    Create a new project with optional multiple PO documents upload.

    Request body should be sent as a form with 'request' field containing a JSON string with the following structure:
    ```json
    {
        "name": "Project Name",
        "description": "Project Description",
        "location": "Project Location",
        "start_date": "2025-06-04",
        "end_date": "2026-06-04",
        "po_balance": 1000.0,
        "estimated_balance": 1500.0,
        "actual_balance": 500.0,
        "pos": [
            {
                "po_number": "PO001",
                "amount": 500.0,
                "description": "First PO"
            },
            {
                "po_number": "PO002",
                "amount": 500.0,
                "description": "Second PO"
            }
        ]
    }
    ```

    Multiple PO documents can be uploaded as files with names 'po_document_0', 'po_document_1', etc.
    """
)
def create_project(
    request: str = Form(..., description="JSON string containing project details including multiple POs"),
    po_document_0: Optional[UploadFile] = File(None, description="First PO document file"),
    po_document_1: Optional[UploadFile] = File(None, description="Second PO document file"),
    po_document_2: Optional[UploadFile] = File(None, description="Third PO document file"),
    po_document_3: Optional[UploadFile] = File(None, description="Fourth PO document file"),
    po_document_4: Optional[UploadFile] = File(None, description="Fifth PO document file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Parse the request data from form
        request_data = json.loads(request)
        project_request = ProjectCreateRequest(**request_data)

        logger.info(f"Create project request received: {project_request}")
        # Fix: current_user might be dict, access role accordingly
        user_role = current_user.role if hasattr(current_user, 'role') else current_user.get('role')
        logger.info(f"Current user role: {user_role}")
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

        # Handle legacy single PO document upload if provided
        po_document_path = None
        po_documents = [po_document_0, po_document_1, po_document_2, po_document_3, po_document_4]

        # Create new project with all balance types
        new_project = Project(
            uuid=project_uuid,
            name=project_request.name,
            description=project_request.description,
            start_date=project_request.start_date,
            end_date=project_request.end_date,
            location=project_request.location,
            po_balance=project_request.po_balance,
            estimated_balance=project_request.estimated_balance,
            actual_balance=project_request.actual_balance,
            po_document_path=po_document_path  # Keep for backward compatibility
        )
        db.add(new_project)
        db.flush()  # Get the project ID without committing

        # Handle multiple POs if provided
        created_pos = []
        if project_request.pos:
            for idx, po_request in enumerate(project_request.pos):
                # Handle PO document upload if provided
                po_file_path = None
                if idx < len(po_documents) and po_documents[idx]:
                    upload_dir = constants.UPLOAD_DIR
                    os.makedirs(upload_dir, exist_ok=True)

                    # Create a unique filename with UUID to avoid collisions
                    file_ext = os.path.splitext(po_documents[idx].filename)[1]
                    unique_filename = f"PO_{project_uuid}_{idx}_{str(uuid4())}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)

                    # Save the file
                    with open(file_path, "wb") as buffer:
                        buffer.write(po_documents[idx].file.read())
                    po_file_path = file_path

                # Create ProjectPO entry
                new_po = ProjectPO(
                    project_id=new_project.uuid,
                    po_number=po_request.po_number,
                    amount=po_request.amount,
                    description=po_request.description,
                    file_path=po_file_path,
                    created_by=current_user.uuid
                )
                db.add(new_po)
                created_pos.append(new_po)

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

        # Prepare PO data for response
        pos_data = []
        for po in created_pos:
            pos_data.append({
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "amount": po.amount,
                "description": po.description,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None
            })

        return ProjectServiceResponse(
            data={
                "uuid": str(new_project.uuid),
                "name": new_project.name,
                "description": new_project.description,
                "location": new_project.location,
                "start_date": new_project.start_date,
                "end_date": new_project.end_date,
                "po_balance": new_project.po_balance,
                "estimated_balance": new_project.estimated_balance,
                "actual_balance": new_project.actual_balance,
                "po_document_path": new_project.po_document_path,
                "pos": pos_data  # New field for multiple POs
            },
            message="Project Created Successfully",
            status_code=201
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in create_project API: {str(e)}")
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
    • Everyone else      → only projects they're mapped to (ProjectUserMap)

    Response schema
    ----------------
    [
        {
            "uuid": <project-uuid>,
            "name": "<project-name>",
            "description": "<project-description>",
            "location": "<project-location>",
            "start_date": "project-start_date",
            "end_date": "project-end_date",
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
                    "start_date": project.start_date,
                    "end_date": project.end_date,
                    "po_balance": po_balance,
                    "estimated_balance": estimated_balance,
                    "actual_balance": actual_balance,
                    "po_document_path": constants.HOST_URL + "/" + project.po_document_path if project.po_document_path else None,
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
        logger.error(f"Error in list_all_projects API: {str(e)}")
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
        # total_balance = (
        #     db.query(func.sum(ProjectBalance.adjustment))
        #     .filter(ProjectBalance.project_id == project_uuid)
        #     .scalar()
        # ) or 0.0

        # Get PO balance
        po_balance = project.po_balance if project.po_balance else 0

        # Get estimated balance
        estimated_balance = project.estimated_balance if project.estimated_balance else 0

        # Get actual balance
        actual_balance = project.actual_balance if project.actual_balance else 0

        project_response_data = ProjectResponse(
            uuid=project.uuid,
            description=project.description,
            name=project.name,
            location=project.location,
            start_date=project.start_date,
            end_date=project.end_date,
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
        logger.error(f"Error in get_project_info API: {str(e)}")
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
      - start_date
      - end_date
      - po_balance
      - estimated_balance
      - actual_balance

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
        if payload.start_date is not None:
            project.start_date = payload.start_date
        if payload.end_date is not None:
            project.end_date = payload.end_date
        if payload.po_balance is not None:
            project.po_balance = payload.po_balance
        if payload.estimated_balance is not None:
            project.estimated_balance = payload.estimated_balance
        if payload.actual_balance is not None:
            project.actual_balance = payload.actual_balance

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
                "location": project.location,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "po_balance": project.po_balance,
                "estimated_balance": project.estimated_balance,
                "actual_balance": project.actual_balance
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
        logger.error(f"Error in add_bank: {e}")
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
        logger.error(f"Error in edit_bank: {e}")
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
        logger.error(f"Error in get_bank_balance API: {str(e)}")
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
        logger.error(f"Error in delete_bank API: {str(e)}")
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
        logger.error(f"Error in delete_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while deleting the project"
        ).model_dump()



# Additional PO Management APIs for unlimited PO support

@project_router.post(
    "/{project_id}/pos",
    status_code=status.HTTP_201_CREATED,
    tags=["Project POs"],
    description="""
    Add a new PO to an existing project.
    
    This API allows unlimited POs to be added to a project after creation.
    Each PO can have its own document, amount, and description.
    """
)
def add_project_po(
    project_id: UUID,
    po_data: str = Form(..., description="JSON string containing PO details"),
    po_document: Optional[UploadFile] = File(None, description="PO document file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new PO to an existing project with optional document upload."""
    try:
        # Parse PO data
        po_request_data = json.loads(po_data)
        
        # Validate required fields
        if not po_request_data.get("amount") or po_request_data["amount"] <= 0:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Amount must be greater than 0"
            ).model_dump()

        # Check if project exists
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

        # Check permissions
        user_role = current_user.role if hasattr(current_user, "role") else current_user.get("role")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to add POs to project"
            ).model_dump()

        # Check for duplicate PO number within the project
        if po_request_data.get("po_number"):
            existing_po = db.query(ProjectPO).filter(
                ProjectPO.project_id == project_id,
                ProjectPO.po_number == po_request_data["po_number"],
                ProjectPO.is_deleted.is_(False)
            ).first()
            
            if existing_po:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message=f"PO number \"{po_request_data[\"po_number\"]}\" already exists in this project"
                ).model_dump()

        # Handle document upload if provided
        po_file_path = None
        file_info = {"uploaded": False, "filename": None, "size": 0}
        
        if po_document and po_document.filename:
            try:
                upload_dir = constants.UPLOAD_DIR
                os.makedirs(upload_dir, exist_ok=True)

                # Validate file type
                allowed_extensions = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".txt", ".xlsx", ".xls"}
                file_ext = os.path.splitext(po_document.filename)[1].lower()
                
                if file_ext not in allowed_extensions:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message=f"File type {file_ext} not allowed. Allowed types: {\", \".join(allowed_extensions)}"
                    ).model_dump()

                # Create unique filename
                safe_po_number = (po_request_data.get("po_number", "PO") or "PO").replace("/", "_").replace("\\", "_")
                unique_filename = f"PO_{project_id}_{safe_po_number}_{str(uuid4())}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)

                # Read and validate file content
                content = po_document.file.read()
                if len(content) == 0:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message="Uploaded file is empty"
                    ).model_dump()
                
                # Check file size (max 10MB)
                max_size = 10 * 1024 * 1024  # 10MB
                if len(content) > max_size:
                    return ProjectServiceResponse(
                        data=None,
                        status_code=400,
                        message="File size exceeds 10MB limit"
                    ).model_dump()

                # Save the file
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                
                po_file_path = file_path
                file_info.update({
                    "uploaded": True,
                    "filename": po_document.filename,
                    "size": len(content)
                })
                
                logger.info(f"PO document saved: {po_file_path}")
                
            except Exception as file_error:
                logger.error(f"Error saving PO document: {str(file_error)}")
                return ProjectServiceResponse(
                    data=None,
                    status_code=500,
                    message=f"Failed to save PO document: {str(file_error)}"
                ).model_dump()

        # Create new PO
        new_po = ProjectPO(
            project_id=project_id,
            po_number=po_request_data.get("po_number"),
            amount=po_request_data["amount"],
            description=po_request_data.get("description"),
            file_path=po_file_path,
            created_by=current_user.uuid
        )
        
        db.add(new_po)
        db.commit()
        db.refresh(new_po)

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="ProjectPO",
            action="Create",
            entity_id=new_po.uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return ProjectServiceResponse(
            data={
                "uuid": str(new_po.uuid),
                "project_id": str(new_po.project_id),
                "po_number": new_po.po_number,
                "amount": new_po.amount,
                "description": new_po.description,
                "file_path": constants.HOST_URL + "/" + new_po.file_path if new_po.file_path else None,
                "has_document": new_po.file_path is not None,
                "file_info": file_info,
                "created_at": new_po.created_at.isoformat() if new_po.created_at else None
            },
            message="PO added to project successfully",
            status_code=201
        ).model_dump()

    except json.JSONDecodeError as json_error:
        logger.error(f"JSON parsing error in add_project_po: {str(json_error)}")
        return ProjectServiceResponse(
            data=None,
            status_code=400,
            message=f"Invalid JSON in PO data: {str(json_error)}"
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in add_project_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while adding PO: {str(e)}"
        ).model_dump()


@project_router.get(
    "/{project_id}/pos",
    tags=["Project POs"],
    description="Get all POs for a specific project"
)
def get_project_pos(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all POs for a specific project with their details."""
    try:
        # Check if project exists
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

        # Get all POs for this project
        pos = db.query(ProjectPO).filter(
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).order_by(ProjectPO.created_at).all()

        # Format PO data
        pos_data = []
        total_amount = 0.0
        files_count = 0
        
        for po in pos:
            po_data = {
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "amount": po.amount,
                "description": po.description,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                "has_document": po.file_path is not None,
                "created_at": po.created_at.isoformat() if po.created_at else None,
                "created_by": str(po.created_by)
            }
            pos_data.append(po_data)
            total_amount += po.amount
            if po.file_path:
                files_count += 1

        return ProjectServiceResponse(
            data={
                "project_id": str(project_id),
                "project_name": project.name,
                "po_summary": {
                    "total_pos": len(pos),
                    "total_amount": total_amount,
                    "files_uploaded": files_count,
                    "files_missing": len(pos) - files_count
                },
                "pos": pos_data
            },
            message="Project POs fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_project_pos API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching project POs: {str(e)}"
        ).model_dump()


@project_router.put(
    "/{project_id}/pos/{po_id}",
    tags=["Project POs"],
    description="Update an existing PO"
)
def update_project_po(
    project_id: UUID,
    po_id: UUID,
    po_data: str = Form(..., description="JSON string containing updated PO details"),
    po_document: Optional[UploadFile] = File(None, description="New PO document file (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing PO with optional document replacement."""
    try:
        # Parse PO data
        po_request_data = json.loads(po_data)

        # Check permissions
        user_role = current_user.role if hasattr(current_user, "role") else current_user.get("role")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to update POs"
            ).model_dump()

        # Find the PO
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).first()
        
        if not po:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found"
            ).model_dump()

        # Update PO fields
        if "po_number" in po_request_data:
            po.po_number = po_request_data["po_number"]
        if "amount" in po_request_data:
            if po_request_data["amount"] <= 0:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message="Amount must be greater than 0"
                ).model_dump()
            po.amount = po_request_data["amount"]
        if "description" in po_request_data:
            po.description = po_request_data["description"]

        db.commit()
        db.refresh(po)

        return ProjectServiceResponse(
            data={
                "uuid": str(po.uuid),
                "project_id": str(po.project_id),
                "po_number": po.po_number,
                "amount": po.amount,
                "description": po.description,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                "has_document": po.file_path is not None,
                "updated_at": po.updated_at.isoformat() if po.updated_at else None
            },
            message="PO updated successfully",
            status_code=200
        ).model_dump()

    except json.JSONDecodeError as json_error:
        logger.error(f"JSON parsing error in update_project_po: {str(json_error)}")
        return ProjectServiceResponse(
            data=None,
            status_code=400,
            message=f"Invalid JSON in PO data: {str(json_error)}"
        ).model_dump()
    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_project_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while updating PO: {str(e)}"
        ).model_dump()


@project_router.delete(
    "/{project_id}/pos/{po_id}",
    tags=["Project POs"],
    description="Delete a PO from a project"
)
def delete_project_po(
    project_id: UUID,
    po_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft delete a PO from a project."""
    try:
        # Check permissions
        user_role = current_user.role if hasattr(current_user, "role") else current_user.get("role")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to delete POs"
            ).model_dump()

        # Find the PO
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).first()
        
        if not po:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found"
            ).model_dump()

        # Check if PO has associated invoices
        invoices = db.query(Invoice).filter(
            Invoice.project_po_id == po_id,
            Invoice.is_deleted.is_(False)
        ).count()
        
        if invoices > 0:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message=f"Cannot delete PO. It has {invoices} associated invoice(s). Please delete or reassign the invoices first."
            ).model_dump()

        # Soft delete the PO
        po.is_deleted = True
        db.commit()

        return ProjectServiceResponse(
            data={"deleted_po_id": str(po_id)},
            message="PO deleted successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in delete_project_po API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while deleting PO: {str(e)}"
        ).model_dump()


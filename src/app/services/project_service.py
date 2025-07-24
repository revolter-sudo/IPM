import os
from src.app.utils.logging_config import get_logger
import json
from uuid import UUID, uuid4
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from decimal import Decimal

from src.app.database.database import get_db
from src.app.database.models import (
    Log,
    Project,
    ProjectBalance,
    ProjectUserItemMap,
    User,
    BalanceDetail,
    Payment,
    ProjectUserMap,
    Item,
    ProjectItemMap,
    Invoice,
    PaymentItem,
    ProjectPO,
    ProjectPOItem,
    CompanyInfo
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
    InvoiceStatusUpdateRequest,
    ProjectPOUpdateSchema,
    CompanyInfoCreate,
    CompanyInfoUpdate
)
from src.app.services.location_service import LocationService
from src.app.services.auth_service import get_current_user
from datetime import datetime, timedelta
import traceback

# Initialize logger
logger = get_logger(__name__)

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
            logger.warning(f"[{current_user.username}] project balance not found for {project_uuid}")
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project balance not found"
            ).model_dump()

        # Update adjustment value
        project_balance.adjustment = new_balance

        # Log the update action
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

        logger.info(f"[{current_user.name}] updated balance for project {project_uuid}. New total: {total_balance}")

        return ProjectServiceResponse(
            data=total_balance,
            message="Project balance updated successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"[{current_user.name}] Error updating project balance for {project_uuid}: {str(e)}")
        logger.error(traceback.format_exc())
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
def get_project_balance(project_uuid: UUID, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
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
    "/create",
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"],
    description="""
    Create a new project.
    """
)
def create_project(
    request: str = Form(..., description="JSON string containing project details"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        request_data = json.loads(request)
        project_request = ProjectCreateRequest(**request_data)

        user_role = current_user.role if hasattr(current_user, 'role') else current_user.get('role')

        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            logger.warning(f"[{current_user.name}] not authorized to create a project")
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message=constants.CAN_NOT_CREATE_PROJECT
            ).model_dump()

        project_uuid = str(uuid4())

        # Create Project
        new_project = Project(
            uuid=project_uuid,
            name=project_request.name,
            description=project_request.description,
            start_date=project_request.start_date,
            end_date=project_request.end_date,
            location=project_request.location,
            estimated_balance=project_request.estimated_balance,
            actual_balance=project_request.actual_balance
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        

        # Create estimated balance entry
        if project_request.estimated_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.estimated_balance,
                description="Initial estimated balance",
                current_user=current_user,
                balance_type="estimated"
            )

        # Create actual balance entry
        if project_request.actual_balance > 0:
            create_project_balance_entry(
                db=db,
                project_id=new_project.uuid,
                adjustment=project_request.actual_balance,
                description="Initial actual balance",
                current_user=current_user,
                balance_type="actual"
            )

        # Log the creation
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Project",
            action="Create",
            entity_id=new_project.uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        logger.info(f"Project created by [{current_user.name}]: project name [{new_project.name}]")

        return ProjectServiceResponse(
            data={
                "uuid": str(new_project.uuid),
                "name": new_project.name,
                "description": new_project.description,
                "location": new_project.location,
                "start_date": new_project.start_date,
                "end_date": new_project.end_date,
                "estimated_balance": new_project.estimated_balance,
                "actual_balance": new_project.actual_balance,
            },
            message="Project Created Successfully",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in create_project API by user [{current_user.name}]: {str(e)}")
        logger.error(traceback.format_exc())
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while creating project: {str(e)}"
        ).model_dump()


# @project_router.get("", status_code=status.HTTP_200_OK, tags=["Projects"])
# def list_all_projects(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     Fetch all projects visible to the current user.

#     • Super-Admin / Admin → every non-deleted project
#     • Everyone else      → only projects they're mapped to (ProjectUserMap)

#     Response schema
#     ----------------
#     [
#         {
#             "uuid": <project-uuid>,
#             "name": "<project-name>",
#             "description": "<project-description>",
#             "location": "<project-location>",
#             "start_date": "project-start_date",
#             "end_date": "project-end_date",
#             # "balance": <current_balance_float>,  # For backward compatibility
#             "estimated_balance": <estimated_balance_float>,
#             "actual_balance": <actual_balance_float>,
#             "items_count": <total_number_of_items_in_project>,
#             "exceeding_items": {
#                 "count": <number_of_items_exceeding_estimation>,
#                 "items": [
#                     {
#                         "item_name": "<item-name>",
#                         "estimation": <estimation_amount>,
#                         "current_expense": <current_expense_amount>
#                     },
#                     ...
#                 ]
#             }
#         },
#         ...
#     ]
#     """
#     try:
#         # 1. Base project list depending on role
#         if current_user.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, UserRole.ACCOUNTANT.value]:
#             projects = db.query(
#                 Project
#             ).filter(
#                 Project.is_deleted.is_(False)
#             ).order_by(Project.id.desc()).all()
#         else:
#             projects = (
#                 db.query(Project)
#                 .join(
#                     ProjectUserMap,
#                     Project.uuid == ProjectUserMap.project_id
#                 )
#                 .filter(
#                     Project.is_deleted.is_(False),
#                     ProjectUserMap.user_id == current_user.uuid,
#                 )
#                 .order_by(Project.id.desc())
#                 .all()
#             )

#         # 2. Build response with all balance types
#         projects_response_data = []
#         for project in projects:
#             # Get total balance (for backward compatibility)
#             # total_balance = (
#             #     db.query(func.sum(ProjectBalance.adjustment))
#             #     .filter(ProjectBalance.project_id == project.uuid)
#             #     .scalar()
#             # ) or 0.0

#             # Get PO balance
#             # po_balance = project.po_balance if project.po_balance else 0

#             # Get estimated balance
#             estimated_balance = project.estimated_balance if project.estimated_balance else 0

#             # Get actual balance
#             actual_balance = project.actual_balance if project.actual_balance else 0

#             # Get all items mapped to this project with their balances
#             project_items = (
#                 db.query(ProjectItemMap, Item)
#                 .join(Item, ProjectItemMap.item_id == Item.uuid)
#                 .filter(ProjectItemMap.project_id == project.uuid)
#                 .all()
#             )

#             # Count total items
#             items_count = len(project_items)

#             # Find items where current expense exceeds estimation
#             exceeding_items = []
#             for project_item, item in project_items:
#                 # Get estimation (balance added when assigned)
#                 estimation = project_item.item_balance or 0.0

#                 # Get current expense (sum of transferred payments for this item)
#                 # First, get all payment items for this item in this project
#                 payment_items = (
#                     db.query(PaymentItem)
#                     .join(Payment, PaymentItem.payment_id == Payment.uuid)
#                     .filter(
#                         PaymentItem.item_id == item.uuid,
#                         Payment.project_id == project.uuid,
#                         Payment.status == 'transferred',
#                         Payment.is_deleted.is_(False),
#                         PaymentItem.is_deleted.is_(False)
#                     )
#                     .all()
#                 )
#                 # Fetch all POs for this project
#                 pos = []
#                 for po in project.project_pos:
#                     creator = db.query(User.name).filter(User.uuid == po.created_by).scalar()
#                     pos.append({
#                         "uuid": str(po.uuid),
#                         "po_number": po.po_number,
#                         "amount": po.amount,
#                         "description": po.description,
#                         "file_path": po.file_path,
#                         "created_by": creator or "Unknown",
#                         "created_at": po.created_at
#                     })


#                 # Get the payment amounts
#                 payment_ids = [pi.payment_id for pi in payment_items]
#                 current_expense = 0.0
#                 if payment_ids:
#                     current_expense = (
#                         db.query(func.sum(Payment.amount))
#                         .filter(
#                             Payment.uuid.in_(payment_ids),
#                             Payment.status == 'transferred',
#                             Payment.is_deleted.is_(False)
#                         )
#                         .scalar() or 0.0
#                     )

#                 # Check if current expense exceeds estimation
#                 if current_expense > estimation:
#                     exceeding_items.append({
#                         "item_name": item.name,
#                         "estimation": estimation,
#                         "current_expense": current_expense
#                     })

#             projects_response_data.append(
#                 {
#                     "uuid": project.uuid,
#                     "name": project.name,
#                     "description": project.description,
#                     "location": project.location,
#                     "start_date": project.start_date,
#                     "end_date": project.end_date,
#                     "estimated_balance": estimated_balance,
#                     "actual_balance": actual_balance,
#                     "items_count": items_count,
#                     "exceeding_items": {
#                         "count": len(exceeding_items),
#                         "items": exceeding_items
#                     },
#                     "pos":pos
#                 }
#             )

#         return ProjectServiceResponse(
#             data=projects_response_data,
#             message="Projects fetched successfully.",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         logger.error(f"Error in list_all_projects API: {str(e)}")
#         return ProjectServiceResponse(
#             data=None,
#             status_code=500,
#             message="An error occurred while fetching project details."
#         ).model_dump()

@project_router.get(
    "",
    status_code=status.HTTP_200_OK,
    tags=["Projects"],
    description="Fetch all projects visible to the current user along with PO and item expense details."
)
def list_all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch all projects visible to the current user.

    • Super-Admin / Admin / Accountant → every non-deleted project
    • Everyone else → only projects they're mapped to (ProjectUserMap)

    Returns full details with:
    - Estimated & actual balances
    - Items count & overbudget info
    - List of all POs with metadata
    - Total PO amount per project
    """
    try:
        if current_user.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, UserRole.ACCOUNTANT.value]:
            projects = db.query(Project).filter(Project.is_deleted.is_(False)).order_by(Project.id.desc()).all()
        else:
            projects = (
                db.query(Project)
                .join(ProjectUserMap, Project.uuid == ProjectUserMap.project_id)
                .filter(
                    Project.is_deleted.is_(False),
                    ProjectUserMap.user_id == current_user.uuid,
                )
                .order_by(Project.id.desc())
                .all()
            )

        projects_response_data = []

        for project in projects:
            estimated_balance = project.estimated_balance or 0.0
            actual_balance = project.actual_balance or 0.0

            # Item logic - use subquery to handle potential duplicates
            subquery = (
                db.query(
                    ProjectItemMap.project_id,
                    ProjectItemMap.item_id,
                    func.max(ProjectItemMap.id).label('max_id')
                )
                .filter(ProjectItemMap.project_id == project.uuid)
                .group_by(ProjectItemMap.project_id, ProjectItemMap.item_id)
                .subquery()
            )

            project_items = (
                db.query(ProjectItemMap, Item)
                .join(subquery, ProjectItemMap.id == subquery.c.max_id)
                .join(Item, ProjectItemMap.item_id == Item.uuid)
                .all()
            )

            items_count = len(project_items)
            exceeding_items = []

            for project_item, item in project_items:
                estimation = project_item.item_balance or 0.0
                # Get current expense (sum of transferred payments for this item)
                # Use a more direct approach to get the sum of payment amounts
                current_expense = (
                    db.query(func.sum(Payment.amount))
                    .join(PaymentItem, Payment.uuid == PaymentItem.payment_id)
                    .filter(
                        PaymentItem.item_id == item.uuid,
                        Payment.project_id == project.uuid,
                        Payment.status == 'transferred',
                        Payment.is_deleted.is_(False),
                        PaymentItem.is_deleted.is_(False)
                    )
                    .scalar() or 0.0
                )
                if current_expense > estimation:
                    exceeding_items.append({
                        "item_name": item.name,
                        "estimation": estimation,
                        "current_expense": current_expense
                    })

            # PO list and total value
            pos_list = []
            total_po_amount = 0.0
            total_po_paid = 0.0

            for po in project.project_pos:
                if po.is_deleted:
                    continue

                paid_amount = (
                    db.query(func.sum(Invoice.total_paid_amount))
                    .join(ProjectPO, Invoice.project_po_id == ProjectPO.uuid)
                    .filter(
                        Invoice.project_po_id == po.uuid, 
                        Invoice.is_deleted.is_(False), 
                        # Invoice.status == 'paid',
                        Invoice.payment_status.in_(["partially_paid", "fully_paid"])
                    )
                    .scalar() or 0.0
                )
                total_po_paid += paid_amount

                creator_name = db.query(User.name).filter(User.uuid == po.created_by).scalar()
                pos_list.append({
                    "uuid": str(po.uuid),
                    "po_number": po.po_number,
                    "client_name": po.client_name,
                    "amount": po.amount,
                    "description": po.description,
                    "po_date": po.po_date.strftime("%Y-%m-%d") if po.po_date else None,
                    "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                    "created_by": creator_name or "Unknown",
                    "created_at": po.created_at.strftime("%Y-%m-%d %H:%M:%S") if po.created_at else None
                })
                total_po_amount += po.amount or 0.0

            projects_response_data.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "estimated_balance": estimated_balance,
                "actual_balance": actual_balance,
                "created_at": project.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "items_count": items_count,
                "exceeding_items": {
                    "count": len(exceeding_items),
                    "items": exceeding_items
                },
                "total_po_amount": total_po_amount,
                "total_po_paid": total_po_paid,
                "pos": pos_list
            })

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
def get_project_info(project_uuid: UUID, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
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
        # po_balance = project.po_balance if project.po_balance else 0

        # Get estimated balance & actual balance
        estimated_balance = project.estimated_balance if project.estimated_balance else 0
        actual_balance = project.actual_balance if project.actual_balance else 0
        
        total_po_paid = 0.0
        for po in project.project_pos:
            if po.is_deleted:
                continue
            paid_amount = (
                db.query(func.sum(Invoice.total_paid_amount))
                .join(ProjectPO, Invoice.project_po_id == ProjectPO.uuid)
                .filter(
                    Invoice.project_po_id == po.uuid,
                    Invoice.is_deleted.is_(False),
                    Invoice.payment_status.in_(["partially_paid", "fully_paid"])
                )
                .scalar() or 0.0
            )
            total_po_paid += paid_amount

        project_response_data = ProjectResponse(
            uuid=project.uuid,
            description=project.description,
            name=project.name,
            location=project.location,
            start_date=project.start_date,
            end_date=project.end_date,
            estimated_balance=estimated_balance,
            actual_balance=actual_balance,
            created_at=project.created_at,
        ).model_dump()

        project_response_data["total_po_paid"] = total_po_paid

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
    current_user: User = Depends(get_current_user)
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
        # Load project with relationships
        project = (
            db.query(Project)
            .filter(Project.uuid == project_uuid, Project.is_deleted.is_(False))
            .first()
        )

        if not project:
            logger.warning(f"[{project.name}] delete failed - project not found")
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        if current_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            logger.warning(f"[{current_user.name}] not authorized to delete")
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to delete project"
            ).model_dump()

        # Soft delete project
        project.is_deleted = True

        # Soft delete related Payments
        db.query(Payment).filter(
            Payment.project_id == project.uuid
        ).update({Payment.is_deleted: True})

        # Soft delete ProjectUserMap
        db.query(ProjectUserMap).filter(
            ProjectUserMap.project_id == project.uuid
        ).update({ProjectUserMap.is_deleted: True})

        # Soft delete ProjectItemMap
        db.query(ProjectItemMap).filter(
            ProjectItemMap.project_id == project.uuid
        ).update({ProjectItemMap.is_deleted: True})

        # Soft delete ProjectUserItemMap
        db.query(ProjectUserItemMap).filter(
            ProjectUserItemMap.project_id == project.uuid
        ).update({ProjectUserItemMap.is_deleted: True})

        # Add log
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Project",
            action="Delete",
            entity_id=project_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)

        db.commit()
        logger.info(f"[{current_user.name}]: project deleted successfully[{project.name}]")

        return ProjectServiceResponse(
            data=None,
            message="Project and related data deleted successfully",
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


# Simple PO Management API for unlimited PO support

@project_router.post(
    "/{project_id}/pos",
    status_code=status.HTTP_201_CREATED,
    tags=["Project POs"],
    description="""
Add a new Purchase Order (PO) under a project.

Send the PO data as a JSON string via the `po_data` form field and optionally upload a PO document file.

 **Example `po_data` JSON Format**:
```json
{
  "po_number": "PO-2025-0005",         
  "client_name": "ABC Company",        
  "amount": 500.0,                     
  "description": "Invoice for materials", 
  "po_date": "2025-06-15",             
  "items": [
    {
      "item_name": "Steel Rods",
      "basic_value": 200
    },
    {
      "item_name": "Cement Bags",
      "basic_value": 300
    }
  ]
}
 File Upload :

Use po_document field to attach a PDF/DOCX file.
"""
)
def add_project_po(
    project_id: UUID,
    po_data: str = Form(..., description="JSON string containing PO details"),
    po_document: Optional[UploadFile] = File(None, description="PO document file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        po_request_data = json.loads(po_data)
        amount = po_request_data.get("amount")
        description = po_request_data.get("description")
        client_name = po_request_data.get("client_name")
        po_number = po_request_data.get("po_number")  # Can be None
        po_date_str = po_request_data.get("po_date")  # Expecting date string
        items = po_request_data.get("items", [])

        if not amount or amount <= 0:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Amount must be greater than 0"
            ).model_dump()

        # Convert date
        po_date = None
        if po_date_str:
            try:
                po_date = datetime.strptime(po_date_str, "%Y-%m-%d").date()
            except ValueError:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message="Invalid date format. Use YYYY-MM-DD"
                ).model_dump()

        # Check project
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()
        if not project:
            logger.warning(f"[{project.name}] not found.")
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Role check
        user_role = getattr(current_user, "role", None) or current_user.get("role")
        if user_role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            logger.warning(f"[{current_user.name}] not authorized for creating po")
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Unauthorized to add POs to project"
            ).model_dump()

        # Auto-generate PO number if not given
        if not po_number:
            year = datetime.utcnow().year
            existing_po_count = db.query(ProjectPO).filter(
                ProjectPO.project_id == project_id
            ).count()
            po_number = f"PO-{year}-{str(existing_po_count + 1).zfill(4)}"

        # Save file if provided
        file_path = None
        if po_document:
            ext = os.path.splitext(po_document.filename)[1]
            filename = f"PO_{str(uuid4())}{ext}"
            upload_dir = "uploads/po_docs"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(po_document.file.read())

        # Create main PO
        new_po = ProjectPO(
            project_id=project_id,
            po_number=po_number,
            amount=amount,
            description=description,
            client_name=client_name,
            po_date=po_date,
            file_path=file_path,
            created_by=current_user.uuid
        )
        db.add(new_po)
        db.flush()  # Required to get new_po.uuid before adding items

        # Save items
        for item in items:
            item_name = item.get("item_name")
            basic_value = item.get("basic_value")
            if not item_name or basic_value is None:
                continue
            new_item = ProjectPOItem(
                project_po_id=new_po.uuid,
                item_name=item_name,
                basic_value=basic_value
            )
            db.add(new_item)

        db.commit()
        db.refresh(new_po)
        
        logger.info(f"PO created by [{current_user.name}]: PO-Number[{po_number}]")

        return ProjectServiceResponse(
            data={
                "uuid": str(new_po.uuid),
                "project_id": str(new_po.project_id),
                "project_name": new_po.project.name if new_po.project else None,
                "po_number": new_po.po_number,
                "client_name": new_po.client_name,
                "amount": new_po.amount,
                "description": new_po.description,
                "po_date": new_po.po_date.strftime("%Y-%m-%d") if new_po.po_date else None,
                "created_at": new_po.created_at.strftime("%Y-%m-%d %H:%M:%S") if new_po.created_at else None,
                "items": [
                    {
                        "item_name": item.item_name,
                        "basic_value": item.basic_value
                    } for item in new_po.po_items  # ensure this relationship exists
                ] if hasattr(new_po, "po_items") else [],
                "file_path": new_po.file_path
            },
            message="PO added to project successfully",
            status_code=201
        ).model_dump()

    except json.JSONDecodeError as json_error:
        return ProjectServiceResponse(
            data=None,
            status_code=400,
            message=f"Invalid JSON in PO data: {str(json_error)}"
        ).model_dump()

    except Exception as e:
        db.rollback()
        logger.error(f"Error in create_po API by user [{current_user.name}]: {str(e)}")
        logger.error(traceback.format_exc())
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
    """Get all POs for a specific project."""
    try:
        # Validate project
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

        # Fetch all non-deleted POs
        pos = db.query(ProjectPO).filter(
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).order_by(ProjectPO.created_at).all()

        pos_data = []
        total_amount = 0.0

        for po in pos:

            # Get invoices for this PO
            invoices = db.query(Invoice).filter(
                Invoice.project_po_id == po.uuid,
                Invoice.is_deleted.is_(False)
            ).all()

            # Count invoices for this PO
            invoice_count = len(invoices)

            # total_invoice_amount = sum(inv.amount for inv in invoices)
            # total_paid_amount = sum(inv.total_paid_amount for inv in invoices if inv.payment_status in ["partially_paid", "fully_paid"])
            # pending_amount = total_invoice_amount - total_paid_amount
            # not_generated_amount = po.amount - total_invoice_amount


            po_data = {
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "client_name": po.client_name,
                "amount": po.amount,
                "description": po.description,
                "po_date": po.po_date.strftime("%Y-%m-%d") if po.po_date else None,
                "created_at": po.created_at.strftime("%Y-%m-%d %H:%M:%S") if po.created_at else None,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                "invoice_count": invoice_count,
                "items": [
                    {
                        "item_name": item.item_name,
                        "basic_value": item.basic_value
                    } for item in getattr(po, "po_items", [])
                ] if hasattr(po, "po_items") else [],
                # "metrics": {
                #     "total_po_paid": total_paid_amount,
                #     "total_created_invoice_pending": pending_amount,
                #     "invoice_not_generated_amount": not_generated_amount
                # },
                "created_by": str(po.created_by)
            }
            pos_data.append(po_data)
            total_amount += po.amount

        return ProjectServiceResponse(
            data={
                "project_id": str(project.uuid),
                "project_name": project.name,
                "po_summary": {
                    "total_pos": len(pos),
                    "total_amount": total_amount
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

@project_router.get(
        "/pos",
        tags=["Project POs"],
        status_code=status.HTTP_200_OK,
        description="fetch all pos"
)
def list_all_pos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Get all project UUIDs user can see
        if current_user.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value, UserRole.ACCOUNTANT.value]:
            pos = db.query(ProjectPO).filter(ProjectPO.is_deleted.is_(False)).order_by(ProjectPO.id.desc()).all()
        else:
            project_ids = (
                db.query(ProjectUserMap.project_id)
                .filter(ProjectUserMap.user_id == current_user.uuid)
                .all()
            )
            project_uuids = [pid for (pid,) in project_ids]
            pos = (
                db.query(ProjectPO)
                .filter(ProjectPO.project_id.in_(project_uuids), ProjectPO.is_deleted.is_(False))
                .order_by(ProjectPO.id.desc())
                .all()
            )

        data = []
        for po in pos:
            # Invoices for this PO (if any)
            invoices = (
                db.query(Invoice)
                .filter(
                    Invoice.project_po_id == po.uuid,
                    Invoice.is_deleted.is_(False)
                )
                .order_by(Invoice.id.asc())
                .all()
            )
            invoices_list = [
                {
                    "uuid": str(inv.uuid),
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                    "amount": inv.amount,
                    "total_paid_amount": inv.total_paid_amount,
                    "payment_status": inv.payment_status,
                    "status": inv.status,
                    "file_path": constants.HOST_URL + "/" + inv.file_path if inv.file_path else None,
                }
                for inv in invoices
            ]
            data.append({
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "client_name": po.client_name,
                "amount": po.amount,
                "description": po.description,
                "po_date": po.po_date.strftime("%Y-%m-%d") if po.po_date else None,
                "file_path": constants.HOST_URL + "/" + po.file_path if po.file_path else None,
                "created_by": str(po.created_by),
                "created_at": po.created_at.strftime("%Y-%m-%d %H:%M:%S") if po.created_at else None,
                "invoices": invoices_list  # Will be [] if none
            })

        return ProjectServiceResponse(
            data=data,
            message="POs fetched successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        logger.error(f"Error in list_all_pos API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching POs."
        ).model_dump()

@project_router.put(
    "/{project_id}/pos/{po_id}",
    tags=["Project POs"],
    description="Update an existing Purchase Order (PO) under a project. File update is not allowed."
)
def update_project_po(
    po_id: UUID,
    po_data: ProjectPOUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        po = db.query(ProjectPO).filter(
            ProjectPO.uuid == po_id,
            ProjectPO.is_deleted.is_(False)
        ).first()

        if not po:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="PO not found under this project"
            ).model_dump()

        # Update fields
        po.po_number = po_data.po_number or po.po_number
        po.amount = po_data.amount or po.amount
        po.client_name = po_data.client_name or po.client_name
        po.description = po_data.description or po.description

        if po_data.po_date:
            try:
                po.po_date = datetime.strptime(po_data.po_date, "%Y-%m-%d").date()
            except ValueError:
                return ProjectServiceResponse(
                    data=None,
                    status_code=400,
                    message="Invalid date format. Use YYYY-MM-DD"
                ).model_dump()

        #  Update PO items
        db.query(ProjectPOItem).filter(ProjectPOItem.project_po_id == po_id).delete()
        for item in po_data.items:
            db.add(ProjectPOItem(
                project_po_id=po_id,
                item_name=item.item_name,
                basic_value=item.basic_value
            ))

        db.commit()
        db.refresh(po)

        return ProjectServiceResponse(
            data={
                "uuid": str(po.uuid),
                "po_number": po.po_number,
                "client_name": po.client_name,
                "amount": po.amount,
                "description": po.description,
                "po_date": po.po_date.strftime("%Y-%m-%d") if po.po_date else None,
                "items": [
                    {
                        "item_name": item.item_name,
                        "basic_value": item.basic_value
                    } for item in po.po_items
                ] if hasattr(po, "po_items") else []
            },
            message="PO updated successfully",
            status_code=200
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
    "/project/po/{po_id}",
    tags=["Project POs"],
    description="Delete a project PO",
)

def delete_project_po(
    po_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a PO by its ID."""
    # Fetch PO
    po = db.query(ProjectPO).filter(ProjectPO.uuid == po_id).first()

    if not po:
        logger.warning(f"[{po.po_number}] delete failed - po not found")
        return ProjectServiceResponse(
            data=None,
            status_code=404,
            message="PO not found"
        ).model_dump()

    # Authorization check
    user_role = getattr(current_user, "role", None) or current_user.get("role")
    if user_role not in [
        UserRole.SUPER_ADMIN.value,
        UserRole.ADMIN.value,
        UserRole.PROJECT_MANAGER.value,
    ]:
        logger.warning(f"[{current_user.name}] not authorized to delete PO")
        return ProjectServiceResponse(
            data=None,
            status_code=403,
            message="You are not authorized to delete this PO"
        ).model_dump()

    try:
        db.delete(po)
        db.commit()
        logger.info(f"[{current_user.name}]: po delete [{po.po_number}]")
        
        return ProjectServiceResponse(
            data={"uuid": str(po_id)},
            message="PO deleted successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            message=f"An error occurred while deleting PO: {str(e)}",
            status_code=500
        ).model_dump()
    

 
@project_router.get(
    "/project-item-view/{project_id}/{user_id}",
    tags=["Mappings"],
    description="Get items visible to current user under a specific project."
)
def view_project_items_for_user(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        # Show all unique items assigned to the project
        # Use subquery to handle potential duplicates
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
            db.query(ProjectItemMap)
            .join(subquery, ProjectItemMap.id == subquery.c.max_id)
            .join(Item, ProjectItemMap.item_id == Item.uuid)
            .all()
        )
        response = [
            {
                "uuid": m.item.uuid,
                "name": m.item.name if m.item else None,
                "category": m.item.category if m.item else None,
                "listTag": m.item.list_tag if m.item else None,
                "has_additional_info": m.item.has_additional_info if m.item else None,
                "item_balance": m.item_balance,
                "remaining_balance": None
            }
            for m in project_items
        ]
    else:
        # Show only items mapped to this user
        # Query both ProjectUserItemMap and ProjectItemMap to get item_balance
        project_items = (
            db.query(ProjectUserItemMap, ProjectItemMap)
            .join(Item, ProjectUserItemMap.item_id == Item.uuid)
            .join(ProjectItemMap, and_(
                ProjectUserItemMap.item_id == ProjectItemMap.item_id,
                ProjectUserItemMap.project_id == ProjectItemMap.project_id
            ))
            .filter(
                ProjectUserItemMap.project_id == project_id,
                ProjectUserItemMap.user_id == user_id
            )
            .all()
        )
        response = [
            {
                "uuid": user_item_map.item.uuid,
                "name": user_item_map.item.name if user_item_map.item else None,
                "category": user_item_map.item.category if user_item_map.item else None,
                "listTag": user_item_map.item.list_tag if user_item_map.item else None,
                "has_additional_info": user_item_map.item.has_additional_info if user_item_map.item else None,
                "item_balance": project_item_map.item_balance,
                "remaining_balance": None
            }
            for user_item_map, project_item_map in project_items
        ]
    return ProjectServiceResponse(
        data=response,
        message="Project User Items Fetched Successfully.",
        status_code=200
    ).model_dump()

@project_router.get(
        "/states",
        tags=["Location"],
        description="Get a list of all Indian states", 
    )
def get_all_states(current_user: User = Depends(get_current_user)):
    states = list(LocationService._INDIA_STATES_CITIES.keys())
    return {
        "data": states,
        "message": "List of Indian States fetched successfully.",
        "status_code": 200
    }

@project_router.get(
        "/cities", 
        tags=["Location"],
        description="Get a list of cities for a given state",
    )
def get_cities_by_state(state: str = Query(..., description="State name to get cities for"),current_user: User = Depends(get_current_user)):
    normalized_state = state.strip().lower()
    matched_state = None

    for key in LocationService._INDIA_STATES_CITIES:
        if key.lower() == normalized_state:
            matched_state = key
            break

    if not matched_state:
        raise HTTPException(status_code=404, detail="State not found")

    return {
        "data": LocationService._INDIA_STATES_CITIES[matched_state],
        "message": f"Cities fetched for {matched_state.title()}",
        "status_code": 200
    }

@project_router.post(
    "/company-info",
    status_code=status.HTTP_201_CREATED,
    tags=["Company Info"],
    description="""
Create a new Company Info entry.

Send the `company_data` JSON string via form and optionally upload a logo file.

**Example `company_data` JSON**:
```json
{
  "years_of_experience": 5,
  "no_of_staff": 30,
  "user_construction": "Industrial",
  "successfull_installations": "150+ installations"
}
"""
)
def create_company_info(
    company_data: str = Form(..., description="JSON string with company info"),
    logo_photo_file: Optional[UploadFile] = File(None, description="Company logo file"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        # Role check
        user_role = getattr(current_user, "role", None) or current_user.get("role")
        if user_role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            return ProjectServiceResponse(
            status_code=403,
            message="Unauthorized to create company info"
            ).model_dump()

        # Parse JSON
        try:
            payload_dict = json.loads(company_data)
            payload = CompanyInfoCreate(**payload_dict)
        except Exception as e:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message=f"Invalid JSON: {str(e)}"
            ).model_dump()

        # Save logo file if present
        file_path = None
        if logo_photo_file:
            ext = os.path.splitext(logo_photo_file.filename)[1]
            filename = f"logo_{str(uuid4())}{ext}"
            upload_dir = "uploads/company_logos"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(logo_photo_file.file.read())

        # Create CompanyInfo
        company = CompanyInfo(
            years_of_experience=payload.years_of_experience,
            no_of_staff=payload.no_of_staff,
            user_construction=payload.user_construction,
            successfull_installations=payload.successfull_installations,
            logo_photo_url=file_path,  # same as file_path, not full URL
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        return ProjectServiceResponse(
            data={
                "uuid": str(company.uuid),
                "years_of_experience": company.years_of_experience,
                "no_of_staff": company.no_of_staff,
                "user_construction": company.user_construction,
                "successfull_installations": company.successfull_installations,
                "logo_photo_path": company.logo_photo_url
            },
            status_code=201,
            message="Company info created successfully"
        ).model_dump()

    except Exception as e:
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"Error while creating company info: {str(e)}"
        ).model_dump()

@project_router.get(
    "/company-info",
    tags=["Company Info"],
    response_model=dict,
    summary="Get all company info records",
    description="Fetches all company info entries including logo URL"
)
def get_all_company_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        companies = db.query(CompanyInfo).filter().all()

        data = [
            {
                "uuid": str(c.uuid),
                "years_of_experience": c.years_of_experience,
                "no_of_staff": c.no_of_staff,
                "user_construction": c.user_construction,
                "successfull_installations": c.successfull_installations,
                "logo_photo_url": f"{constants.HOST_URL}/{c.logo_photo_url}" if c.logo_photo_url else None
            } for c in companies
        ]

        return ProjectServiceResponse(
            data=data,
            status_code=200,
            message="Company info records fetched successfully"
        ).model_dump()

    except Exception as e:
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching records: {str(e)}"
        ).model_dump()


@project_router.get(
    "/company-info/{uuid}",
    tags=["Company Info"],
    response_model=dict,
    summary="Get single company info by UUID",
    description="Fetch a specific company info entry",
    deprecated=True
)
def get_company_info_by_uuid(
    uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        company = db.query(CompanyInfo).filter(
            CompanyInfo.uuid == uuid
        ).first()

        if not company:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Company info not found"
            ).model_dump()

        data = {
            "uuid": str(company.uuid),
            "years_of_experience": company.years_of_experience,
            "no_of_staff": company.no_of_staff,
            "user_construction": company.user_construction,
            "successfull_installations": company.successfull_installations,
            "logo_photo_url": company.logo_photo_url
        }

        return ProjectServiceResponse(
            data=data,
            status_code=200,
            message="Company info fetched successfully"
        ).model_dump()

    except Exception as e:
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching company info: {str(e)}"
        ).model_dump()

@project_router.put(
    "/company-info/{uuid}",
    status_code=status.HTTP_200_OK,
    tags=["Company Info"],
    response_model=dict,
    description="""
Update an existing Company Info entry and optionally replace the logo/document.

Send as `multipart/form-data`:
- `company_data`: JSON string with updated fields.
- `logo_photo_file`: (Optional) new file to replace the existing logo.

**Example `company_data` JSON**:
```json
{
  "years_of_experience": 20,
  "no_of_staff": 50,
  "user_construction": "Industrial",
  "successfull_installations": "500+ successful projects"
}
"""
)
def update_company_info(
    uuid: UUID,
    company_data: str = Form(..., description="Updated JSON data"),
    logo_photo_file: Optional[UploadFile] = File(None, description="New logo or document"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        # Role check
        user_role = getattr(current_user, "role", None) or current_user.get("role")
        if user_role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            return ProjectServiceResponse(
            status_code=403,
            message="Unauthorized to update company info"
            ).model_dump()

        # Fetch company record
        company = db.query(CompanyInfo).filter(CompanyInfo.uuid == uuid).first()
        if not company:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Company info not found"
            ).model_dump()

        # Parse JSON
        try:
            payload_dict = json.loads(company_data)
            payload = CompanyInfoUpdate(**payload_dict)
        except Exception as e:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message=f"Invalid JSON: {str(e)}"
            ).model_dump()

        # Save new logo if provided
        if logo_photo_file:
            upload_dir = "uploads/company_logos"
            os.makedirs(upload_dir, exist_ok=True)
            ext = os.path.splitext(logo_photo_file.filename)[1]
            filename = f"logo_{str(uuid4())}{ext}"
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(logo_photo_file.file.read())
            company.logo_photo_url = file_path  # just store relative path

        # Update fields if present
        if payload.years_of_experience is not None:
            company.years_of_experience = payload.years_of_experience
        if payload.no_of_staff is not None:
            company.no_of_staff = payload.no_of_staff
        if payload.user_construction is not None:
            company.user_construction = payload.user_construction
        if payload.successfull_installations is not None:
            company.successfull_installations = payload.successfull_installations

        db.commit()
        db.refresh(company)

        return ProjectServiceResponse(
            data={
                "uuid": str(company.uuid),
                "years_of_experience": company.years_of_experience,
                "no_of_staff": company.no_of_staff,
                "user_construction": company.user_construction,
                "successfull_installations": company.successfull_installations,
                "logo_photo_path": company.logo_photo_url
            },
            status_code=200,
            message="Company info updated successfully"
        ).model_dump()

    except Exception as e:
        db.rollback()
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"Error while updating company info: {str(e)}"
        ).model_dump()
    

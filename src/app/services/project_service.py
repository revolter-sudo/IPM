import logging
from uuid import UUID, uuid4
from typing import Optional,List
from fastapi import APIRouter, Depends, HTTPException, status
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
    ProjectItemMap
)
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.project_service_schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectServiceResponse,
    UpdateProjectSchema,
    BankCreateSchema,
    BankEditSchema
)
from src.app.services.auth_service import get_current_user

project_router = APIRouter(prefix="/projects")

balance_router = APIRouter(prefix="")


def create_project_balance_entry(
    db, current_user, project_id: UUID, adjustment: float, description: str = None
):
    balance_entry = ProjectBalance(
        project_id=project_id, adjustment=adjustment, description=description
    )
    db.add(balance_entry)
    log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Deactivate",
            entity_id=project_id,
            performed_by=current_user.uuid,
        )
    db.add(log_entry)
    db.commit()
    db.refresh(balance_entry)


@project_router.put("/update-balance", tags=["Projects"])
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


@project_router.put("/adjust-balance", tags=["Projects"])
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
    "/create", status_code=status.HTTP_201_CREATED, tags=["Projects"]
)
def create_project(
    request: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logging.info(f"Create project request received: {request}")
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
        initial_balance = (
            request.balance if request.balance is not None else 0.0
        )

        new_project = Project(
            uuid=project_uuid,
            name=request.name,
            description=request.description,
            location=request.location,
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        # Initialize project balance with the given amount or default to 0.0
        create_project_balance_entry(
            db=db,
            project_id=new_project.uuid,
            adjustment=initial_balance,
            description="Initial project balance",
            current_user=current_user
        )

        # Create a log entry for project creation
        db.commit()
        return ProjectServiceResponse(
            data=None,
            message="Project Created Successfully",
            status_code=201
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in create_project API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching project details"
        ).model_dump()


@project_router.get("", status_code=status.HTTP_200_OK, tags=["Projects"])
def list_all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # If user is admin or super admin, return all projects
        if current_user.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            projects_data = (
                db.query(Project).filter(Project.is_deleted.is_(False)).all()
            )
        else:
            # Filter projects where user is mapped in ProjectUserMap
            projects_data = (
                db.query(Project)
                .join(ProjectUserMap, Project.uuid == ProjectUserMap.project_id)
                .filter(
                    Project.is_deleted.is_(False),
                    ProjectUserMap.user_id == current_user.uuid,
                )
                .all()
            )

        projects_response_data = []
        for project in projects_data:
            total_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(ProjectBalance.project_id == project.uuid)
                .scalar()
            ) or 0.0

            # Fetch items related to the project
            items = (
                db.query(Item)
                .join(ProjectItemMap, Item.uuid == ProjectItemMap.item_id)
                .filter(ProjectItemMap.project_id == project.uuid)
                .all()
            )

            item_responses = []
            for item in items:
                item_responses.append(
                    {
                        "uuid": item.uuid,
                        "name": item.name,
                        "category": item.category,
                        "list_tag": item.list_tag,
                        "has_additional_info": item.has_additional_info,
                    }
                )

            projects_response_data.append(
                {
                    "uuid": project.uuid,
                    "name": project.name,
                    "description": project.description,
                    "location": project.location,
                    "balance": total_balance,
                    "items": item_responses,
                }
            )
        return ProjectServiceResponse(
            data=projects_response_data,
            message="Projects data fetched successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in list_all_projects API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while fetching project details"
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

        total_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(ProjectBalance.project_id == project_uuid)
            .scalar()
        ) or 0.0

        project_response_data = ProjectResponse(
            uuid=project.uuid,
            description=project.description,
            name=project.name,
            location=project.location,
            balance=total_balance,
        ).to_dict()
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
            message="An error occurred while fetching project details"
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

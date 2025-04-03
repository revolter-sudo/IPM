import logging
from uuid import UUID, uuid4

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
    Payment
)
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.project_service_schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectServiceResponse
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
        if current_user.role not in [
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
def list_all_projects(db: Session = Depends(get_db)):
    try:
        projects_data = (
            db.query(Project).filter(Project.is_deleted.is_(False)).all()
        )

        projects_response_data = []
        for project in projects_data:
            total_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(ProjectBalance.project_id == project.uuid)
                .scalar()
            ) or 0.0

            projects_response_data.append(
                ProjectResponse(
                    uuid=project.uuid,
                    name=project.name,
                    description=project.description,
                    location=project.location,
                    balance=total_balance,
                ).to_dict()
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


@balance_router.post(
    "/create-balance",
    tags=["Bank Balance"]
)
def create_balance(
    balance_amount: Decimal,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        logging.info(f"Initial Balance: {balance_amount}")
        if user.role not in [
            UserRole.ACCOUNTANT.value,
            UserRole.SUPER_ADMIN.value
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=400,
                message="Only Accountant or Super Admin can update Balance"
            ).model_dump()
        balance_obj = db.query(BalanceDetail).first()
        if balance_obj:
            logging.info(f"Balance amount existing case: {balance_amount}")
            balance_obj.balance = balance_amount
        else:
            logging.info(f"Balance amount not fount case: {balance_amount}")
            balance_obj = BalanceDetail(balance=balance_amount)
            db.add(balance_obj)
        db.commit()
        db.refresh(balance_obj)
        return ProjectServiceResponse(
            data=balance_obj,
            status_code=201,
            message="Balance Updated Successfully"
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in create_balance API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while creating balance"
        ).model_dump()


def get_total_transferred_payments_sum(db):
    total_sum = db.query(func.sum(Payment.amount))\
                  .filter(Payment.status == 'transferred', Payment.is_deleted.is_(False))\
                  .scalar()
    if total_sum:
        return total_sum
    else:
        return 0.0


@balance_router.get(
    "/balance",
    tags=["Bank Balance"]
)
def get_bank_balance(
    db: Session = Depends(get_db)
):
    try:
        balance_obj = db.query(BalanceDetail).first()
        balance = balance_obj.balance
        logging.info(f"Balance before subtraction: {balance}")
        if not balance_obj:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Balance Not Found"
            ).model_dump()
        recorded_balance = get_total_transferred_payments_sum(db=db)
        logging.info(f"Total records: {balance}")
        remaining_balance = balance - recorded_balance
        result = {"balance": remaining_balance}
        logging.info(f"Remaining Balance: {balance}")
        return ProjectServiceResponse(
            data=result,
            status_code=200,
            message="Balance Fetched Successfully."
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_bank_balance API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message="An error occurred while getting balance"
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

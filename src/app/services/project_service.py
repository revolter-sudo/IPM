import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from src.app.database.database import get_db
from src.app.database.models import Log, Project, ProjectBalance, User
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.project_service_schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectServiceResponse
)
from src.app.services.auth_service import get_current_user

project_router = APIRouter(prefix="/projects")


def create_project_balance_entry(
    db, project_id: UUID, adjustment: float, description: str = None
):
    balance_entry = ProjectBalance(
        project_id=project_id, adjustment=adjustment, description=description
    )
    db.add(balance_entry)
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
            raise HTTPException(
                status_code=404, detail="Project balance not found"
            )

        # Update project balance
        project_balance.adjustment = new_balance
        db.commit()

        total_balance = (
            db.query(func.sum(ProjectBalance.adjustment))
            .filter(ProjectBalance.project_id == project_uuid)
            .scalar()
        ) or 0.0
        return ProjectServiceResponse(
            data=total_balance,
            message="Project balance updated successfully"
        ).model_dump()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


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
            message="Project balance fetched successfully."
        ).model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


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
            raise HTTPException(status_code=404, detail="Project not found")

        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
        ]:
            raise HTTPException(
                status_code=403, detail="Unauthorized to adjust balance"
            )

        create_project_balance_entry(db, project_uuid, adjustment, description)
        return ProjectServiceResponse(
            data=None,
            message="Project balance adjusted successfully"
        ).model_dump()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=constants.CAN_NOT_CREATE_PROJECT,
            )

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
            data=None,
            message="Project Created Successfully"
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in create_project API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the project",
        )


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
            message="Projects data fetched successfully."
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in list_all_projects API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching projects",
        )


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
            raise HTTPException(
                status_code=404, detail=constants.PROJECT_NOT_FOUND
            )

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
            message="Project info fetched successfully."
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_project_info API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching project details",
        )

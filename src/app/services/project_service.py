import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.app.database.database import get_db
from src.app.database.models import Log, Project, User
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.project_service_schemas import (
    ProjectCreateRequest,
    ProjectResponse,
)
from src.app.services.auth_service import get_current_user

project_router = APIRouter(prefix="/projects")


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
        new_project = Project(
            uuid=project_uuid,
            name=request.name,
            description=request.description,
            location=request.location,
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        log_entry = Log(
            uuid=str(uuid4()),
            entity="Project",
            action="Create",
            entity_id=project_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()

        return {"result": "Project Created Successfully"}
    except Exception as e:
        logging.info(f"Error in create_project API: {str(e)}")
        raise e


@project_router.get("/", status_code=status.HTTP_200_OK, tags=["Projects"])
def list_all_projects(db: Session = Depends(get_db)):
    try:
        projects_data = (
            db.query(Project).filter(Project.is_deleted.is_(False)).all()
        )
        projects_response_data = [
            ProjectResponse(
                uuid=project.uuid,
                name=project.name,
                description=project.description,
                location=project.location,
            ).to_dict()
            for project in projects_data
        ]
        return {"result": projects_response_data}
    except Exception as e:
        logging.info(f"Error in list_all_projects API: {str(e)}")
        raise e


@project_router.get(
    "/{project_uuid}", status_code=status.HTTP_200_OK, tags=["Projects"]
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
        project_response_data = ProjectResponse(
            uuid=project.uuid,
            description=project.description,
            name=project.name,
            location=project.location,
        ).to_dict()

        return {"result": project_response_data}
    except Exception as e:
        logging.info(f"Error in get_project_info API: {str(e)}")
        raise e

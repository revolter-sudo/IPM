import os
import traceback
from fastapi import FastAPI, Body, HTTPException
from fastapi_sqlalchemy import DBSessionMiddleware
from src.app.database.database import settings
from src.app.services.auth_service import get_current_user
from src.app.schemas.auth_service_schamas import UserRole
from src.app.admin_panel.services import create_project_user_mapping
from src.app.schemas.project_service_schemas import ProjectServiceResponse
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
    Form
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
    ProjectItemMap
)
from sqlalchemy.orm import Session
from src.app.admin_panel.services import get_default_config_service, create_project_item_mapping
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
            total_balance = (
                db.query(func.sum(ProjectBalance.adjustment))
                .filter(ProjectBalance.project_id == project.uuid)
                .scalar()
            ) or 0.0

            project_response.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
                "balance": total_balance
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

            projects_list.append({
                "uuid": str(project.uuid),
                "name": project.name,
                "description": project.description,
                "location": project.location,
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
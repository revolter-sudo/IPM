from src.app.database.models import Item,ProjectUserMap, ProjectItemMap
from uuid import UUID, uuid4
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.app.database.database import SessionLocal
from src.app.admin_panel import constants
from sqlalchemy import func



def get_default_config_service() -> dict:
    db: Session = SessionLocal()
    item_data = (
        db.query(Item)
        .filter(func.lower(Item.name) == "site expense")
        .first()
    )

    if not item_data:
        response = {
            "admin_amount": constants.ACCOUNTANT_LIMIT
        }
    else:
        response = {
            "item": {
                "name": item_data.name,
                "uuid": item_data.uuid,
                "category": item_data.category,
                "list_tag": item_data.list_tag,
                "has_addition_info": item_data.has_additional_info
            },
            "admin_amount": constants.ACCOUNTANT_LIMIT
        }
    return response


def create_project_user_mapping(
    db: Session, user_id: UUID, project_id: UUID
):
    # Check if mapping already exists
    existing_mapping = db.query(ProjectUserMap).filter(
        ProjectUserMap.user_id == user_id,
        ProjectUserMap.project_id == project_id
    ).first()
    if existing_mapping:
        return existing_mapping

    project_user_mapping = ProjectUserMap(
        uuid=str(uuid4()),
        user_id=user_id,
        project_id=project_id,
    )
    db.add(project_user_mapping)
    db.commit()
    db.refresh(project_user_mapping)
    return project_user_mapping

def create_project_item_mapping(
    db: Session, item_id: UUID, project_id: UUID
):

    # Check if mapping already exists
    existing_mapping = db.query(ProjectItemMap).filter(
        ProjectItemMap.item_id == item_id,
        ProjectItemMap.project_id == project_id
    ).first()
    if existing_mapping:
        return existing_mapping

    project_item_mapping = ProjectItemMap(
        uuid=str(uuid4()),
        item_id=item_id,
        project_id=project_id,
    )
    db.add(project_item_mapping)
    db.commit()
    db.refresh(project_item_mapping)
    return project_item_mapping
from src.app.database.models import Item, ProjectUserMap, ProjectItemMap, UserItemMap, DefaultConfig
from uuid import UUID, uuid4
from typing import Optional, List
from sqlalchemy.orm import Session
from src.app.database.database import SessionLocal
from src.app.admin_panel import constants
from sqlalchemy import func
from datetime import datetime


def get_default_config_service() -> dict:
    """
    Get the default configuration from the DefaultConfig table.
    If no configuration exists, use the default values from constants.
    """
    db: Session = SessionLocal()

    # Get the first default config entry that is not deleted
    default_config = (
        db.query(DefaultConfig)
        .filter(DefaultConfig.is_deleted.is_(False))
        .order_by(DefaultConfig.created_at.desc())
        .first()
    )

    if not default_config:
        # If no default config exists, use the old behavior as fallback
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
    else:
        # Get the item data from the item_id in default_config
        item_data = db.query(Item).filter(Item.uuid == default_config.item_id).first()

        if not item_data:
            response = {
                "admin_amount": default_config.admin_amount
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
                "admin_amount": default_config.admin_amount
            }

    db.close()
    return response


def create_default_config_service(item_id: UUID, admin_amount: float) -> DefaultConfig:
    """
    Create a new default configuration.
    If a default config already exists, mark it as deleted before creating a new one.
    """
    db: Session = SessionLocal()

    try:
        # Mark all existing default configs as deleted
        existing_configs = db.query(DefaultConfig).filter(DefaultConfig.is_deleted.is_(False)).all()
        for config in existing_configs:
            config.is_deleted = True

        # Create a new default config
        new_config = DefaultConfig(
            item_id=item_id,
            admin_amount=admin_amount
        )

        db.add(new_config)
        db.commit()
        db.refresh(new_config)

        return new_config
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def update_default_config_service(item_id: UUID, admin_amount: float) -> DefaultConfig:
    """
    Update the default configuration by creating a new entry and marking the old one as deleted.
    """
    return create_default_config_service(item_id, admin_amount)


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
    db: Session, item_id: UUID, project_id: UUID, item_balance: Optional[float] = None
):
    # Check if mapping already exists
    existing_mapping = db.query(ProjectItemMap).filter(
        ProjectItemMap.item_id == item_id,
        ProjectItemMap.project_id == project_id
    ).first()
    if existing_mapping:
        if item_balance is not None:  # Only update balance if provided
            existing_mapping.item_balance = item_balance
            db.commit()
            db.refresh(existing_mapping)
        return existing_mapping

    project_item_mapping = ProjectItemMap(
        uuid=str(uuid4()),
        item_id=item_id,
        project_id=project_id,
        item_balance=item_balance  # Will be None if not provided
    )
    db.add(project_item_mapping)
    db.commit()
    db.refresh(project_item_mapping)
    return project_item_mapping


def create_multiple_project_item_mappings(
    db: Session, item_ids: List[UUID], project_id: UUID, item_balances: Optional[List[float]] = None
):
    """
    Map multiple items to a project at once.

    Args:
        db: Database session
        item_ids: List of item UUIDs to map
        project_id: Project UUID to map items to
        item_balances: Optional list of balances for each item (must match length of item_ids)

    Returns:
        List of created or updated ProjectItemMap objects
    """
    if item_balances and len(item_ids) != len(item_balances):
        raise ValueError("item_ids and item_balances must have the same length")

    mappings = []

    for i, item_id in enumerate(item_ids):
        balance = item_balances[i] if item_balances else None

        # Check if mapping already exists
        existing_mapping = db.query(ProjectItemMap).filter(
            ProjectItemMap.item_id == item_id,
            ProjectItemMap.project_id == project_id
        ).first()

        if existing_mapping:
            if balance is not None:  # Only update balance if provided
                existing_mapping.item_balance = balance
            mappings.append(existing_mapping)
        else:
            # Create new mapping
            new_mapping = ProjectItemMap(
                uuid=str(uuid4()),
                item_id=item_id,
                project_id=project_id,
                item_balance=balance
            )
            db.add(new_mapping)
            mappings.append(new_mapping)

    db.commit()

    # Refresh all mappings
    for mapping in mappings:
        db.refresh(mapping)

    return mappings


def create_user_item_mapping(
    db: Session, user_id: UUID, item_id: UUID, item_balance: Optional[float] = None
):
    # Check if mapping already exists
    existing_mapping = db.query(UserItemMap).filter(
        UserItemMap.user_id == user_id,
        UserItemMap.item_id == item_id
    ).first()
    if existing_mapping:
        if item_balance is not None:  # Only update balance if provided
            existing_mapping.item_balance = item_balance
            db.commit()
            db.refresh(existing_mapping)
        return existing_mapping

    user_item_mapping = UserItemMap(
        uuid=str(uuid4()),
        user_id=user_id,
        item_id=item_id,
        item_balance=item_balance  # Will be None if not provided
    )
    db.add(user_item_mapping)
    db.commit()
    db.refresh(user_item_mapping)
    return user_item_mapping


def create_multiple_user_item_mappings(
    db: Session, user_id: UUID, item_ids: List[UUID], item_balances: Optional[List[float]] = None
):
    """
    Map multiple items to a user at once.

    Args:
        db: Database session
        user_id: User UUID to map items to
        item_ids: List of item UUIDs to map
        item_balances: Optional list of balances for each item (must match length of item_ids)

    Returns:
        List of created or updated UserItemMap objects
    """
    if item_balances and len(item_ids) != len(item_balances):
        raise ValueError("item_ids and item_balances must have the same length")

    mappings = []

    for i, item_id in enumerate(item_ids):
        balance = item_balances[i] if item_balances else None

        # Check if mapping already exists
        existing_mapping = db.query(UserItemMap).filter(
            UserItemMap.user_id == user_id,
            UserItemMap.item_id == item_id
        ).first()

        if existing_mapping:
            if balance is not None:  # Only update balance if provided
                existing_mapping.item_balance = balance
            mappings.append(existing_mapping)
        else:
            # Create new mapping
            new_mapping = UserItemMap(
                uuid=str(uuid4()),
                user_id=user_id,
                item_id=item_id,
                item_balance=balance
            )
            db.add(new_mapping)
            mappings.append(new_mapping)

    db.commit()

    # Refresh all mappings
    for mapping in mappings:
        db.refresh(mapping)

    return mappings


def create_multiple_project_user_mappings(
    db: Session, project_id: UUID, user_ids: List[UUID]
):
    """
    Map multiple users to a project at once.

    Args:
        db: Database session
        project_id: Project UUID to map users to
        user_ids: List of user UUIDs to map

    Returns:
        List of created ProjectUserMap objects
    """
    mappings = []

    for user_id in user_ids:
        # Check if mapping already exists
        existing_mapping = db.query(ProjectUserMap).filter(
            ProjectUserMap.user_id == user_id,
            ProjectUserMap.project_id == project_id
        ).first()

        if existing_mapping:
            mappings.append(existing_mapping)
        else:
            # Create new mapping
            new_mapping = ProjectUserMap(
                uuid=str(uuid4()),
                user_id=user_id,
                project_id=project_id
            )
            db.add(new_mapping)
            mappings.append(new_mapping)

    db.commit()

    # Refresh all mappings
    for mapping in mappings:
        db.refresh(mapping)

    return mappings


def remove_project_item_mapping(db: Session, item_id: UUID, project_id: UUID):
    """
    Remove an item mapping from a project.

    Args:
        db: Database session
        item_id: Item UUID to remove
        project_id: Project UUID to remove item from

    Returns:
        True if mapping was removed, False if mapping didn't exist
    """
    mapping = db.query(ProjectItemMap).filter(
        ProjectItemMap.item_id == item_id,
        ProjectItemMap.project_id == project_id
    ).first()

    if not mapping:
        return False

    db.delete(mapping)
    db.commit()
    return True


def remove_project_user_mapping(db: Session, user_id: UUID, project_id: UUID):
    """
    Remove a user mapping from a project.

    Args:
        db: Database session
        user_id: User UUID to remove
        project_id: Project UUID to remove user from

    Returns:
        True if mapping was removed, False if mapping didn't exist
    """
    mapping = db.query(ProjectUserMap).filter(
        ProjectUserMap.user_id == user_id,
        ProjectUserMap.project_id == project_id
    ).first()

    if not mapping:
        return False

    db.delete(mapping)
    db.commit()
    return True


def remove_user_item_mapping(db: Session, user_id: UUID, item_id: UUID):
    """
    Remove an item mapping from a user.

    Args:
        db: Database session
        user_id: User UUID to remove item from
        item_id: Item UUID to remove

    Returns:
        True if mapping was removed, False if mapping didn't exist
    """
    mapping = db.query(UserItemMap).filter(
        UserItemMap.user_id == user_id,
        UserItemMap.item_id == item_id
    ).first()

    if not mapping:
        return False

    db.delete(mapping)
    db.commit()
    return True
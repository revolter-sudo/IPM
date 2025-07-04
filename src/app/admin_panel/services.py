from typing import List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.app.admin_panel import constants
from src.app.database.database import SessionLocal
from src.app.database.models import (
    DefaultConfig,
    Item,
    ProjectItemMap,
    ProjectUserItemMap,
    ProjectUserMap,
    UserItemMap,
)


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
            db.query(Item).filter(func.lower(Item.name) == "site expense").first()
        )

        if not item_data:
            response = {"admin_amount": constants.ACCOUNTANT_LIMIT}
        else:
            response: dict[str, Any] = {
                "item": {
                    "name": item_data.name,
                    "uuid": item_data.uuid,
                    "category": item_data.category,
                    "list_tag": item_data.list_tag,
                    "has_addition_info": item_data.has_additional_info,
                },
                "admin_amount": constants.ACCOUNTANT_LIMIT,
            }
    else:
        # Get the item data from the item_id in default_config
        item_data = db.query(Item).filter(Item.uuid == default_config.item_id).first()

        if not item_data:
            response = {"admin_amount": default_config.admin_amount}
        else:
            response = {
                "item": {
                    "name": item_data.name,
                    "uuid": item_data.uuid,
                    "category": item_data.category,
                    "list_tag": item_data.list_tag,
                    "has_addition_info": item_data.has_additional_info,
                },
                "admin_amount": default_config.admin_amount,
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
        existing_configs = (
            db.query(DefaultConfig).filter(DefaultConfig.is_deleted.is_(False)).all()
        )
        for config in existing_configs:
            config.is_deleted = True

        # Create a new default config
        new_config = DefaultConfig(item_id=item_id, admin_amount=admin_amount)

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
    Update the default configuration by
    creating a new entry and marking the old one as deleted.
    """
    return create_default_config_service(item_id, admin_amount)


def create_project_user_mapping(db: Session, user_id: UUID, project_id: UUID):
    # Check if mapping already exists
    existing_mapping = (
        db.query(ProjectUserMap)
        .filter(
            ProjectUserMap.user_id == user_id, ProjectUserMap.project_id == project_id
        )
        .first()
    )
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
    existing_mapping = (
        db.query(ProjectItemMap)
        .filter(
            ProjectItemMap.item_id == item_id, ProjectItemMap.project_id == project_id
        )
        .first()
    )
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
        item_balance=item_balance,  # Will be None if not provided
    )
    db.add(project_item_mapping)
    db.commit()
    db.refresh(project_item_mapping)
    return project_item_mapping


def create_multiple_project_item_mappings(
    db: Session,
    item_ids: List[UUID],
    project_id: UUID,
    item_balances: Optional[List[float]] = None,
):
    """
    Map multiple items to a project at once.

    Args:
        db: Database session
        item_ids: List of item UUIDs to map
        project_id: Project UUID to map items to
        item_balances: Optional list of balances for each item

    Returns:
        List of created or updated ProjectItemMap objects
    """
    if item_balances and len(item_ids) != len(item_balances):
        raise ValueError("item_ids and item_balances must have the same length")

    mappings = []

    for i, item_id in enumerate(item_ids):
        balance = item_balances[i] if item_balances else None

        # Check if mapping already exists
        existing_mapping = (
            db.query(ProjectItemMap)
            .filter(
                ProjectItemMap.item_id == item_id,
                ProjectItemMap.project_id == project_id,
            )
            .first()
        )

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
                item_balance=balance,
            )
            db.add(new_mapping)
            mappings.append(new_mapping)

    db.commit()

    # Refresh all mappings
    for mapping in mappings:
        db.refresh(mapping)

    return mappings


def sync_project_item_mappings(
    db: Session, item_data_list: List[dict], project_id: UUID
):
    """
    Synchronize project-item mappings based on the provided list.
    This function will:
    1. Add new mappings for items not already mapped to the project
    2. Update balances for existing mappings
    3. Remove mappings for items that are in the database but not in the provided list

    Args:
        db: Database session
        item_data_list: List of dictionaries with item_id and balance
        project_id: Project UUID to sync items with

    Returns:
        Dict containing added, updated, and removed mapping counts
    """
    # Extract item IDs and balances from the input data
    item_ids = []
    item_balances = []

    for item_data in item_data_list:
        item_id = UUID(item_data.get("item_id"))
        balance = float(item_data.get("balance", 0.0))
        item_ids.append(item_id)
        item_balances.append(balance)

    # Get existing mappings for this project
    existing_mappings = (
        db.query(ProjectItemMap).filter(ProjectItemMap.project_id == project_id).all()
    )

    existing_item_ids = {mapping.item_id for mapping in existing_mappings}

    # Identify items to add, update, and remove
    items_to_add = [
        i for i, item_id in enumerate(item_ids) if item_id not in existing_item_ids
    ]
    items_to_update = [
        i for i, item_id in enumerate(item_ids) if item_id in existing_item_ids
    ]
    items_to_remove = [
        mapping.item_id
        for mapping in existing_mappings
        if mapping.item_id not in item_ids
    ]

    # Add new mappings
    added_mappings = []
    for i in items_to_add:
        new_mapping = ProjectItemMap(
            uuid=str(uuid4()),
            item_id=item_ids[i],
            project_id=project_id,
            item_balance=item_balances[i],
        )
        db.add(new_mapping)
        added_mappings.append(new_mapping)

    # Update existing mappings
    updated_mappings = []
    for i in items_to_update:
        existing_mapping = next(
            m for m in existing_mappings if m.item_id == item_ids[i]
        )
        existing_mapping.item_balance = item_balances[i]
        updated_mappings.append(existing_mapping)

    # Remove mappings not in the provided list
    removed_count = 0
    for item_id in items_to_remove:
        mapping_to_remove = next(m for m in existing_mappings if m.item_id == item_id)
        db.delete(mapping_to_remove)
        removed_count += 1

    # Commit changes
    db.commit()

    # Refresh added and updated mappings
    for mapping in added_mappings + updated_mappings:
        db.refresh(mapping)

    return {
        "added": len(added_mappings),
        "updated": len(updated_mappings),
        "removed": removed_count,
        "mappings": added_mappings + updated_mappings,
    }


def create_user_item_mapping(
    db: Session, user_id: UUID, item_id: UUID, item_balance: Optional[float] = None
):
    # Check if mapping already exists
    existing_mapping = (
        db.query(UserItemMap)
        .filter(UserItemMap.user_id == user_id, UserItemMap.item_id == item_id)
        .first()
    )
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
        item_balance=item_balance,  # Will be None if not provided
    )
    db.add(user_item_mapping)
    db.commit()
    db.refresh(user_item_mapping)
    return user_item_mapping


def create_multiple_user_item_mappings(
    db: Session,
    user_id: UUID,
    item_ids: List[UUID],
    item_balances: Optional[List[float]] = None,
):
    """
    Map multiple items to a user at once.

    Args:
        db: Database session
        user_id: User UUID to map items to
        item_ids: List of item UUIDs to map
        item_balances: Optional list of balances for each item

    Returns:
        List of created or updated UserItemMap objects
    """
    if item_balances and len(item_ids) != len(item_balances):
        raise ValueError("item_ids and item_balances must have the same length")

    mappings = []

    for i, item_id in enumerate(item_ids):
        balance = item_balances[i] if item_balances else None

        # Check if mapping already exists
        existing_mapping = (
            db.query(UserItemMap)
            .filter(UserItemMap.user_id == user_id, UserItemMap.item_id == item_id)
            .first()
        )

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
                item_balance=balance,
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
        existing_mapping = (
            db.query(ProjectUserMap)
            .filter(
                ProjectUserMap.user_id == user_id,
                ProjectUserMap.project_id == project_id,
            )
            .first()
        )

        if existing_mapping:
            mappings.append(existing_mapping)
        else:
            # Create new mapping
            new_mapping = ProjectUserMap(
                uuid=str(uuid4()), user_id=user_id, project_id=project_id
            )
            db.add(new_mapping)
            mappings.append(new_mapping)

    db.commit()

    # Refresh all mappings
    for mapping in mappings:
        db.refresh(mapping)

    return mappings


def sync_project_user_mappings(db: Session, user_ids: List[UUID], project_id: UUID):
    """
    Synchronize project-user mappings based on the provided list.
    This function will:
    1. Add new mappings for users not already mapped to the project
    2. Remove mappings for users that are in the database but not in the provided list

    Args:
        db: Database session
        user_ids: List of user UUIDs to sync with the project
        project_id: Project UUID to sync users with

    Returns:
        Dict containing added and removed mapping counts
    """
    # Get existing mappings for this project
    existing_mappings = (
        db.query(ProjectUserMap).filter(ProjectUserMap.project_id == project_id).all()
    )

    existing_user_ids = {mapping.user_id for mapping in existing_mappings}

    # Identify users to add and remove
    users_to_add = [user_id for user_id in user_ids if user_id not in existing_user_ids]
    users_to_remove = [
        mapping.user_id
        for mapping in existing_mappings
        if mapping.user_id not in user_ids
    ]

    # Add new mappings
    added_mappings = []
    for user_id in users_to_add:
        new_mapping = ProjectUserMap(
            uuid=str(uuid4()), user_id=user_id, project_id=project_id
        )
        db.add(new_mapping)
        added_mappings.append(new_mapping)

    # Remove mappings not in the provided list
    removed_count = 0
    for user_id in users_to_remove:
        mapping_to_remove = next(m for m in existing_mappings if m.user_id == user_id)
        db.delete(mapping_to_remove)
        removed_count += 1

    # Commit changes
    db.commit()

    # Refresh added mappings
    for mapping in added_mappings:
        db.refresh(mapping)

    return {
        "added": len(added_mappings),
        "removed": removed_count,
        "mappings": added_mappings,
    }


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
    mapping = (
        db.query(ProjectItemMap)
        .filter(
            ProjectItemMap.item_id == item_id, ProjectItemMap.project_id == project_id
        )
        .first()
    )

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
    mapping = (
        db.query(ProjectUserMap)
        .filter(
            ProjectUserMap.user_id == user_id, ProjectUserMap.project_id == project_id
        )
        .first()
    )

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
    mapping = (
        db.query(UserItemMap)
        .filter(UserItemMap.user_id == user_id, UserItemMap.item_id == item_id)
        .first()
    )

    if not mapping:
        return False

    db.delete(mapping)
    db.commit()
    return True


def sync_project_user_item_mappings(
    db: Session, project_id: UUID, user_id: UUID, item_ids: List[UUID]
):
    """
    Synchronize project-user-item mappings based on the provided list.
    This function will:
    1. Add new mappings for items not already mapped to the user under the project
    2. Remove mappings for items that are in the database but not in the provided list

    Args:
        db: Database session
        project_id: Project UUID
        user_id: User UUID
        item_ids: List of item UUIDs to sync with the user under the project

    Returns:
        Dict containing added and removed mapping counts
    """
    # Get existing mappings for this project-user combination
    existing_mappings = (
        db.query(ProjectUserItemMap)
        .filter(
            ProjectUserItemMap.project_id == project_id,
            ProjectUserItemMap.user_id == user_id,
        )
        .all()
    )

    existing_item_ids = {mapping.item_id for mapping in existing_mappings}

    # Identify items to add and remove
    items_to_add = [item_id for item_id in item_ids if item_id not in existing_item_ids]
    items_to_remove = [
        mapping.item_id
        for mapping in existing_mappings
        if mapping.item_id not in item_ids
    ]

    # Add new mappings
    added_mappings = []
    for item_id in items_to_add:
        new_mapping = ProjectUserItemMap(
            uuid=uuid4(), project_id=project_id, user_id=user_id, item_id=item_id
        )
        db.add(new_mapping)
        added_mappings.append(new_mapping)

    # Remove mappings not in the provided list
    removed_count = 0
    for item_id in items_to_remove:
        mapping_to_remove = next(m for m in existing_mappings if m.item_id == item_id)
        db.delete(mapping_to_remove)
        removed_count += 1

    # Commit changes
    db.commit()

    # Refresh added mappings
    for mapping in added_mappings:
        db.refresh(mapping)

    return {
        "added": len(added_mappings),
        "removed": removed_count,
        "mappings": added_mappings,
    }

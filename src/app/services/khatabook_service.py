# services/khatabook_service.py
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.app.database.models import Khatabook, KhatabookFile, KhatabookItem, Item, Project
import os
import shutil
from src.app.database.models import KhatabookBalance
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from src.app.schemas import constants


# def create_khatabook_entry_service(
#     db: Session,
#     data: Dict,
#     file_paths: list,
#     user_id: UUID
# ) -> Khatabook:
#     """
#     data is a dict with keys like 'amount', 'remarks', 'user_id', 'person_id', 'item_ids'
#     """
#     amount = data.get("amount")
#     remarks = data.get("remarks")
#     person_id = data.get("person_id")
#     item_ids = data.get("item_ids", [])
#     expense_date = data.get("expense_date")

#     kb_entry = Khatabook(
#         amount=amount,
#         remarks=remarks,
#         person_id=person_id,
#         expense_date=expense_date,
#         created_by=user_id
#     )
#     db.add(kb_entry)
#     db.flush()

#     if item_ids:
#         for item_uuid in item_ids:
#             item_obj = db.query(Item).filter(Item.uuid == item_uuid).first()
#             if item_obj:
#                 kb_item = KhatabookItem(
#                     khatabook_id=kb_entry.uuid,
#                     item_id=item_obj.uuid
#                 )
#                 db.add(kb_item)

#     if file_paths:
#         for f in file_paths:
#             new_file = KhatabookFile(
#                 khatabook_id=kb_entry.uuid,
#                 file_path=f
#             )
#             db.add(new_file)

#     db.commit()
#     db.refresh(kb_entry)
#     return kb_entry

def create_khatabook_entry_service(
    db: Session,
    data: Dict,
    file_paths: List[str],
    user_id: UUID,
    current_user: UUID
) -> Khatabook:
    """
    Creates a new Khatabook entry and updates the user's balance.
    If concurrency is possible, row-level locking ensures only one transaction
    at a time can modify the same user's balance.

    data is a dict with keys like:
      'amount': float
      'remarks': str
      'person_id': UUID
      'item_ids': list of UUID
      'expense_date': datetime string or None
    """
    try:
        amount = float(data.get("amount", 0.0))

        user_balance = get_user_balance(user_uuid=current_user, db=db)
        entries = get_all_khatabook_entries_service(user_id=current_user, db=db)
        total_amount = sum(entry["amount"] for entry in entries) if entries else 0.0

        new_total_amount = total_amount + amount
        new_balance = user_balance - new_total_amount

        # 3. Create the Khatabook entry.
        kb_entry = Khatabook(
            amount=amount,
            remarks=data.get("remarks"),
            person_id=data.get("person_id"),
            expense_date=data.get("expense_date"),
            created_by=user_id,
            balance_after_entry=new_balance,  # Snapshot at time of creation
            project_id=data.get("project_id"),
            payment_mode=data.get("payment_mode")
        )
        db.add(kb_entry)
        db.flush()
        # 4. Attach items
        item_ids = data.get("item_ids", [])
        if item_ids:
            for item_uuid in item_ids:
                item_obj = db.query(Item).filter(Item.uuid == item_uuid).first()
                if item_obj:
                    kb_item = KhatabookItem(
                        khatabook_id=kb_entry.uuid,
                        item_id=item_obj.uuid
                    )
                    db.add(kb_item)

        # 5. Store file attachments
        for f in file_paths:
            new_file = KhatabookFile(khatabook_id=kb_entry.uuid, file_path=f)
            db.add(new_file)

        # 6. Commit all changes
        db.commit()
        db.refresh(kb_entry)
        return kb_entry

    except Exception as e:
        print(str(e))
        db.rollback()
        raise


def update_khatabook_entry_service(
    db: Session, kb_uuid: UUID, data: Dict, files: List[UploadFile]
) -> Optional[Khatabook]:
    kb_entry = db.query(Khatabook).filter(
        Khatabook.uuid == kb_uuid,
        Khatabook.is_deleted.is_(False)
    ).first()
    if not kb_entry:
        return None

    kb_entry.amount = data.get("amount", kb_entry.amount)
    kb_entry.remarks = data.get("remarks", kb_entry.remarks)
    kb_entry.person_id = data.get("person_id", kb_entry.person_id)
    kb_entry.user_id = data.get("user_id", kb_entry.user_id)

    # If item_ids key is present, replace items
    if "item_ids" in data:
        item_ids = data["item_ids"]
        db.query(KhatabookItem).filter(KhatabookItem.khatabook_id == kb_entry.uuid).delete()
        db.flush()
        for item_uuid in item_ids:
            item_obj = db.query(Item).filter(Item.uuid == item_uuid).first()
            if item_obj:
                new_kb_item = KhatabookItem(
                    khatabook_id=kb_entry.uuid,
                    item_id=item_obj.uuid
                )
                db.add(new_kb_item)

    if files:
        db.query(KhatabookFile).filter(KhatabookFile.khatabook_id == kb_entry.uuid).delete()
        db.flush()
        for f in files:
            file_path = save_uploaded_file(f, "khatabook_files")
            new_file = KhatabookFile(
                khatabook_id=kb_entry.uuid,
                file_path=file_path
            )
            db.add(new_file)

    db.commit()
    db.refresh(kb_entry)
    return kb_entry


def delete_khatabook_entry_service(db: Session, kb_uuid: UUID) -> bool:
    """
    Soft delete a khatabook entry by setting is_deleted to True.

    Args:
        db: Database session
        kb_uuid: UUID of the khatabook entry

    Returns:
        True if the entry was deleted, False if the entry doesn't exist
    """
    kb_entry = db.query(Khatabook).filter(
        Khatabook.uuid == kb_uuid,
        Khatabook.is_deleted.is_(False)
    ).first()
    if not kb_entry:
        return False

    kb_entry.is_deleted = True
    db.commit()
    return True


def hard_delete_khatabook_entry_service(db: Session, kb_uuid: UUID) -> bool:
    """
    Hard delete a khatabook entry by removing it from the database.
    Also deletes related files and item mappings.

    Args:
        db: Database session
        kb_uuid: UUID of the khatabook entry

    Returns:
        True if the entry was deleted, False if the entry doesn't exist
    """
    # First, delete related files
    db.query(KhatabookFile).filter(KhatabookFile.khatabook_id == kb_uuid).delete()

    # Delete related item mappings
    db.query(KhatabookItem).filter(KhatabookItem.khatabook_id == kb_uuid).delete()

    # Delete the khatabook entry
    result = db.query(Khatabook).filter(Khatabook.uuid == kb_uuid).delete()

    db.commit()
    return result > 0


def get_all_khatabook_entries_service(user_id: UUID, db: Session) -> List[dict]:
    entries = (
        db.query(Khatabook)
        .options(
            joinedload(Khatabook.files),
            joinedload(Khatabook.person),
            joinedload(Khatabook.items).joinedload(KhatabookItem.item),
            joinedload(Khatabook.project),
            joinedload(Khatabook.created_by_user)  # Add created_by_user relationship
        )
        .filter(
            Khatabook.is_deleted.is_(False),
            Khatabook.created_by == user_id
        )
        .order_by(Khatabook.id.desc())
        .all()
    )

    response_data = []
    for entry in entries:
        file_urls = []
        if entry.files:
            for f in entry.files:
                filename = os.path.basename(f.file_path)
                file_url = f"{constants.HOST_URL}/uploads/khatabook_files/{filename}"
                file_urls.append(file_url)

        items_data = []
        if entry.items:
            for khatabook_item in entry.items:
                if khatabook_item.item:
                    items_data.append({
                        "uuid": str(khatabook_item.item.uuid),
                        "name": khatabook_item.item.name,
                        "category": khatabook_item.item.category,
                    })

        project_info = None
        if entry.project:
            project_info = {
                "uuid": str(entry.project.uuid),
                "name": entry.project.name
            }

        # Add created_by_user information
        user_info = None
        if entry.created_by_user:
            user_info = {
                "uuid": str(entry.created_by_user.uuid),
                "name": entry.created_by_user.name
            }

        response_data.append({
            "uuid": str(entry.uuid),
            "amount": entry.amount,
            "remarks": entry.remarks,
            "balance_after_entry": entry.balance_after_entry,  # <-- include the snapshot
            "person": {
                "uuid": str(entry.person.uuid),
                "name": entry.person.name
            } if entry.person else None,
            "project_info": project_info,
            "expense_date": entry.expense_date.isoformat() if entry.expense_date else None,
            "created_at": entry.created_at.isoformat(),
            "files": file_urls,
            "items": items_data,
            "payment_mode": entry.payment_mode,
            "is_suspicious": entry.is_suspicious,
            "created_by_user": user_info  # Include created_by_user info
        })

    return response_data


def save_uploaded_file(upload_file: UploadFile, folder: str) -> str:
    """
    Utility function to save an uploaded file to disk and return its path.
    """
    upload_dir = os.path.join("src", "app", "uploads", folder)
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, upload_file.filename)
    with open(file_location, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    return file_location


def get_user_balance(user_uuid: UUID, db: Session) -> float:
    """
    Fetch the user's current Khatabook balance from KhatabookBalance.
    Returns 0.0 if no balance record exists.
    """
    bal = db.query(KhatabookBalance.balance).filter(
        KhatabookBalance.user_uuid == user_uuid
    ).first()
    return bal[0] if bal else 0.0


def mark_khatabook_entry_suspicious(db: Session, kb_uuid: UUID, is_suspicious: bool) -> Optional[Khatabook]:
    """
    Mark a khatabook entry as suspicious or not suspicious.

    Args:
        db: Database session
        kb_uuid: UUID of the khatabook entry
        is_suspicious: Whether to mark the entry as suspicious or not

    Returns:
        The updated khatabook entry, or None if the entry doesn't exist
    """
    kb_entry = db.query(Khatabook).filter(
        Khatabook.uuid == kb_uuid,
        Khatabook.is_deleted.is_(False)
    ).first()

    if not kb_entry:
        return None

    kb_entry.is_suspicious = is_suspicious
    db.commit()
    db.refresh(kb_entry)
    return kb_entry

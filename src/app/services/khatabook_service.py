import os
import shutil
import json
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.app.database.models import (
    Khatabook,
    KhatabookFile,
    KhatabookItem,
    Item
)


def create_khatabook_entry_service(
    db: Session, data: Dict, files: List[UploadFile]
) -> Khatabook:
    """
    data is a dict with keys like:
        "amount", "remarks", "person_id", "user_id", "item_ids" (list of UUIDs)
    Example:
        {
          "amount": 1000,
          "remarks": "Remark 1",
          "person_id": "4bf5e206-7f57-4173-8655-59ab8b06653e",
          "user_id": "73abb595-5e50-411e-b113-bf7f64be6a17",
          "item_ids": ["5001074c-128d-4435-93f6-3ab6a05a3066"]
        }
    """
    # Extract fields from data safely
    amount = data.get("amount")
    remarks = data.get("remarks")
    person_id = data.get("person_id")
    user_id = data.get("user_id")
    item_ids = data.get("item_ids", [])

    # 1) Create main Khatabook entry
    kb_entry = Khatabook(
        amount=amount,
        remarks=remarks,
        person_id=person_id,
        user_id=user_id
    )
    db.add(kb_entry)
    db.flush()  # to get kb_entry.uuid

    # 2) Link items
    for item_uuid in item_ids:
        item_obj = db.query(Item).filter(Item.uuid == item_uuid).first()
        if item_obj:
            kb_item = KhatabookItem(
                khatabook_id=kb_entry.uuid,
                item_id=item_obj.uuid
            )
            db.add(kb_item)

    # 3) Save files
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



def get_all_khatabook_entries_service(db: Session) -> List[Khatabook]:
    """Return all non-deleted khatabook entries."""
    return db.query(Khatabook).filter(Khatabook.is_deleted == False).order_by(Khatabook.id.desc()).all()

def update_khatabook_entry_service(
    db: Session, kb_uuid: UUID, data: Dict, files: List[UploadFile]
) -> Optional[Khatabook]:
    """
    Update an existing Khatabook entry. If item_ids are provided, replace them.
    If files are provided, remove old files, store new ones.
    """
    kb_entry = db.query(Khatabook).filter(
        Khatabook.uuid == kb_uuid,
        Khatabook.is_deleted == False
    ).first()
    if not kb_entry:
        return None

    # Update basic fields
    if "amount" in data:
        kb_entry.amount = data["amount"]
    if "remarks" in data:
        kb_entry.remarks = data["remarks"]
    if "person_id" in data:
        kb_entry.person_id = data["person_id"]
    if "user_id" in data:
        kb_entry.user_id = data["user_id"]

    # Replace items if item_ids is present
    if "item_ids" in data:
        item_ids = data["item_ids"]
        db.query(KhatabookItem).filter(KhatabookItem.khatabook_id == kb_entry.uuid).delete()
        db.flush()
        for item_uuid in item_ids:
            item_obj = db.query(Item).filter(Item.uuid == item_uuid).first()
            if item_obj:
                kb_item = KhatabookItem(
                    khatabook_id=kb_entry.uuid,
                    item_id=item_obj.uuid
                )
                db.add(kb_item)

    # Replace files if new files are uploaded
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
    """Soft-deletes a Khatabook entry by setting is_deleted=True."""
    kb_entry = db.query(Khatabook).filter(
        Khatabook.uuid == kb_uuid,
        Khatabook.is_deleted == False
    ).first()
    if not kb_entry:
        return False

    kb_entry.is_deleted = True
    db.commit()
    return True


def save_uploaded_file(upload_file: UploadFile, folder: str) -> str:
    """
    Saves an uploaded file to local 'src/app/uploads/<folder>/' directory.
    Returns the file path.
    """
    upload_dir = os.path.join("src", "app", "uploads", folder)
    os.makedirs(upload_dir, exist_ok=True)

    file_location = os.path.join(upload_dir, upload_file.filename)
    with open(file_location, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)

    return file_location

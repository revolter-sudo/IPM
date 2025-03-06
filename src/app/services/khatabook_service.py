# services/khatabook_service.py
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.app.database.models import Khatabook, KhatabookFile, KhatabookItem, Item
import os
import shutil

def create_khatabook_entry_service(
    db: Session, data: Dict, files: List[UploadFile]
) -> Khatabook:
    """
    data is a dict with keys like 'amount', 'remarks', 'user_id', 'person_id', 'item_ids'
    """
    amount = data.get("amount")
    remarks = data.get("remarks")
    person_id = data.get("person_id")
    user_id = data.get("user_id")
    item_ids = data.get("item_ids", [])

    kb_entry = Khatabook(
        amount=amount,
        remarks=remarks,
        person_id=person_id,
        user_id=user_id
    )
    db.add(kb_entry)
    db.flush()

    if item_ids:
        for item_uuid in item_ids:
            item_obj = db.query(Item).filter(Item.uuid == item_uuid).first()
            if item_obj:
                kb_item = KhatabookItem(
                    khatabook_id=kb_entry.uuid,
                    item_id=item_obj.uuid
                )
                db.add(kb_item)

    if files:
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


def update_khatabook_entry_service(
    db: Session, kb_uuid: UUID, data: Dict, files: List[UploadFile]
) -> Optional[Khatabook]:
    kb_entry = db.query(Khatabook).filter(Khatabook.uuid == kb_uuid, Khatabook.is_deleted == False).first()
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
    kb_entry = db.query(Khatabook).filter(
        Khatabook.uuid == kb_uuid, 
        Khatabook.is_deleted == False
    ).first()
    if not kb_entry:
        return False

    kb_entry.is_deleted = True
    db.commit()
    return True


def get_all_khatabook_entries_service(db: Session) -> List[Khatabook]:
    return db.query(Khatabook).filter(Khatabook.is_deleted == False).all()


def save_uploaded_file(upload_file: UploadFile, folder: str) -> str:
    upload_dir = os.path.join("src", "app", "uploads", folder)
    os.makedirs(upload_dir, exist_ok=True)

    file_location = os.path.join(upload_dir, upload_file.filename)
    with open(file_location, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)

    return file_location

# services/khatabook_service.py
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.orm import Session
from src.app.database.models import Khatabook, KhatabookFile, KhatabookItem, Item
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
    user_id: UUID
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
        # 1. Retrieve and lock the balance row so no other transaction can modify it.
        bal_obj = (
            db.query(KhatabookBalance)
            .filter(KhatabookBalance.user_uuid == user_id)
            .with_for_update()  # <-- row-level lock
            .one_or_none()
        )
        if not bal_obj:
            # Optionally create a new balance record if user has none
            bal_obj = KhatabookBalance(user_uuid=user_id, balance=0.0)
            db.add(bal_obj)
            db.flush()

        old_balance = bal_obj.balance
        amount = float(data.get("amount", 0.0))

        # 2. Subtract the amount from the old balance.
        #    If you want to disallow negative balances, add a check here:
        # if old_balance < amount:
        #     raise HTTPException(status_code=400, detail="Insufficient balance.")

        new_balance = old_balance - amount
        bal_obj.balance = new_balance

        # 3. Create the Khatabook entry.
        kb_entry = Khatabook(
            amount=amount,
            remarks=data.get("remarks"),
            person_id=data.get("person_id"),
            expense_date=data.get("expense_date"),
            created_by=user_id,
            balance_after_entry=new_balance,  # Snapshot at time of creation
        )
        db.add(kb_entry)
        db.flush()

        # 4. Attach items
        item_ids = data.get("item_ids", [])
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
    kb_entry = db.query(Khatabook).filter(
        Khatabook.uuid == kb_uuid,
        Khatabook.is_deleted.is_(False)
    ).first()
    if not kb_entry:
        return False

    kb_entry.is_deleted = True
    db.commit()
    return True


# def get_all_khatabook_entries_service(
#     user_id: UUID,
#     db: Session
# ) -> List[dict]:
#     # Use joinedload to fetch files, person, and items->item in one go
#     entries = (
#         db.query(Khatabook)
#         .options(
#             joinedload(Khatabook.files),
#             joinedload(Khatabook.person),
#             joinedload(Khatabook.items).joinedload(KhatabookItem.item)
#         )
#         .filter(
#             and_(
#                 Khatabook.is_deleted.is_(False),
#                 Khatabook.created_by == user_id
#             )
#         )
#         .order_by(Khatabook.id.desc())
#         .all()
#     )

#     response_data = []
#     for entry in entries:
#         # Build file URL list
#         file_urls = []
#         if entry.files:
#             for f in entry.files:
#                 filename = os.path.basename(f.file_path)
#                 file_url = f"{constants.HOST_URL}/uploads/khatabook_files/{filename}"
#                 file_urls.append(file_url)

#         # Build items data
#         items_data = []
#         if entry.items:
#             for khatabook_item in entry.items:
#                 if khatabook_item.item:
#                     items_data.append({
#                         "uuid": str(khatabook_item.item.uuid),
#                         "name": khatabook_item.item.name,
#                         "category": khatabook_item.item.category,
#                         "quantity": getattr(khatabook_item, "quantity", None)
#                     })

#         response_data.append({
#             "uuid": str(entry.uuid),
#             "amount": entry.amount,
#             "remarks": entry.remarks,
#             "person": {
#                 "uuid": str(entry.person.uuid),
#                 "name": entry.person.name
#             } if entry.person else None,
#             "expense_date": entry.expense_date.isoformat() if entry.expense_date else None,
#             "created_at": entry.created_at.isoformat(),
#             "files": file_urls,
#             "items": items_data
#         })

#     return response_data

def get_all_khatabook_entries_service(user_id: UUID, db: Session) -> List[dict]:
    entries = (
        db.query(Khatabook)
        .options(
            joinedload(Khatabook.files),
            joinedload(Khatabook.person),
            joinedload(Khatabook.items).joinedload(KhatabookItem.item)
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

        response_data.append({
            "uuid": str(entry.uuid),
            "amount": entry.amount,
            "remarks": entry.remarks,
            "balance_after_entry": entry.balance_after_entry,  # <-- include the snapshot
            "person": {
                "uuid": str(entry.person.uuid),
                "name": entry.person.name
            } if entry.person else None,
            "expense_date": entry.expense_date.isoformat() if entry.expense_date else None,
            "created_at": entry.created_at.isoformat(),
            "files": file_urls,
            "items": items_data
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

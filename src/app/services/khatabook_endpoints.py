from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Form
from typing import List, Optional
from uuid import UUID
import json

from starlette.responses import FileResponse
from sqlalchemy.orm import Session

from src.app.database.database import get_db
from src.app.database.models import KhatabookFile
from src.app.services.khatabook_service import (
    create_khatabook_entry_service,
    get_all_khatabook_entries_service,
    update_khatabook_entry_service,
    delete_khatabook_entry_service
)

khatabook_router = APIRouter(prefix="/khatabook", tags=["Khatabook"])


@khatabook_router.post("/")
async def create_khatabook_entry(
    data: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db)
):
    """
    Creates a Khatabook entry from multipart/form-data:
      - 'data' is a JSON string
      - 'files' is a list of uploaded files

    Example 'data' (JSON):
        {
          "amount": 1000,
          "remarks": "Remark 1",
          "person_id": "4bf5e206-7f57-4173-8655-59ab8b06653e",
          "user_id": "73abb595-5e50-411e-b113-bf7f64be6a17",
          "item_ids": ["5001074c-128d-4435-93f6-3ab6a05a3066"]
        }
    """
    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in 'data' field")

    entry = create_khatabook_entry_service(db, parsed_data, files)
    return build_khatabook_dict(entry)


@khatabook_router.get("/")
def get_all_khatabook_entries(db: Session = Depends(get_db)):
    """
    Returns a list of Khatabook entries as dictionaries, including person/user/items/files.
    """
    entries = get_all_khatabook_entries_service(db)
    return [build_khatabook_dict(e) for e in entries]


@khatabook_router.put("/{khatabook_uuid}")
def update_khatabook_entry(
    khatabook_uuid: UUID,
    data: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db)
):
    """
    Update a Khatabook entry with new data (in JSON string) and/or files.
    """
    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in 'data' field")

    entry = update_khatabook_entry_service(db, khatabook_uuid, parsed_data, files)
    if not entry:
        raise HTTPException(status_code=404, detail="Khatabook entry not found")

    return build_khatabook_dict(entry)


@khatabook_router.delete("/{khatabook_uuid}", status_code=204)
def delete_khatabook_entry(khatabook_uuid: UUID, db: Session = Depends(get_db)):
    """
    Soft-delete a Khatabook entry by uuid.
    """
    success = delete_khatabook_entry_service(db, khatabook_uuid)
    if not success:
        raise HTTPException(status_code=404, detail="Khatabook entry not found")
    return  # 204 => No Content


@khatabook_router.get("/files/{file_id}/download")
def download_khatabook_file(file_id: int, db: Session = Depends(get_db)):
    """
    Download an uploaded file by ID.
    """
    file_obj = db.query(KhatabookFile).filter(KhatabookFile.id == file_id).first()
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_obj.file_path,
        filename=file_obj.file_path.split("/")[-1]
    )


# Helper to return a plain dictionary from the Khatabook ORM object


def build_khatabook_dict(entry) -> dict:
    """
    Convert the Khatabook ORM object (plus user/person/items/files relationships)
    into a simple dictionary response, avoiding nested Pydantic models.
    """
    if not entry:
        return {}

    data = {
        "uuid": str(entry.uuid),
        "amount": entry.amount,
        "remarks": entry.remarks,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "person": None,
        "user": None,
        "items": [],
        "files": []
    }

    # Person
    if entry.person:
        data["person"] = {
            "uuid": str(entry.person.uuid),
            "name": entry.person.name,
            "phone_number": entry.person.phone_number,
        }

    # User
    if entry.user:
        data["user"] = {
            "uuid": str(entry.user.uuid),
            "name": entry.user.name
        }

    # Items (pivot table)
    for kb_item in entry.items:
        if kb_item.item:
            data["items"].append({
                "uuid": str(kb_item.item.uuid),
                "name": kb_item.item.name,
                # add more fields if needed
            })

    # Files
    for f in entry.files:
        data["files"].append({
            "id": f.id,
            "download_url": f"/khatabook/files/{f.id}/download"
        })

    return data

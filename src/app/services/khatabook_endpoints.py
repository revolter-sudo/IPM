import os
import shutil
import json
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from src.app.database.database import get_db
from src.app.schemas.auth_service_schamas import AuthServiceResponse
from src.app.services.khatabook_service import (
    create_khatabook_entry_service,
    get_all_khatabook_entries_service,
    update_khatabook_entry_service,
    delete_khatabook_entry_service,
    get_user_balance
)
from src.app.database.models import User
from src.app.services.auth_service import get_current_user
from src.app.schemas import constants

khatabook_router = APIRouter(prefix="/khatabook", tags=["Khatabook"])

UPLOAD_DIR = constants.KHATABOOK_FOLDER
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_uploaded_file(upload_file: UploadFile) -> str:
    file_location = os.path.join(UPLOAD_DIR, upload_file.filename)
    with open(file_location, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)
    return upload_file.filename

@khatabook_router.post("")
async def create_khatabook_entry(
    data: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        parsed_data = json.loads(data)
        file_paths = [save_uploaded_file(f) for f in files] if files else []
        create_khatabook_entry_service(db=db, data=parsed_data, file_paths=file_paths, user_id=current_user.uuid, current_user=current_user.uuid)
        return AuthServiceResponse(
            data=None,
            status_code=201,
            message="Khatabook entry created successfully"
        ).model_dump()
    except Exception as e:
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error: {str(e)}"
        ).model_dump()

@khatabook_router.put("/{khatabook_uuid}")
def update_khatabook_entry(
    khatabook_uuid: UUID,
    data: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    try:
        parsed_data = json.loads(data)
        file_paths = [save_uploaded_file(f) for f in files] if files else []
        entry = update_khatabook_entry_service(db, khatabook_uuid, parsed_data, file_paths)
        if not entry:
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="Khatabook entry not found"
            ).model_dump()
        return AuthServiceResponse(
            data=None,
            status_code=200,
            message="Khatabook entry updated successfully"
        ).model_dump()
    except Exception as e:
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error: {str(e)}"
        ).model_dump()


@khatabook_router.get("")
def get_all_khatabook_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_balance = get_user_balance(user_uuid=current_user.uuid, db=db)
    entries = get_all_khatabook_entries_service(user_id=current_user.uuid, db=db)
    total_amount = sum(entry["amount"] for entry in entries) if entries else 0.0
    remaining_balance = user_balance - total_amount
    response_data = {
        "remaining_balance": remaining_balance,
        "total_amount": total_amount,
        "entries": entries
    }
    return AuthServiceResponse(
        data=response_data,
        status_code=200,
        message="Khatabook entries fetched successfully"
    ).model_dump()

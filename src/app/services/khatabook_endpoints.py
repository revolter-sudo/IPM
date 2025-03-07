from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import List, Optional
from uuid import UUID
import json
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


khatabook_router = APIRouter(prefix="/khatabook", tags=["Khatabook"])

@khatabook_router.post("")
async def create_khatabook_entry(
    data: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db=Depends(get_db)
):
    try:
        parsed_data = json.loads(data)
        entry = create_khatabook_entry_service(db, parsed_data, files)
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


@khatabook_router.get("")
def get_all_khatabook_entries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_balance = get_user_balance(user_uuid=current_user.uuid, db=db)
    entries = get_all_khatabook_entries_service(db)
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

@khatabook_router.put("/{khatabook_uuid}")
def update_khatabook_entry(
    khatabook_uuid: UUID,
    data: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    parsed_data = json.loads(data)
    entry = update_khatabook_entry_service(db, khatabook_uuid, parsed_data, files)
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

@khatabook_router.delete("/{khatabook_uuid}")
def delete_khatabook_entry(khatabook_uuid: UUID, db: Session = Depends(get_db)):
    success = delete_khatabook_entry_service(db, khatabook_uuid)
    if not success:
        return AuthServiceResponse(
            data=None,
            status_code=404,
            message="Khatabook entry not found"
        ).model_dump()

    return AuthServiceResponse(
        data=None,
        status_code=200,
        message="Khatabook entry deleted successfully"
    ).model_dump()

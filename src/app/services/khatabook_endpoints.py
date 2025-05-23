import os
import shutil
import json
import pandas as pd
from io import BytesIO
from src.app.schemas.auth_service_schamas import UserRole
from typing import Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from src.app.database.database import get_db
from src.app.schemas.auth_service_schamas import AuthServiceResponse
from src.app.schemas.khatabook_schemas import MarkSuspiciousRequest, KhatabookServiceResponse
from src.app.services.khatabook_service import (
    create_khatabook_entry_service,
    get_all_khatabook_entries_service,
    update_khatabook_entry_service,
    delete_khatabook_entry_service,
    hard_delete_khatabook_entry_service,
    get_user_balance,
    mark_khatabook_entry_suspicious
)
from src.app.database.models import User
from src.app.services.auth_service import get_current_user
from src.app.schemas import constants

khatabook_router = APIRouter(prefix="/khatabook", tags=["Khatabook"])

UPLOAD_DIR = constants.KHATABOOK_FOLDER
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_uploaded_file(upload_file: UploadFile) -> str:
    # Create a unique filename to avoid collisions
    file_ext = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{str(uuid4())}{file_ext}"
    file_location = os.path.join(UPLOAD_DIR, unique_filename)

    # Save the file
    with open(file_location, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)

    return unique_filename

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
    # Check if current_user is a dictionary (error response)
    if isinstance(current_user, dict):
        # Return the error response directly
        return current_user

    try:
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
    except Exception as e:
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching khatabook entries: {str(e)}"
        ).model_dump()


@khatabook_router.patch("/{khatabook_uuid}/mark-suspicious")
def mark_suspicious(
    khatabook_uuid: UUID,
    request: MarkSuspiciousRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a khatabook entry as suspicious or not suspicious.
    Only admin and super admin users can mark entries as suspicious.
    """
    # Check if current_user is a dictionary (error response)
    if isinstance(current_user, dict):
        # Return the error response directly
        return current_user

    try:
        # Check if user has permission (admin or super admin)
        if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            return KhatabookServiceResponse(
                data=None,
                status_code=403,
                message="Only admin and super admin can mark entries as suspicious"
            ).model_dump()

        # Mark the entry as suspicious
        entry = mark_khatabook_entry_suspicious(
            db=db,
            kb_uuid=khatabook_uuid,
            is_suspicious=request.is_suspicious
        )

        if not entry:
            return KhatabookServiceResponse(
                data=None,
                status_code=404,
                message="Khatabook entry not found"
            ).model_dump()

        return KhatabookServiceResponse(
            data={
                "uuid": str(entry.uuid),
                "is_suspicious": entry.is_suspicious
            },
            status_code=200,
            message=f"Khatabook entry marked as {'suspicious' if request.is_suspicious else 'not suspicious'}"
        ).model_dump()
    except Exception as e:
        db.rollback()
        return KhatabookServiceResponse(
            data=None,
            status_code=500,
            message=f"Error: {str(e)}"
        ).model_dump()


@khatabook_router.get("/export")
def export_khatabook_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export khatabook entries to Excel.
    """
    # Check if current_user is a dictionary (error response)
    if isinstance(current_user, dict):
        # Return the error response directly
        return current_user

    try:
        # Get all khatabook entries
        entries = get_all_khatabook_entries_service(user_id=current_user.uuid, db=db)

        # Create a DataFrame from the entries
        df_data = []
        for entry in entries:
            person_name = entry.get("person", {}).get("name", "") if entry.get("person") else ""

            # Fix for item extraction - handle different item structures
            items_list = []
            for item in entry.get("items", []):
                if isinstance(item, dict):
                    # Direct dictionary with name
                    if "name" in item:
                        items_list.append(item["name"])
                    # Dictionary with nested item structure
                    elif "item" in item and isinstance(item["item"], dict) and "name" in item["item"]:
                        items_list.append(item["item"]["name"])

            items = ", ".join(items_list)

            df_data.append({
                "Date": entry.get("created_at", ""),
                "Expense Date": entry.get("expense_date", ""),
                "Amount": entry.get("amount", 0),
                "Remarks": entry.get("remarks", ""),
                "Person": person_name,
                "Items": items,
                "Payment Mode": entry.get("payment_mode", ""),
                "Balance After Entry": entry.get("balance_after_entry", 0),
                "Suspicious": "Yes" if entry.get("is_suspicious", False) else "No"
            })

        # Create DataFrame
        df = pd.DataFrame(df_data)

        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Khatabook Entries", index=False)

            # Auto-adjust columns width
            worksheet = writer.sheets["Khatabook Entries"]
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, column_width)

        output.seek(0)

        # Return Excel file as response
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=khatabook_entries.xlsx"
            }
        )
    except Exception as e:
        return KhatabookServiceResponse(
            data=None,
            status_code=500,
            message=f"Error exporting khatabook data: {str(e)}"
        ).model_dump()


@khatabook_router.delete("/{khatabook_uuid}/hard-delete")
def hard_delete_khatabook_entry(
    khatabook_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Hard delete a khatabook entry.
    Only admin and super admin users can hard delete entries.
    """
    # Check if current_user is a dictionary (error response)
    if isinstance(current_user, dict):
        # Return the error response directly
        return current_user

    try:
        # Check if user has permission (admin or super admin)
        if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            return KhatabookServiceResponse(
                data=None,
                status_code=403,
                message="Only admin and super admin can hard delete entries"
            ).model_dump()

        # Hard delete the entry
        result = hard_delete_khatabook_entry_service(db=db, kb_uuid=khatabook_uuid)

        if not result:
            return KhatabookServiceResponse(
                data=None,
                status_code=404,
                message="Khatabook entry not found"
            ).model_dump()

        return KhatabookServiceResponse(
            data=None,
            status_code=200,
            message="Khatabook entry permanently deleted"
        ).model_dump()
    except Exception as e:
        db.rollback()
        return KhatabookServiceResponse(
            data=None,
            status_code=500,
            message=f"Error: {str(e)}"
        ).model_dump()

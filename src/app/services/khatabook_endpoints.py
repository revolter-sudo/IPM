import os
import shutil
import json
import pandas as pd
from io import BytesIO
from src.app.schemas.auth_service_schamas import UserRole
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from src.app.database.database import get_db
from src.app.schemas.auth_service_schamas import AuthServiceResponse
from src.app.schemas.khatabook_schemas import (
    MarkSuspiciousRequest, KhatabookServiceResponse
)
from src.app.services.khatabook_service import (
    create_khatabook_entry_service,
    get_all_khatabook_entries_service,
    update_khatabook_entry_service,
    hard_delete_khatabook_entry_service,
    mark_khatabook_entry_suspicious,
    soft_delete_khatabook_entry_service
)
from src.app.database.models import User, Khatabook, KhatabookBalance
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
        # Get the current balance directly from KhatabookBalance table
        # This is the source of truth that includes self payments
        user_balance_record = db.query(KhatabookBalance).filter(
            KhatabookBalance.user_uuid == current_user.uuid
        ).first()

        current_balance = user_balance_record.balance if user_balance_record else 0.0

        entries = get_all_khatabook_entries_service(user_id=current_user.uuid, db=db)

        # Calculate total spent (only debit entries - manual expenses)
        total_spent = sum(
            entry["amount"] for entry in entries
            if entry.get("entry_type") == "Debit"
        ) if entries else 0.0
        remaining_balance = current_balance - total_spent

        response_data = {
            "remaining_balance": remaining_balance,  # Current balance from KhatabookBalance table
            "total_amount": total_spent,  # Total manual expenses (debit entries)
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
    user_id: Optional[UUID] = None,
    item_id: Optional[UUID] = None,
    person_id: Optional[UUID] = None,
    project_id: Optional[UUID] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    payment_mode: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export khatabook entries to Excel.

    For regular users: exports only their own entries.
    For admin/super admin: can apply filters to export filtered data from
    admin panel.

    Filter parameters (admin only):
    - user_id: Filter by user ID
    - item_id: Filter by item ID
    - person_id: Filter by person ID
    - project_id: Filter by project ID
    - min_amount: Minimum amount
    - max_amount: Maximum amount
    - start_date: Start date (YYYY-MM-DD format)
    - end_date: End date (YYYY-MM-DD format)
    - payment_mode: Payment mode
    """
    # Check if current_user is a dictionary (error response)
    if isinstance(current_user, dict):
        # Return the error response directly
        return current_user

    try:
        # Check if any filters are provided and user has admin permissions
        has_filters = any([
            user_id, item_id, person_id, project_id, min_amount,
            max_amount, start_date, end_date, payment_mode
        ])
        is_admin = current_user.role in [
            UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value
        ]

        if has_filters and not is_admin:
            return KhatabookServiceResponse(
                data=None,
                status_code=403,
                message="Only admin and super admin can use filters for export"
            ).model_dump()

        # If admin with filters, use admin filtering logic
        if is_admin and has_filters:
            # Import datetime here to avoid circular imports
            from datetime import datetime
            from sqlalchemy.orm import joinedload
            from src.app.database.models import (
                KhatabookItem, KhatabookFile, Person, Project
            )

            # Base query with all joins (same as admin API)
            query = (
                db.query(Khatabook)
                .outerjoin(
                    KhatabookItem,
                    Khatabook.uuid == KhatabookItem.khatabook_id
                )
                .outerjoin(
                    KhatabookFile,
                    Khatabook.uuid == KhatabookFile.khatabook_id
                )
                .outerjoin(User, Khatabook.created_by == User.uuid)  # Uncommented User join
                .outerjoin(Person, Khatabook.person_id == Person.uuid)
                .outerjoin(Project, Khatabook.project_id == Project.uuid)  # Uncommented Project join
                .filter(Khatabook.is_deleted.is_(False))
                .distinct()
            )

            # Apply filters if provided
            if user_id:
                query = query.filter(Khatabook.created_by == user_id)

            if item_id:
                query = query.filter(KhatabookItem.item_id == item_id)

            if person_id:
                query = query.filter(Khatabook.person_id == person_id)

            if project_id:
                query = query.filter(Khatabook.project_id == project_id)

            if min_amount is not None:
                query = query.filter(Khatabook.amount >= min_amount)

            if max_amount is not None:
                query = query.filter(Khatabook.amount <= max_amount)

            if start_date:
                try:
                    start_date_obj = datetime.fromisoformat(start_date)
                    query = query.filter(
                        Khatabook.expense_date >= start_date_obj
                    )
                except ValueError:
                    return KhatabookServiceResponse(
                        data=None,
                        status_code=400,
                        message="Invalid start_date format. Use YYYY-MM-DD"
                    ).model_dump()

            if end_date:
                try:
                    end_date_obj = datetime.fromisoformat(end_date)
                    query = query.filter(
                        Khatabook.expense_date <= end_date_obj
                    )
                except ValueError:
                    return KhatabookServiceResponse(
                        data=None,
                        status_code=400,
                        message="Invalid end_date format. Use YYYY-MM-DD"
                    ).model_dump()

            if payment_mode:
                query = query.filter(Khatabook.payment_mode == payment_mode)

            # Order by most recent first
            query = query.order_by(Khatabook.created_at.desc())

            # Execute query with eager loading of relationships
            khatabook_entries = (
                query
                .options(
                    joinedload(Khatabook.files),
                    joinedload(Khatabook.person),
                    joinedload(Khatabook.items).joinedload(KhatabookItem.item),
                    joinedload(Khatabook.project),
                    joinedload(Khatabook.created_by_user)
                )
                .all()
            )

            entries = []
            for entry in khatabook_entries:
                # Process items
                items_data = []
                if entry.items:
                    for khatabook_item in entry.items:
                        if khatabook_item.item:
                            items_data.append({
                                "item": {
                                    "name": khatabook_item.item.name
                                }
                            })

                # Process person info
                person_info = None
                if entry.person:
                    person_info = {
                        "name": entry.person.name
                    }

                # Process created_by user info
                created_by_info = None
                if entry.created_by_user:
                    created_by_info = {
                        "name": entry.created_by_user.name
                    }

                entries.append({
                    "created_at": entry.created_at.isoformat(),
                    "expense_date": (
                        entry.expense_date.isoformat()
                        if entry.expense_date else ""
                    ), 
                    "amount": entry.amount,
                    "remarks": entry.remarks,
                    "person": person_info,
                    "created_by_user": created_by_info,  # Use consistent field name
                    "items": items_data,
                    "payment_mode": entry.payment_mode,
                    "balance_after_entry": entry.balance_after_entry,
                    "is_suspicious": entry.is_suspicious
                })
        else:
            # Regular user or admin without filters - use existing service
            entries = get_all_khatabook_entries_service(
                user_id=current_user.uuid, db=db
            )

        # Create a DataFrame from the entries
        df_data = []
        for entry in entries:
            person = entry.get("person")
            created_by = entry.get("created_by_user")

            person_name = person.get("name") if isinstance(person, dict) and person else ""
            user_name = created_by.get("name") if isinstance(created_by, dict) and created_by else ""
            # remarks = entry.get("remarks", "").lower().strip()

            # Safe item extraction
            items_list = []
            for item in entry.get("items", []):
                if isinstance(item, dict):
                    if "name" in item:
                        items_list.append(item["name"])
                    elif isinstance(item.get("item"), dict):
                        items_list.append(item["item"].get("name", ""))

            items = ", ".join(items_list)

            # Determine credit/debit
            amount = entry.get("amount", 0)
            entry_type = entry.get("entry_type", "").strip().lower()
             
            # Append data to DataFrame
            df_data.append({
                "Date": entry.get("created_at", "-"),
                "Expense Date": entry.get("expense_date", "-"),
                "Credit Amount": amount if entry_type == "credit" else None,
                "Debit Amount": amount if entry_type == "debit" else None,
                "Remarks": entry.get("remarks", "-"),
                "Person": person_name or "-",
                "Created By": user_name or "-",
                "Items": items or "-",
                "Payment Mode": entry.get("payment_mode", "-"),
                "Balance After Entry": entry.get("balance_after_entry", "-"),
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
                column_width = max(
                    df[col].astype(str).map(len).max(), len(col)
                ) + 2
                worksheet.set_column(i, i, column_width)

        output.seek(0)

        # Return Excel file as response
        excel_media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return Response(
            content=output.getvalue(),
            media_type=excel_media_type,
            headers={
                "Content-Disposition": (
                    "attachment; filename=khatabook_entries.xlsx"
                )
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
        if current_user.role not in [
            UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value
        ]:
            return KhatabookServiceResponse(
                data=None,
                status_code=403,
                message="Only admin and super admin can hard delete entries"
            ).model_dump()

        # Hard delete the entry
        result = hard_delete_khatabook_entry_service(
            db=db, kb_uuid=khatabook_uuid
        )

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

@khatabook_router.delete("/{khatabook_uuid}/soft-delete")
def soft_delete_khatabook_entry(
    khatabook_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete a khatabook entry.
    Only ADMIN and SUPER_ADMIN users can perform this action.
    """
    # Handle unauthorized user
    if isinstance(current_user, dict):
        return current_user

    try:
        # Check user role
        if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            return KhatabookServiceResponse(
                data=None,
                status_code=403,
                message="Only admin and super admin can soft delete entries"
            ).model_dump()

        # Perform soft delete
        result = soft_delete_khatabook_entry_service(db=db, kb_uuid=khatabook_uuid)

        if not result:
            return KhatabookServiceResponse(
                data=None,
                status_code=404,
                message="Khatabook entry not found"
            ).model_dump()

        return KhatabookServiceResponse(
            data=None,
            status_code=200,
            message="Khatabook entry soft deleted successfully"
        ).model_dump()

    except Exception as e:
        db.rollback()
        return KhatabookServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while soft deleting the entry: {str(e)}"
        ).model_dump()

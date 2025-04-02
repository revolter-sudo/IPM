import os
import shutil
import traceback
from typing import Optional, List
from pydantic import BaseModel, ValidationError
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Body, Form
from fastapi import status as h_status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from src.app.database.database import get_db
from src.app.database.models import (
    Payment,
    Project,
    Person,
    User,
    Item,
    PaymentItem,
    PaymentFile,
    PaymentStatusHistory,
    Log,
    KhatabookBalance,
    PaymentEditHistory,
    Priority
)
from src.app.schemas.auth_service_schamas import UserRole
from uuid import uuid4
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.payment_service_schemas import (
    CreatePerson,
    PaymentsResponse,
    PaymentStatus,
    PaymentServiceResponse,
    CreatePaymentRequest,
    PaymentUpdateSchema,
    StatusDatePair,
    ItemListTag
)
from src.app.notification.notification_service import send_push_notification
from sqlalchemy.orm import aliased
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from src.app.services.auth_service import get_current_user
from src.app.services.project_service import create_project_balance_entry
import json
from collections import defaultdict

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


@payment_router.post("", tags=["Payments"], status_code=201)
def create_payment(
    request: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new Payment record in the database.
    If self_payment=True, automatically sets Payment.person to current_user's Person UUID.
    Otherwise, uses the person field from the request if supplied.
    Links items, uploads files, creates PaymentStatusHistory, and adjusts project balance.
    """
    try:
        import pdb
        pdb.set_trace()
        request_data = json.loads(request)
        payment_request = CreatePaymentRequest(**request_data)

        # Validate Project
        project = db.query(Project).filter(Project.uuid == payment_request.project_id).first()
        if not project:
            return PaymentServiceResponse(
                status_code=404,
                data=None,
                message="Project not found."
            ).model_dump()

        # If it's a self-payment, overwrite the `person` field with current_user's Person (if any)
        # so you don't rely on the client to supply a person UUID
        if payment_request.self_payment:
            if not current_user.person:
                # If user does not have a linked Person row, decide how to handle:
                return PaymentServiceResponse(
                    status_code=400,
                    data=None,
                    message="Cannot create self-payment because current user has no linked Person record."
                ).model_dump()
            # Force the Payment.person to the current_user’s Person.uuid
            payment_request.person = current_user.person.uuid

        # Create Payment
        new_payment = Payment(
            amount=payment_request.amount,
            description=payment_request.description,
            project_id=payment_request.project_id,
            status='requested',
            remarks=payment_request.remarks,
            created_by=current_user.uuid,
            person=payment_request.person,            # might be overwritten for self_payment
            self_payment=payment_request.self_payment, # store the flag
            latitude=payment_request.latitude,
            longitude=payment_request.longitude,
            priority_id=payment_request.priority_id,
        )
        db.add(new_payment)
        db.flush()  # flush so new_payment.uuid is available

        # Create Payment status history
        db.add(
            PaymentStatusHistory(
                payment_id=new_payment.uuid,
                status='requested',
                created_by=current_user.uuid
            )
        )
        db.flush()

        # Link items if provided
        if payment_request.item_uuids:
            db.add_all([
                PaymentItem(payment_id=new_payment.uuid, item_id=item_id)
                for item_id in payment_request.item_uuids
            ])

        # Update project balance
        create_project_balance_entry(
            db=db,
            project_id=payment_request.project_id,
            adjustment=-payment_request.amount,
            description="Payment deduction",
            current_user=current_user
        )

        # Handle file uploads
        if files:
            upload_dir = constants.UPLOAD_DIR
            os.makedirs(upload_dir, exist_ok=True)
            for file in files:
                file_path = os.path.join(upload_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    buffer.write(file.file.read())
                db.add(PaymentFile(
                    payment_id=new_payment.uuid,
                    file_path=file_path
                    ))

        db.commit()

        return PaymentServiceResponse(
            data={"payment_uuid": new_payment.uuid},
            message="Payment created successfully.",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            status_code=500,
            data=None,
            message=f"An error occurred: {str(e)}"
        ).model_dump()


@payment_router.patch("/{payment_uuid}")
def update_payment_amount(
    payment_uuid: UUID,
    payload: PaymentUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <--- If you want to store who updated
):
    # Fetch existing payment
    payment = db.query(Payment).filter(Payment.uuid == payment_uuid).first()
    if not payment:
        return PaymentServiceResponse(
            message="Payment not found",
            data=None,
            status_code=404
        ).model_dump()

    # If the new amount is different from the old, record it in PaymentEditHistory
    old_amount = payment.amount
    new_amount = payload.amount

    if old_amount != new_amount:
        edit_record = PaymentEditHistory(
            payment_id=payment.uuid,
            old_amount=old_amount,
            new_amount=new_amount,
            remarks=payload.remark,
            updated_by=current_user.uuid if current_user else None
        )
        db.add(edit_record)

    # Update the payment to the new amount
    payment.amount = new_amount
    payment.update_remarks = payload.remark  # Always store the latest remark in Payment

    # Commit changes
    db.commit()
    db.refresh(payment)

    return PaymentServiceResponse(
        message="Payment updated successfully",
        data={
            "uuid": str(payment.uuid),
            "amount": payment.amount,
            "update_remarks": payment.update_remarks,
        },
        status_code=201
    ).model_dump()


def get_parent_account_data(person_id: UUID, db):
    try:
        person = (
            db.query(Person)
            .options(joinedload(Person.parent))
            .filter(Person.uuid == person_id)
            .one_or_none()
        )
        if person is None:
            return None  # or handle error
        """
        If this person has a parent, return the parent's details; otherwise,
        return the person's own details
        """
        if person.parent is not None:
            return person.parent
        else:
            return person
    except Exception as e:
        print(f"Error in get_parent_account_data API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"Error in get_parent_account_data: {str(e)}",
            status_code=500,
        ).model_dump()


def can_edit_payment(status_history: List[str], current_user_role: str) -> bool:
    # SiteEngineer and SubContractor can never edit
    if current_user_role in [UserRole.SITE_ENGINEER, UserRole.SUB_CONTRACTOR]:
        return False

    # Project Manager, Admin, Accountant, SuperAdmin can edit in any status except transferred or declined
    if current_user_role in [UserRole.PROJECT_MANAGER, UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.SUPER_ADMIN]:
        if any(status in [PaymentStatus.TRANSFERRED, PaymentStatus.DECLINED] for status in status_history):
            return False
        return True

    return False


@payment_router.get("", tags=["Payments"], status_code=h_status.HTTP_200_OK)
def get_all_payments(
    db: Session = Depends(get_db),
    amount: Optional[float] = Query(None),
    project_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    recent: Optional[bool] = Query(False),
    person_id: Optional[UUID] = Query(None),
    item_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches payments, optionally filtering by:
      - amount
      - project_id
      - status
      - date range (start_date, end_date)
      - person_id
      - item_id
      - 'recent' (last 5, excluding 'transferred')
    
    Returns structured data with:
      - Payment details (description, remarks, date, etc.)
      - Project info (uuid, name)
      - Person info (name, account_number, ifsc_code, upi_number)
      - Created-by user info
      - Files
      - Items
      - Priority name
      - Status history
      - Edit history
      - Whether the current user can edit this payment
    """
    try:
        base_query = db.query(Payment.uuid).filter(Payment.is_deleted.is_(False))

        # Restrict to own payments if current_user is site_engineer/sub_contractor
        if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
            base_query = base_query.filter(Payment.created_by == current_user.uuid)

        # If 'recent' is True, take the last 5 payments (excluding 'transferred' below)
        if recent:
            base_query = base_query.order_by(desc(Payment.created_at)).limit(5).subquery()

        EditUser = aliased(User)

        # MAIN query: join everything we need (Projects, Person, Priority, PaymentFile, PaymentItem, etc.)
        query = (
            db.query(
                Payment,
                Project.name.label("project_name"),
                Person.name.label("person_name"),
                Person.account_number,
                Person.ifsc_code,
                Person.upi_number,
                User.name.label("user_name"),
                PaymentStatusHistory.status.label("history_status"),
                PaymentStatusHistory.created_at.label("history_created_at"),
                PaymentEditHistory.old_amount.label("edit_old_amount"),
                PaymentEditHistory.new_amount.label("edit_new_amount"),
                PaymentEditHistory.remarks.label("edit_remarks"),
                PaymentEditHistory.updated_at.label("edit_updated_at"),
                EditUser.name.label("edit_updated_by_name"),
                EditUser.role.label("edit_updated_by_role"),
                Priority.priority.label("priority_name"),  # <-- Priority name
            )
            .outerjoin(Project, Payment.project_id == Project.uuid)
            .outerjoin(Person, Payment.person == Person.uuid)
            .outerjoin(User, Payment.created_by == User.uuid)
            .outerjoin(PaymentFile)
            .outerjoin(PaymentItem, Payment.uuid == PaymentItem.payment_id)
            .outerjoin(Item, PaymentItem.item_id == Item.uuid)
            .outerjoin(PaymentStatusHistory, Payment.uuid == PaymentStatusHistory.payment_id)
            .outerjoin(PaymentEditHistory, Payment.uuid == PaymentEditHistory.payment_id)
            .outerjoin(EditUser, PaymentEditHistory.updated_by == EditUser.uuid)
            # NEW: join Priority so we can display priority name
            .outerjoin(Priority, Payment.priority_id == Priority.uuid)
            .filter(Payment.is_deleted.is_(False))
            .order_by(Payment.created_at.desc())
        )

        # Additional restriction if user is site_engineer/sub_contractor
        if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
            query = query.filter(Payment.created_by == current_user.uuid)

        # Exclude 'transferred' in "recent" & keep only the last 5 from base_query
        if recent:
            transferred_sub = (
                db.query(PaymentStatusHistory.payment_id)
                .filter(PaymentStatusHistory.status == "transferred")
                .subquery()
            )
            query = query.filter(~Payment.uuid.in_(transferred_sub))
            query = query.filter(Payment.uuid.in_(db.query(base_query.c.uuid)))

        # Apply optional filters
        if amount is not None:
            query = query.filter(Payment.amount == amount)
        if project_id is not None:
            query = query.filter(Payment.project_id == project_id)
        if status is not None:
            query = query.filter(Payment.status == status)

        # Handle date-range filters properly
        if start_date is not None and end_date is not None:
            # Make end_date inclusive to end of that day
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Payment.created_at.between(start_date, end_date))
        else:
            if start_date is not None:
                query = query.filter(Payment.created_at >= start_date)
            if end_date is not None:
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Payment.created_at <= end_date)

        if person_id is not None:
            query = query.filter(Payment.person == person_id)
        if item_id is not None:
            query = query.filter(PaymentItem.item_id == item_id)

        results = query.all()

        # We'll group our data by Payment UUID
        grouped_data = defaultdict(
            lambda: {
                "row_data": None,
                "statuses": [],
                "status_seen": set(),
                "edits": [],
                "edits_seen": set()
            }
        )

        for row in results:
            payment_obj = row[0]  # The Payment model instance
            if not grouped_data[payment_obj.uuid]["row_data"]:
                grouped_data[payment_obj.uuid]["row_data"] = row

            # Collect status history
            history_status = row.history_status
            history_created_at = row.history_created_at
            if history_status and history_created_at:
                date_str = history_created_at.strftime("%Y-%m-%d %H:%M:%S")
                status_key = (history_status, date_str)
                if status_key not in grouped_data[payment_obj.uuid]["status_seen"]:
                    grouped_data[payment_obj.uuid]["status_seen"].add(status_key)
                    grouped_data[payment_obj.uuid]["statuses"].append(
                        {"status": history_status, "date": date_str}
                    )

            # Collect edit histories
            if row.edit_old_amount is not None and row.edit_new_amount is not None:
                edit_key = (
                    row.edit_old_amount,
                    row.edit_new_amount,
                    row.edit_remarks,
                    row.edit_updated_at,
                    row.edit_updated_by_name,
                    row.edit_updated_by_role
                )
                if edit_key not in grouped_data[payment_obj.uuid]["edits_seen"]:
                    grouped_data[payment_obj.uuid]["edits_seen"].add(edit_key)
                    grouped_data[payment_obj.uuid]["edits"].append({
                        "old_amount": row.edit_old_amount,
                        "new_amount": row.edit_new_amount,
                        "remarks": row.edit_remarks,
                        "updated_at": row.edit_updated_at.strftime("%Y-%m-%d %H:%M:%S")
                        if row.edit_updated_at else None,
                        "updated_by": {
                            "name": row.edit_updated_by_name,
                            "role": row.edit_updated_by_role
                        }
                    })

        # Build final list of payments
        payments_data = []

        for payment_uuid, data in grouped_data.items():
            data["edits"].reverse()
            row = data["row_data"]
            payment = row[0]

            # Gather all statuses for the can_edit_payment logic
            status_list = [entry["status"] for entry in data["statuses"]]

            project_name = row.project_name
            person_name = row.person_name
            user_name = row.user_name

            # priority name from joined table
            priority_name = row.priority_name

            # Files (excluding is_approval_upload)
            file_urls = []
            if payment.payment_files:
                for f in payment.payment_files:
                    if not f.is_approval_upload:
                        filename = os.path.basename(f.file_path)
                        file_url = f"{constants.HOST_URL}/uploads/payments/{filename}"
                        file_urls.append(file_url)

            # Items
            item_names = []
            if payment.payment_items:
                item_names = [p_item.item.name for p_item in payment.payment_items if p_item.item]

            # Return parent's data if any
            parent_data = get_parent_account_data(person_id=payment.person, db=db)

            # Payment response build-up
            payments_data.append({
                **PaymentsResponse(
                    uuid=payment.uuid,
                    amount=payment.amount,
                    description=payment.description,
                    project={
                        "uuid": str(payment.project_id),
                        "name": project_name
                    } if payment.project_id else None,
                    person={
                        "uuid": str(parent_data.uuid),
                        "name": parent_data.name
                    } if parent_data else None,
                    payment_details={
                        "person_uuid": str(payment.person) if payment.person else None,
                        "name": person_name,
                        "account_number": str(row.account_number) if row.account_number else None,
                        "ifsc_code": row.ifsc_code if row.ifsc_code else None,
                        "upi_number": row.upi_number if row.upi_number else None
                    },
                    created_by={
                        "uuid": str(payment.created_by),
                        "name": user_name
                    } if payment.created_by else None,
                    files=file_urls,
                    items=item_names,
                    remarks=payment.remarks,
                    status_history=[StatusDatePair(**h) for h in data["statuses"]],
                    current_status=payment.status,
                    created_at=payment.created_at.strftime("%Y-%m-%d"),
                    update_remarks=payment.update_remarks,
                    latitude=payment.latitude,
                    longitude=payment.longitude,
                    transferred_date=(
                        payment.transferred_date.strftime("%Y-%m-%d")
                        if payment.transferred_date else None
                    ),
                    payment_history=data["edits"]
                ).model_dump(),
                "priority_name": priority_name,  # <--- Add to output
                "edit": can_edit_payment(status_list, current_user.role)
            })
        send_push_notification(
            registration_token="TOKEN",
            title="Get Payment",
            body="BODY",
            data={}
        )
        return PaymentServiceResponse(
            data=payments_data,
            message="Recent Payments fetched successfully." if recent else "All Payments fetched successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        print(f"Error in get_all_payments API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.put("/cancel-status")
def cancel_payment_status(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if current_user.role not in [
            UserRole.PROJECT_MANAGER.value,
            UserRole.ACCOUNTANT.value,
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value,
        ]:
            return PaymentServiceResponse(
                data=None,
                message="You are not authorized to cancel payment status.",
                status_code=403,
            ).model_dump()

        payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
        if not payment:
            return PaymentServiceResponse(
                data=None,
                message="Payment not found.",
                status_code=404,
            ).model_dump()

        # Prevent cancellation if last status is 'transferred'
        history_entries = (
            db.query(PaymentStatusHistory)
            .filter(PaymentStatusHistory.payment_id == payment_id)
            .order_by(PaymentStatusHistory.created_at.desc())
            .all()
        )

        if len(history_entries) <= 1:
            return PaymentServiceResponse(
                data=None,
                message="Cannot cancel the only status in history.",
                status_code=400,
            ).model_dump()

        last_status_entry = history_entries[0]

        if last_status_entry.status == PaymentStatus.TRANSFERRED.value:
            return PaymentServiceResponse(
                data=None,
                message="Transferred status cannot be canceled.",
                status_code=400,
            ).model_dump()

        previous_status = history_entries[1].status

        # Delete the last status record
        db.delete(last_status_entry)

        # Update payment current status to previous
        payment.status = previous_status

        # Add log entry
        db.add(
            Log(
                uuid=str(uuid4()),
                entity="Payment",
                action="Cancel Last Status",
                entity_id=payment_id,
                performed_by=current_user.uuid,
            )
        )

        db.commit()

        return PaymentServiceResponse(
            data=None,
            message="Last payment status cancelled and reverted successfully.",
            status_code=200,
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500,
        ).model_dump()


@payment_router.put("/approve")
def approve_payment(
    payment_id: UUID,
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Approve payment and optionally upload files (pdf, images, etc.) related to approval.
    """
    try:
        # 1) Check user role
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
            UserRole.SITE_ENGINEER.value,
            UserRole.ACCOUNTANT.value
        ]:
            return PaymentServiceResponse(
                data=None,
                message=constants.CANT_APPROVE_PAYMENT,
                status_code=403
            ).model_dump()

        # 2) Find the payment
        payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
        if not payment:
            return PaymentServiceResponse(
                data=None,
                message=constants.PAYMENT_NOT_FOUND,
                status_code=404
            ).model_dump()

        # 3) Get the next status from the mapping
        status = constants.RoleStatusMapping.get(current_user.role)
        if not status:
            return PaymentServiceResponse(
                data=None,
                message="Invalid role for updating payment status.",
                status_code=400
            ).model_dump()

        # 3a) Check if this status already exists for this payment
        existing_status_entry = (
            db.query(PaymentStatusHistory)
            .filter(
                PaymentStatusHistory.payment_id == payment.uuid,
                PaymentStatusHistory.status == status
            )
            .first()
        )
        if existing_status_entry:
            return PaymentServiceResponse(
                data=None,
                message=f"Status '{status}' has already been set once for this payment.",
                status_code=400
            ).model_dump()

        # 4) Create a status history entry
        payment_status = PaymentStatusHistory(
            payment_id=payment_id,
            status=status,
            created_by=current_user.uuid
        )
        db.add(payment_status)

        # 5) Update Payment table's status
        payment.status = status
        if status == "transferred":
            payment.transferred_date = datetime.now()
            # If it's a self-payment, update khatabook balance
            if payment.self_payment:
                user_balance = db.query(KhatabookBalance).filter(
                    KhatabookBalance.user_uuid == payment.created_by
                ).first()
                if not user_balance:
                    user_balance = KhatabookBalance(
                        user_uuid=payment.created_by,
                        balance=0.0
                    )
                    db.add(user_balance)
                user_balance.balance += payment.amount

        # 6) Handle optional file uploads
        if files:
            # or wherever you store admin approval files
            upload_dir = constants.UPLOAD_DIR_ADMIN
            os.makedirs(upload_dir, exist_ok=True)
            for file in files:
                file_path = os.path.join(upload_dir, file.filename)
                with open(file_path, "wb") as buffer:
                    buffer.write(file.file.read())

                # Mark these files as approval uploads
                db.add(
                    PaymentFile(
                        payment_id=payment.uuid,
                        file_path=file_path,
                        is_approval_upload=True  # <-- Flag it here
                    )
                )

        # 7) Add a log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Payment",
            action=status,
            entity_id=payment_id,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)

        # Commit everything
        db.commit()

        return PaymentServiceResponse(
            data=None,
            message="Payment approved successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.put("/decline")
def decline_payment(
    payment_id: UUID,
    remarks: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        """Decline a payment request with optional remarks."""

        # 1) Check user role
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
            UserRole.SITE_ENGINEER.value,
            UserRole.ACCOUNTANT.value
        ]:
            return PaymentServiceResponse(
                data=None,
                message=constants.CANT_DECLINE_PAYMENTS,
                status_code=403
            ).model_dump()
        # 2) Find the payment
        payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
        if not payment:
            return PaymentServiceResponse(
                data=None,
                message=constants.PAYMENT_NOT_FOUND,
                status_code=404
            ).model_dump()

        # 3) Check if already declined
        existing_status_entry = (
            db.query(PaymentStatusHistory)
            .filter(
                PaymentStatusHistory.payment_id == payment.uuid,
                PaymentStatusHistory.status == PaymentStatus.DECLINED.value
            )
            .first()
        )
        if existing_status_entry:
            return PaymentServiceResponse(
                data=None,
                message="Payment has already been declined.",
                status_code=400
            ).model_dump()

        # 4) Create a status history entry
        payment_status = PaymentStatusHistory(
            payment_id=payment_id,
            status=PaymentStatus.DECLINED.value,
            created_by=current_user.uuid
        )
        db.add(payment_status)
        db.flush()
        # 5) Update Payment table's status
        payment.status = PaymentStatus.DECLINED.value
        if remarks:
            payment.remarks = remarks

        # 6) Log the action
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Payment",
            action="Declined",
            entity_id=payment_id,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.flush()
        db.commit()
        return PaymentServiceResponse(
            data=None,
            message="Payment declined successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.delete("")
def delete_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        """Delete a payment request."""
        payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
        if not payment:
            return PaymentServiceResponse(
                data=None,
                status_code=404,
                message=constants.PAYMENT_NOT_FOUND
            )

        payment.is_deleted = True
        db.commit()
        return PaymentServiceResponse(
            data=None,
            message="Payment request deleted successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        print(f"Error in delete_payment API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.post(
    "/person", status_code=h_status.HTTP_201_CREATED, tags=["Payments"]
)
def create_person(
    request_data: CreatePerson,
    db: Session = Depends(get_db),
):
    try:
        if request_data.account_number and request_data.ifsc_code:
            existing_person = db.query(Person).filter(
                (Person.account_number == request_data.account_number) |
                (Person.ifsc_code == request_data.ifsc_code)
            ).first()
        else:
            existing_person = db.query(Person).filter(
                (Person.phone_number == request_data.phone_number) |
                (Person.upi_number == request_data.upi_number)
            ).first()

        if existing_person:
            return PaymentServiceResponse(
                data=None,
                status_code=400,
                message=constants.PERSON_EXISTS
            ).model_dump()

        # Validate parent_id if provided
        parent = None
        if request_data.parent_id:
            parent = db.query(Person).filter(Person.uuid == request_data.parent_id, Person.is_deleted.is_(False)).first()
            if not parent:
                return PaymentServiceResponse(
                    data=None,
                    status_code=400,
                    message="Parent account not found."
                ).model_dump()

        new_person = Person(
            name=request_data.name,
            account_number=request_data.account_number,
            ifsc_code=request_data.ifsc_code,
            phone_number=request_data.phone_number,
            parent_id=request_data.parent_id,  # Link to parent account
            upi_number=request_data.upi_number
        )

        db.add(new_person)
        db.flush()

        generated_uuid = new_person.uuid

        db.commit()
        return PaymentServiceResponse(
            data=str(generated_uuid),
            message="Person created successfully.",
            status_code=201
        ).model_dump()

    except HTTPException as e:
        raise e

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.get(
    "/persons", status_code=h_status.HTTP_200_OK, tags=["Payments"]
)
def get_all_persons(
    name: str = Query(None),
    phone_number: str = Query(None),
    account_number: str = Query(None),
    ifsc_code: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Person).filter(
            Person.is_deleted.is_(False),
            Person.parent_id.is_(None)
        )

        if name:
            query = query.filter(Person.name.ilike(f"%{name}%"))
        if phone_number:
            query = query.filter(Person.phone_number == phone_number)
        if account_number:
            query = query.filter(Person.account_number == account_number)
        if ifsc_code:
            query = query.filter(Person.ifsc_code == ifsc_code)

        # Exclude the current user's Person record if it exists:
        query = query.filter(or_(
            Person.user_id.is_(None),
            Person.user_id != current_user.uuid
        ))

        persons = query.all()
        persons_data = []

        for person in persons:
            persons_data.append(
                {
                    "uuid": person.uuid,
                    "name": person.name,
                    "account_number": person.account_number,
                    "ifsc_code": person.ifsc_code,
                    "phone_number": person.phone_number,
                    "parent_id": person.parent_id,
                    "upi_number": person.upi_number,
                    "secondary_accounts": [
                        {
                            "uuid": child.uuid,
                            "name": child.name,
                            "account_number": child.account_number,
                            "ifsc_code": child.ifsc_code,
                            "phone_number": child.phone_number,
                            "upi_number": child.upi_number
                        }
                        for child in person.children
                    ]
                }
            )

        return PaymentServiceResponse(
            data=persons_data,
            message="All persons info fetched successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        traceback.print_exc()
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.put(
    "/persons/delete",
    status_code=h_status.HTTP_204_NO_CONTENT,
    tags=["Payments"],
)
def delete_person(person_uuid: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        person = db.query(Person).filter(Person.uuid == person_uuid).first()

        if not person:
            raise HTTPException(
                status_code=h_status.HTTP_404_NOT_FOUND,
                detail="Person Does Not Exist",
            )
        person.is_deleted = True
        log_entry = Log(
            uuid=str(uuid4()),
            entity="Person",
            action="Delete",
            entity_id=person_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        return PaymentServiceResponse(
            data=None,
            message="Person deleted successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        traceback.print_exc()
        print(f"Error in delete_person API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.post("/items", tags=["Items"], status_code=201)
def create_item(
    name: str,
    list_tag: Optional[ItemListTag] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        new_item = Item(
            name=name,
            category=category,
            list_tag=list_tag
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        return PaymentServiceResponse(
            data={"item_uuid": str(new_item.uuid)},
            message="Item created successfully.",
            status_code=201
        ).model_dump()
    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error creating item: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.get("/items", tags=["Items"], status_code=200)
def list_items(db: Session = Depends(get_db)):
    try:
        items = db.query(Item).all()
        items_data = [{"uuid": str(item.uuid), "name": item.name, "category": item.category, "list_tag": item.list_tag} for item in items]

        return PaymentServiceResponse(
            data=items_data,
            message="All items fetched successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        return PaymentServiceResponse(
            data=None,
            message=f"Error fetching items: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.delete("/items/{item_uuid}", tags=["Items"], status_code=200)
def delete_item(item_uuid: UUID, db: Session = Depends(get_db)):
    try:
        item = db.query(Item).filter(Item.uuid == item_uuid).first()

        if not item:
            return PaymentServiceResponse(
                data=None,
                message="Item not found.",
                status_code=404
            ).model_dump()

        db.delete(item)
        db.commit()

        return PaymentServiceResponse(
            data={"deleted_item_uuid": str(item_uuid)},
            message="Item deleted successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error deleting item: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.post("/priority", status_code=201)
def create_priority(priority_name: str, db: Session = Depends(get_db)):
    new_priority = Priority(priority=priority_name)
    db.add(new_priority)
    db.commit()
    db.refresh(new_priority)
    response = {"priority_uuid": str(new_priority.uuid), "priority": new_priority.priority}
    return PaymentServiceResponse(
        data=response,
        message="priority created successfully",
        status_code=201
    ).model_dump()


@payment_router.get("/priority", status_code=200)
def list_priorities(db: Session = Depends(get_db)):
    priorities = db.query(Priority).filter(Priority.is_deleted.is_(False)).all()
    response = [{"uuid": str(p.uuid), "priority": p.priority} for p in priorities]
    return PaymentServiceResponse(
        data=response,
        message="priorities fetched successfully.",
        status_code=200
    ).model_dump()
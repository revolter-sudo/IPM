import os
import traceback
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    Form
)
from fastapi import status as h_status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, case, func
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
    Priority,
    BalanceDetail
)
import logging
import logging
from src.app.schemas.auth_service_schamas import UserRole
from uuid import uuid4
from src.app.schemas import constants
from src.app.schemas.payment_service_schemas import (
    CreatePerson,
    PaymentsResponse,
    PaymentStatus,
    PaymentServiceResponse,
    CreatePaymentRequest,
    PaymentUpdateSchema,
    StatusDatePair,
    ItemListTag,
    UpdatePerson,
    UpdateItemSchema
)
from src.app.notification.notification_service import send_push_notification
from src.app.notification.notification_schemas import NotificationMessage
from src.app.notification.notification_service import send_push_notification
from src.app.notification.notification_schemas import NotificationMessage
from sqlalchemy.orm import aliased
from sqlalchemy import desc
from src.app.services.auth_service import get_current_user
from src.app.services.project_service import create_project_balance_entry
import json
from collections import defaultdict

logging.basicConfig(level=logging.INFO)

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


def notify_create_payment(amount: int, user: User, db: Session):
    try:
        roles_to_notify = [
            UserRole.ACCOUNTANT.value,
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value
        ]
        people_to_notify = db.query(User).filter(
            User.role.in_(roles_to_notify),
            User.is_deleted.is_(False)
        )
        if user.role in roles_to_notify:
            # Then in a second line, exclude the current user
            people_to_notify = people_to_notify.filter(User.uuid != user.uuid)

        people = people_to_notify.all()
        notification = NotificationMessage(
            title="Payment Request",
            body=f"Payment of {amount} amount requested by {user.name}"
        )
        for person in people:
            send_push_notification(
                topic=str(person.uuid),
                title=notification.title,
                body=notification.body
            )
        logging.info(
            f"{len(people)} Users were notified for this payment request"
        )
        return True
    except Exception as e:
        return PaymentServiceResponse(
            data=None,
            message=f"Error in notify_create_payment: {str(e)}",
            status_code=500
        ).model_dump()





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
        request_data = json.loads(request)
        payment_request = CreatePaymentRequest(**request_data)

        # Validate Project
        project = db.query(Project).filter(
            Project.uuid == payment_request.project_id).first()
        project = db.query(Project).filter(
            Project.uuid == payment_request.project_id).first()
        if not project:
            return PaymentServiceResponse(
                status_code=404,
                data=None,
                message="Project not found."
            ).model_dump()

        # If it's a self-payment, overwrite the `person` field with current_user's Person (if any)
        # so you don't rely on the client to supply a person UUID
        # if payment_request.self_payment:
        #     if not current_user.person:
        #         # If user does not have a linked Person row, decide how to handle:
        #         return PaymentServiceResponse(
        #             status_code=400,
        #             data=None,
        #             message="Cannot create self-payment because current user has no linked Person record."
        #         ).model_dump()
        #     # Force the Payment.person to the current_user’s Person.uuid
        #     payment_request.person = current_user.person.uuid

        # Create Payment
        new_payment = Payment(
            amount=payment_request.amount,
            description=payment_request.description,
            project_id=payment_request.project_id,
            status='requested',
            remarks=payment_request.remarks,
            created_by=current_user.uuid,
            person=payment_request.person,            # might be overwritten for self_payment
            self_payment=payment_request.self_payment,  # store the flag
            latitude=payment_request.latitude,
            longitude=payment_request.longitude,
            priority_id=payment_request.priority_id,
        )
        db.add(new_payment)
        db.flush()  # flush so new_payment.uuid is available
        current_payment_uuid = new_payment.uuid

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
        notification = notify_create_payment(
            amount=payment_request.amount,
            user=current_user,
            db=db
        )
        if not notification:
            logging.error(
                "Something went wrong while sending create payment notification")
        return PaymentServiceResponse(
            data={"payment_uuid": current_payment_uuid},
            message="Payment created successfully.",
            status_code=201
        ).model_dump()

    except Exception as e:
        traceback.print_exc()
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
    # <--- If you want to store who updated
    current_user: User = Depends(get_current_user),
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
    # Always store the latest remark in Payment
    payment.update_remarks = payload.remark
    # Always store the latest remark in Payment
    payment.update_remarks = payload.remark

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


### ---------------------------------------------------------------------------------------------------------
def build_recent_subquery(db: Session, current_user: User, recent: bool):
    """
    Builds a subquery of Payment UUIDs if `recent` is True.
    Restricts site_eng / sub_con to only see their own Payment records.
    Returns a subquery object.
    """
    recent_status = [PaymentStatus.DECLINED.value, PaymentStatus.TRANSFERRED.value]

    base_q = db.query(Payment.uuid).filter(
        Payment.is_deleted.is_(False),
        Payment.status.not_in(recent_status)
    )

    # Restrict to own payments if site eng / sub con
    if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
        base_q = base_q.filter(Payment.created_by == current_user.uuid)

    if recent:
        # Get last 5 payments (by created_at desc)
        base_q = base_q.order_by(desc(Payment.created_at)).limit(5)

    return base_q.subquery()


def build_main_payments_query(db: Session, pending_request: bool):
    """
    Builds the main query that pulls Payment + joined entities, plus
    the columns we need for status/edit histories, person data, etc.

    If pending_request=False, we add a default `.order_by(Payment.created_at.desc())`.
    If pending_request=True, we do not apply that ordering here, because
    we'll handle a custom multi-level ordering in `apply_pending_request_logic`.
    """
    EditUser = aliased(User)
    StatusUser = aliased(User)

    query = (
        db.query(
            Payment,
            Project.name.label("project_name"),
            Person.name.label("person_name"),
            Person.account_number,
            Person.ifsc_code,
            Person.upi_number,
            User.name.label("user_name"),  # The user who created Payment
            PaymentStatusHistory.status.label("history_status"),
            PaymentStatusHistory.created_at.label("history_created_at"),
            StatusUser.name.label("status_created_by_name"),
            StatusUser.role.label("status_created_by_role"),
            PaymentEditHistory.old_amount.label("edit_old_amount"),
            PaymentEditHistory.new_amount.label("edit_new_amount"),
            PaymentEditHistory.remarks.label("edit_remarks"),
            PaymentEditHistory.updated_at.label("edit_updated_at"),
            EditUser.name.label("edit_updated_by_name"),
            EditUser.role.label("edit_updated_by_role"),
            Priority.priority.label("priority_name"),
        )
        .outerjoin(Project, Payment.project_id == Project.uuid)
        .outerjoin(Person, Payment.person == Person.uuid)
        .outerjoin(User, Payment.created_by == User.uuid)
        .outerjoin(
            PaymentFile,
            and_(
                PaymentFile.payment_id == Payment.uuid,
                PaymentFile.is_deleted.is_(False),
            ),
        )
        .outerjoin(
            PaymentItem,
            and_(
                PaymentItem.payment_id == Payment.uuid,
                PaymentItem.is_deleted.is_(False),
            ),
        )
        .outerjoin(Item, PaymentItem.item_id == Item.uuid)
        .outerjoin(
            PaymentStatusHistory,
            and_(
                PaymentStatusHistory.payment_id == Payment.uuid,
                PaymentStatusHistory.is_deleted.is_(False),
            ),
        )
        .outerjoin(StatusUser, StatusUser.uuid == PaymentStatusHistory.created_by)
        .outerjoin(
            PaymentEditHistory,
            and_(
                PaymentEditHistory.payment_id == Payment.uuid,
                PaymentEditHistory.is_deleted.is_(False),
            ),
        )
        .outerjoin(EditUser, EditUser.uuid == PaymentEditHistory.updated_by)
        .outerjoin(
            Priority,
            and_(
                Payment.priority_id == Priority.uuid,
                Priority.is_deleted.is_(False)
            ),
        )
        .filter(Payment.is_deleted.is_(False))
    )

    # If not pending_request, default to date desc here
    if not pending_request:
        query = query.order_by(Payment.created_at.desc())

    return query


def apply_role_restrictions(query, current_user: User):
    """
    If user is site engineer or sub contractor, restrict Payment.created_by = current_user.uuid
    """
    if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
        query = query.filter(Payment.created_by == current_user.uuid)
    return query


def exclude_transferred_if_recent(query, db: Session, recent: bool, base_subquery):
    """
    If recent == True, exclude 'transferred' from PaymentStatusHistory
    and only keep Payment.uuids that are in the base_subquery.
    """
    if recent:
        transferred_sub = (
            db.query(PaymentStatusHistory.payment_id)
            .filter(PaymentStatusHistory.status == "transferred")
            .subquery()
        )
        query = query.filter(~Payment.uuid.in_(transferred_sub))
        query = query.filter(Payment.uuid.in_(db.query(base_subquery.c.uuid)))
    return query


def apply_pending_request_logic(query, pending_request: bool, current_user: User):
    """
    If pending_request == True, we filter + order by status:
      - Site Eng / SubCon / Project Mgr => only "requested"
      - Admin => "verified" first, then "requested"
      - Accountant / SuperAdmin => "approved", "verified", "requested"

    Then we do multi-level ordering: first by 'status_order' (ASC),
    then by Payment.created_at (DESC).
    """
    if not pending_request:
        return query

    role = current_user.role
    if role in [
        UserRole.SITE_ENGINEER.value,
        UserRole.SUB_CONTRACTOR.value,
        UserRole.PROJECT_MANAGER.value,
    ]:
        statuses = ["requested"]
        status_order = case(
            (Payment.status == "requested", 0),
            else_=9999
        )
    elif role == UserRole.ADMIN.value:
        statuses = ["verified", "requested"]
        status_order = case(
            (Payment.status == "verified", 0),
            (Payment.status == "requested", 1),
            else_=9999
        )
    elif role in [UserRole.ACCOUNTANT.value, UserRole.SUPER_ADMIN.value]:
        statuses = ["approved", "verified", "requested"]
        status_order = case(
            (Payment.status == "approved", 0),
            (Payment.status == "verified", 1),
            (Payment.status == "requested", 2),
            else_=9999
        )
    else:
        return query  # Unrecognized role => do nothing special

    query = query.filter(Payment.status.in_(statuses))
    query = query.order_by(status_order, Payment.created_at.desc())

    return query


def apply_filters(
    query,
    amount: Optional[float],
    project_id: Optional[UUID],
    status: Optional[List[str]],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    person_id: Optional[UUID],
    item_id: Optional[UUID],
    from_uuid: Optional[UUID],
    to_uuid: Optional[UUID],
):
    """
    Applies any additional optional filters (amount, project, status,
    date range, person, item, from/to UUID).
    """
    if amount is not None:
        query = query.filter(Payment.amount == amount)
    if project_id is not None:
        query = query.filter(Payment.project_id == project_id)
    if status is not None:
        query = query.filter(Payment.status.in_(status))

    # Date range filters
    if start_date is not None and end_date is not None:
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

    if from_uuid is not None:
        query = query.filter(Payment.created_by == from_uuid)
    if to_uuid is not None:
        query = query.filter(Person.uuid == to_uuid)

    return query


def apply_accountant_amount_restriction(query, current_user: User, pending_request: bool, recent: bool):
    """
    If user is accountant and (pending_request == True OR recent == True),
    only show payments where Payment.amount <= 10000.
    """
    if current_user.role == UserRole.ACCOUNTANT.value and (pending_request or recent):
        query = query.filter(Payment.amount <= 10000)
    return query


def group_query_results(results):
    """
    Groups Payment rows by Payment.uuid, collecting status history and edit history
    in the same manner as the old logic.
    """
    grouped_data = defaultdict(
        lambda: {
            "row_data": None,
            "statuses": [],
            "status_seen": set(),
            "edits": [],
            "edits_seen": set(),
        }
    )

    for row in results:
        payment_obj = row[0]  # Payment model instance

        if not grouped_data[payment_obj.uuid]["row_data"]:
            grouped_data[payment_obj.uuid]["row_data"] = row

        # Collect status history
        history_status = row.history_status
        history_created_at = row.history_created_at
        status_created_by_name = row.status_created_by_name
        status_created_by_role = row.status_created_by_role

        if history_status and history_created_at:
            date_str = history_created_at.strftime("%Y-%m-%d %H:%M:%S")
            status_key = (history_status, date_str, status_created_by_name, status_created_by_role)
            if status_key not in grouped_data[payment_obj.uuid]["status_seen"]:
                grouped_data[payment_obj.uuid]["status_seen"].add(status_key)
                grouped_data[payment_obj.uuid]["statuses"].append({
                    "status": history_status,
                    "date": date_str,
                    "created_by": status_created_by_name,
                    "role": status_created_by_role
                })

        # Collect edit histories
        if row.edit_old_amount is not None and row.edit_new_amount is not None:
            edit_key = (
                row.edit_old_amount,
                row.edit_new_amount,
                row.edit_remarks,
                row.edit_updated_at,
                row.edit_updated_by_name,
                row.edit_updated_by_role,
            )
            if edit_key not in grouped_data[payment_obj.uuid]["edits_seen"]:
                grouped_data[payment_obj.uuid]["edits_seen"].add(edit_key)
                grouped_data[payment_obj.uuid]["edits"].append({
                    "old_amount": row.edit_old_amount,
                    "new_amount": row.edit_new_amount,
                    "remarks": row.edit_remarks,
                    "updated_at": (
                        row.edit_updated_at.strftime("%Y-%m-%d %H:%M:%S")
                        if row.edit_updated_at else None
                    ),
                    "updated_by": {
                        "name": row.edit_updated_by_name,
                        "role": row.edit_updated_by_role
                    }
                })

    return grouped_data


def assemble_payments_response(grouped_data, db: Session, current_user: User):
    """
    Assembles the final list of payment response objects,
    including status histories and edit histories.
    """
    payments_data = []

    for payment_uuid, data in grouped_data.items():
        data["edits"].reverse()
        row = data["row_data"]
        payment = row[0]

        status_list = [entry["status"] for entry in data["statuses"]]

        project_name = row.project_name
        person_name = row.person_name
        user_name = row.user_name
        priority_name = row.priority_name

        # ----------------------------------------------------------- files
        file_urls, approval_files = [], []
        if payment.payment_files:
            for f in payment.payment_files:
                file_url = f"{constants.HOST_URL}/{f.file_path}"
                (approval_files if f.is_approval_upload else file_urls).append(file_url)

        # ----------------------------------------------------------- items
        item_names = [
            p_item.item.name for p_item in payment.payment_items if p_item.item
        ] if payment.payment_items else []

        # ----------------------------------------------------------- parent account
        parent_data = get_parent_account_data(person_id=payment.person, db=db)

        # ----------------------------------------------------------- NEW → bank name
        bank_name = (
            payment.deducted_from_bank.name
            if payment.deducted_from_bank and payment.deducted_from_bank.name
            else None
        )

        # ----------------------------------------------------------- build response
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
            "priority_name": priority_name,
            "edit": can_edit_payment(status_list, current_user.role),
            "decline_remark": payment.decline_remark,
            "approval_files": approval_files,
            # ---------- NEW KEY ----------
            "transferred_from_bank": bank_name
        })

    return payments_data

@payment_router.get("", tags=["Payments"], status_code=200)
def get_all_payments(
    db: Session = Depends(get_db),
    amount: Optional[float] = Query(None),
    project_id: Optional[UUID] = Query(None),
    status: Optional[List[str]] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    recent: Optional[bool] = Query(False),
    person_id: Optional[UUID] = Query(None),
    item_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    from_uuid: Optional[UUID] = Query(None, description="UUID of the user who created the payment"),
    to_uuid: Optional[UUID] = Query(None, description="UUID of the person receiving the payment"),
    pending_request: Optional[bool] = Query(False, description="If true, show only role‑specific pending payments."),
    page: Optional[int] = Query(None, ge=1, description="Page number (10 rows per page, omit/null = all)"),
):
    """
    Three modes:
    1) recent=True            → last 5 payments (excl. transferred / declined) newest‑first
    2) pending_request=True   → role queue:   approved → verified → requested
    3) default                → full list, newest‑first

    In every mode we:
      • build an *ordered* list of UUIDs (with pagination)
      • fetch full rows & assemble the response
      • return records in that exact order
    """

    # ------------------------------------------------------------------ helpers
    def paginate(q):
        """return (uuid_list_in_order, total_count) after optional pagination"""
        total = q.count()
        if page:
            q = q.offset((page - 1) * 10).limit(10)
        return [r[0] for r in q.all()], total

    def order_records(selected_uuids, assembled_records):
        """Preserve the SQL ordering after JSON assembly"""
        by_id = {rec["uuid"]: rec for rec in assembled_records}
        return [by_id[u] for u in selected_uuids if u in by_id]

    def calculate_total_request_amount(db):
        """Calculate total amount of all payments with status requested, approved, verified, or transferred"""
        # Get all payments with the specified statuses, regardless of pagination
        query = db.query(func.sum(Payment.amount)).filter(
            Payment.is_deleted.is_(False),
            Payment.status.in_([
                PaymentStatus.REQUESTED.value,
                PaymentStatus.APPROVED.value,
                PaymentStatus.VERIFIED.value,
                PaymentStatus.TRANSFERRED.value
            ])
        )

        # Apply the same filters as the main query
        if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
            query = query.filter(Payment.created_by == current_user.uuid)
        if project_id is not None:
            query = query.filter(Payment.project_id == project_id)
        if status is not None:
            query = query.filter(Payment.status.in_(status))
        if start_date and end_date:
            end_date_with_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Payment.created_at.between(start_date, end_date_with_time))
        else:
            if start_date:
                query = query.filter(Payment.created_at >= start_date)
            if end_date:
                end_date_with_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Payment.created_at <= end_date_with_time)
        if from_uuid:
            query = query.filter(Payment.created_by == from_uuid)
        if person_id or to_uuid:
            query = query.join(Person, Payment.person ==
                               Person.uuid, isouter=True)
            if person_id:
                query = query.filter(Payment.person == person_id)
            if to_uuid:
                query = query.filter(Person.uuid == to_uuid)
        if item_id:
            query = query.join(
                PaymentItem,
                PaymentItem.payment_id == Payment.uuid, isouter=True
            ).filter(
                PaymentItem.is_deleted.is_(False),
                PaymentItem.item_id == item_id
            )

        return query.scalar() or 0.0

    def calculate_total_pending_amount(db):
        """Calculate total amount of all payments with status requested, approved, or verified (excluding transferred)"""
        # Get all payments with the specified statuses, regardless of pagination
        query = db.query(func.sum(Payment.amount)).filter(
            Payment.is_deleted.is_(False),
            Payment.status.in_([
                PaymentStatus.REQUESTED.value,
                PaymentStatus.APPROVED.value,
                PaymentStatus.VERIFIED.value
            ])
        )

        # Apply the same filters as the main query
        if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
            query = query.filter(Payment.created_by == current_user.uuid)
        if project_id is not None:
            query = query.filter(Payment.project_id == project_id)
        if status is not None:
            query = query.filter(Payment.status.in_(status))
        if start_date and end_date:
            end_date_with_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Payment.created_at.between(start_date, end_date_with_time))
        else:
            if start_date:
                query = query.filter(Payment.created_at >= start_date)
            if end_date:
                end_date_with_time = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                query = query.filter(Payment.created_at <= end_date_with_time)
        if from_uuid:
            query = query.filter(Payment.created_by == from_uuid)
        if person_id or to_uuid:
            query = query.join(Person, Payment.person == Person.uuid, isouter=True)
            if person_id:
                query = query.filter(Payment.person == person_id)
            if to_uuid:
                query = query.filter(Person.uuid == to_uuid)
        if item_id:
            query = query.join(
                PaymentItem,
                PaymentItem.payment_id == Payment.uuid, isouter=True
            ).filter(
                PaymentItem.is_deleted.is_(False),
                PaymentItem.item_id == item_id
            )

        return query.scalar() or 0.0

    # ------------------------------------------------------------------ 1) RECENT MODE
    if recent:
        base = (
            db.query(Payment.uuid)
              .filter(
                  Payment.is_deleted.is_(False),
                  Payment.status.notin_(
                      ["transferred", "declined"])  # exclude first!
            )

        )

        # role restriction
        if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
            base = base.filter(Payment.created_by == current_user.uuid)

        # accountants ≤10 000
        if current_user.role == UserRole.ACCOUNTANT.value:
            base = base.filter(Payment.amount <= 10_000)

        # Apply user-supplied filters
        if amount is not None:
            base = base.filter(Payment.amount == amount)
        if project_id is not None:
            base = base.filter(Payment.project_id == project_id)
        if status is not None:
            base = base.filter(Payment.status.in_(status))
        if start_date and end_date:
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            base = base.filter(Payment.created_at.between(start_date, end_date))
        else:
            if start_date:
                base = base.filter(Payment.created_at >= start_date)
            if end_date:
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                base = base.filter(Payment.created_at <= end_date)
        if from_uuid:
            base = base.filter(Payment.created_by == from_uuid)
        if person_id or to_uuid:
            base = base.join(Person, Payment.person == Person.uuid, isouter=True)
            if person_id:
                base = base.filter(Payment.person == person_id)
            if to_uuid:
                base = base.filter(Person.uuid == to_uuid)
        if item_id:
            base = base.join(PaymentItem,
                             PaymentItem.payment_id == Payment.uuid, isouter=True)\
                       .filter(PaymentItem.is_deleted.is_(False),
                               PaymentItem.item_id == item_id)

        # Apply ordering and limit AFTER all filters
        base = base.order_by(Payment.created_at.desc()).limit(5)

        uuids, total = paginate(base)

        # Calculate total amounts using the helper functions
        total_request_amount = calculate_total_request_amount(db)
        total_pending_amount = calculate_total_pending_amount(db)

        if not uuids:
            return PaymentServiceResponse(
                data={
                    "records": [],
                    "total_count": 0,
                    "total_request_amount": total_request_amount,
                    "total_pending_amount": total_pending_amount
                },
                message="No recent payments found.",
                status_code=200
            ).model_dump()

        main_q = build_main_payments_query(db, pending_request=False)\
            .filter(Payment.uuid.in_(uuids))
        results = main_q.all()
        grouped = assemble_payments_response(
            group_query_results(results), db, current_user)
        records_out = order_records(uuids, grouped)

        payload = {
            "records": records_out,
            "total_count": total,
            "total_request_amount": total_request_amount,
            "total_pending_amount": total_pending_amount
        }
        if page:
            payload.update({"page": page, "limit": 10})

        return PaymentServiceResponse(
            data=payload,
            message="Recent payments fetched successfully.",
            status_code=200
        ).model_dump()

    # ------------------------------------------------------------------ 2) PENDING‑REQUEST MODE
    if pending_request:
        role_status_map = {
            UserRole.ACCOUNTANT.value:  ["approved", "verified", "requested"],
            UserRole.SUPER_ADMIN.value: ["approved", "verified", "requested"],
            UserRole.ADMIN.value:       ["verified",  "requested"],
        }
        wanted_statuses = role_status_map.get(current_user.role, ["requested"])

        status_rank = {s: i for i, s in enumerate(wanted_statuses)}
        rank_expr = case(*[(Payment.status == s, r) for s, r in status_rank.items()],
                         else_=99)

        base = (
            db.query(Payment.uuid)
              .filter(
                  Payment.is_deleted.is_(False),
                  Payment.status.in_(wanted_statuses)
            )
        )

        # role restriction
        if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
            base = base.filter(Payment.created_by == current_user.uuid)

        # accountants ≤10 000 in queue view
        if current_user.role == UserRole.ACCOUNTANT.value:
            base = base.filter(Payment.amount <= 10_000)

        # user‑supplied filters (“normal” section reused):
        if amount is not None:
            base = base.filter(Payment.amount == amount)
        if project_id is not None:
            base = base.filter(Payment.project_id == project_id)
        if status is not None:
            base = base.filter(Payment.status.in_(status))
        if start_date and end_date:
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            base = base.filter(Payment.created_at.between(start_date, end_date))
        else:
            if start_date:
                base = base.filter(Payment.created_at >= start_date)
            if end_date:
                end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                base = base.filter(Payment.created_at <= end_date)
        if from_uuid:
            base = base.filter(Payment.created_by == from_uuid)
        if person_id or to_uuid:
            base = base.join(Person, Payment.person == Person.uuid, isouter=True)
            if person_id:
                base = base.filter(Payment.person == person_id)
            if to_uuid:
                base = base.filter(Person.uuid == to_uuid)
        if item_id:
            base = base.join(PaymentItem,
                             PaymentItem.payment_id == Payment.uuid, isouter=True)\
                       .filter(PaymentItem.is_deleted.is_(False),
                               PaymentItem.item_id == item_id)

        # ORDER: status_rank asc, then created_at desc
        base = base.order_by(rank_expr, Payment.created_at.desc())

        uuids, total = paginate(base)

        # Calculate total amounts using the helper functions
        total_request_amount = calculate_total_request_amount(db)
        total_pending_amount = calculate_total_pending_amount(db)

        if not uuids:
            return PaymentServiceResponse(
                data={
                    "records": [],
                    "total_count": 0,
                    "total_request_amount": total_request_amount,
                    "total_pending_amount": total_pending_amount
                },
                message="No pending payments.",
                status_code=200
            ).model_dump()

        main_q = build_main_payments_query(db, pending_request=True)\
            .filter(Payment.uuid.in_(uuids))
        results = main_q.all()
        grouped = assemble_payments_response(
            group_query_results(results), db, current_user)
        records_out = order_records(uuids, grouped)

        payload = {
            "records": records_out,
            "total_count": total,
            "total_request_amount": total_request_amount,
            "total_pending_amount": total_pending_amount
        }
        if page:
            payload.update({"page": page, "limit": 10})

        return PaymentServiceResponse(
            data=payload,
            message="Pending payments fetched successfully.",
            status_code=200
        ).model_dump()

    # ------------------------------------------------------------------ 3) NORMAL LIST
    base = (
        db.query(Payment.uuid)
          .filter(Payment.is_deleted.is_(False))
          .order_by(Payment.created_at.desc())
    )

    # role restriction
    if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
        base = base.filter(Payment.created_by == current_user.uuid)

    # --- same user‑supplied filters as above ---
    if amount is not None:
        base = base.filter(Payment.amount == amount)
    if project_id is not None:
        base = base.filter(Payment.project_id == project_id)
    if status is not None:
        base = base.filter(Payment.status.in_(status))
    if start_date and end_date:
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        base = base.filter(Payment.created_at.between(start_date, end_date))
    else:
        if start_date:
            base = base.filter(Payment.created_at >= start_date)
        if end_date:
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            base = base.filter(Payment.created_at <= end_date)
    if from_uuid:
        base = base.filter(Payment.created_by == from_uuid)
    if person_id or to_uuid:
        base = base.join(Person, Payment.person == Person.uuid, isouter=True)
        if person_id:
            base = base.filter(Payment.person == person_id)
        if to_uuid:
            base = base.filter(Person.uuid == to_uuid)
    if item_id:
        base = base.join(PaymentItem,
                         PaymentItem.payment_id == Payment.uuid, isouter=True)\
            .filter(PaymentItem.is_deleted.is_(False),
                    PaymentItem.item_id == item_id)

    # Calculate total amounts using the helper functions
    total_request_amount = calculate_total_request_amount(db)
    total_pending_amount = calculate_total_pending_amount(db)

    uuids, total = paginate(base)

    if not uuids:
        return PaymentServiceResponse(
            data={
                "records": [],
                "total_count": 0,
                "total_request_amount": total_request_amount,
                "total_pending_amount": total_pending_amount
            },
            message="No payments found.",
            status_code=200
        ).model_dump()

    main_q = build_main_payments_query(db, pending_request=False)\
        .filter(Payment.uuid.in_(uuids))
    grouped = assemble_payments_response(
        group_query_results(main_q.all()), db, current_user)
    records_out = order_records(uuids, grouped)

    payload = {
        "records": records_out,
        "total_count": total,
        "total_request_amount": total_request_amount,
        "total_pending_amount": total_pending_amount
    }
    if page:
        payload.update({"page": page, "limit": 10})

    return PaymentServiceResponse(
        data=payload,
        message="All payments fetched successfully.",
        status_code=200
    ).model_dump()
### ------------------------------------------------------------------------------------------------------------------------

@payment_router.delete("")
def delete_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
        if not payment:
            return PaymentServiceResponse(
                data=None,
                status_code=404,
                message="Payment not found."
            ).model_dump()

        # Soft-delete the Payment
        payment.is_deleted = True

        # Soft-delete PaymentFile
        db.query(PaymentFile).filter(PaymentFile.payment_id == payment.uuid).update(
            {PaymentFile.is_deleted: True}
        )

        # Soft-delete PaymentItem
        db.query(PaymentItem).filter(PaymentItem.payment_id == payment.uuid).update(
            {PaymentItem.is_deleted: True}
        )

        # Soft-delete PaymentStatusHistory
        db.query(PaymentStatusHistory).filter(
            PaymentStatusHistory.payment_id == payment.uuid
        ).update({PaymentStatusHistory.is_deleted: True})

        # Soft-delete PaymentEditHistory
        db.query(PaymentEditHistory).filter(
            PaymentEditHistory.payment_id == payment.uuid
        ).update({PaymentEditHistory.is_deleted: True})

        db.commit()

        return PaymentServiceResponse(
            data=None,
            message="Payment deleted successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


def notify_payment_status_update(
        amount: int,
        status: str,
        user: User,
        payment_user: UUID,
        db: Session
):
    roles_to_notify = [
        UserRole.ACCOUNTANT.value,
        UserRole.ADMIN.value,
        UserRole.SUPER_ADMIN.value,
        UserRole.PROJECT_MANAGER.value
    ]

    # 1) Base query: roles_to_notify OR payment_user
    people_to_notify = db.query(User).filter(
        or_(
            User.role.in_(roles_to_notify),
            User.uuid == payment_user
        ),
        User.is_deleted.is_(False)
    )

    # 2) Exclude current user if they're in that set
    if user.role in roles_to_notify:
        people_to_notify = people_to_notify.filter(User.uuid != user.uuid)

    # 3) If status is APPROVED or VERIFIED, exclude ALL Site Engineers & Sub-contractors
    if status in [PaymentStatus.APPROVED.value, PaymentStatus.VERIFIED.value, "approved", "verified"]:
        people_to_notify = people_to_notify.filter(
            ~User.role.in_([
                UserRole.SITE_ENGINEER.value,
                UserRole.SUB_CONTRACTOR.value
            ])
        )

    # 4) Now fetch and notify
    people = people_to_notify.all()
    notification = NotificationMessage(
        title="Payment Status Updated",
        body=f"Payment of {amount} {status} by {user.name}"
    )

    for person in people:
        send_push_notification(
            topic=str(person.uuid),
            title=notification.title,
            body=notification.body
        )
    logging.info(f"{len(people)} Users were notified for this payment request")
    return True


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
    bank_uuid: Optional[UUID] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Approve payment and optionally upload files (pdf, images, etc.) related to approval.
    If the status resolves to 'transferred', we must provide bank_uuid to deduct from that bank,
    and also store which bank was used in Payment.deducted_from_bank_uuid.

    IMPORTANT CHANGE:
    - We now allow adding a status entry even if the new status is "behind"
      the current Payment.status. In that scenario, we do NOT overwrite
      payment.status.
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

        # 3) Get the next status from the role -> status mapping
        #    e.g., Project Manager -> "verified", Admin -> "approved", Accountant -> "transferred"
        status = constants.RoleStatusMapping.get(current_user.role)
        if not status:
            return PaymentServiceResponse(
                data=None,
                message="Invalid role for updating payment status.",
                status_code=400
            ).model_dump()

        # 4) Always create a PaymentStatusHistory record
        payment_status = PaymentStatusHistory(
            payment_id=payment_id,
            status=status,
            created_by=current_user.uuid
        )
        db.add(payment_status)

        # 5) Only update payment table’s 'status' if `status` is ahead of the current payment.status
        status_order_map = {
            "requested": 1,
            "verified": 2,
            "approved": 3,
            "transferred": 4
        }

        def get_order(s: str) -> int:
            return status_order_map.get(s, 0)

        current_order = get_order(payment.status)
        new_order = get_order(status)

        if new_order > current_order:
            payment.status = status

            # If the new status is 'transferred', do the existing logic
            if status == "transferred":
                # We require the bank_uuid param for deduction
                if not bank_uuid:
                    return PaymentServiceResponse(
                        data=None,
                        message="Must provide bank_uuid when transferring payment.",
                        status_code=400
                    ).model_dump()

                payment.transferred_date = datetime.now()

                # For self-payment logic
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

                # Deduct from the chosen bank
                balance_obj = db.query(BalanceDetail).filter(
                    BalanceDetail.uuid == bank_uuid
                ).first()
                if not balance_obj:
                    return PaymentServiceResponse(
                        data=None,
                        message="No bank found for given bank_uuid.",
                        status_code=404
                    ).model_dump()

                balance_obj.balance -= payment.amount

                # Record in Payment which bank/cash account was used
                payment.deducted_from_bank_uuid = bank_uuid

        # 6) Handle optional file uploads
        if files:
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
                        is_approval_upload=True
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

        # 8) Commit changes
        db.commit()

        # 9) Send notifications
        notify_payment_status_update(
            amount=payment.amount,
            status=status,
            user=current_user,
            payment_user=payment.created_by,
            db=db
        )

        return PaymentServiceResponse(
            data=None,
            message="Payment status updated successfully",
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
            payment.decline_remark = remarks

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

        # 7) Send notification
        notify_payment_status_update(
            amount=payment.amount,
            status=PaymentStatus.DECLINED.value,
            user=current_user,
            payment_user=payment.created_by,
            db=db
        )

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



@payment_router.post(
    "/person", status_code=h_status.HTTP_201_CREATED, tags=["Payments"]
)
def create_person(
    request_data: CreatePerson,
    db: Session = Depends(get_db),
):
    try:
        if request_data.account_number:
            existing_person = db.query(Person).filter(
                (Person.account_number == request_data.account_number),
                (Person.is_deleted.is_(False))
            ).first()
            reason = "A person with the same account number already exists."
        else:
            if request_data.upi_number:
                existing_person = db.query(Person).filter(
                    (Person.phone_number == request_data.phone_number) |
                    (Person.upi_number == request_data.upi_number)
                ).first()
                reason = "Person with same phone number ot account number exists"
            else:
                existing_person = db.query(Person).filter(
                    (Person.phone_number == request_data.phone_number)
                ).first()
                reason = "Person with same phone number exists"
            if request_data.upi_number:
                existing_person = db.query(Person).filter(
                    (Person.phone_number == request_data.phone_number) |
                    (Person.upi_number == request_data.upi_number)
                ).first()
                reason = "Person with same phone number ot account number exists"
            else:
                existing_person = db.query(Person).filter(
                    (Person.phone_number == request_data.phone_number)
                ).first()
                reason = "Person with same phone number exists"

        if existing_person:
            return PaymentServiceResponse(
                data=None,
                status_code=400,
                message=reason
            ).model_dump()

        # Validate parent_id if provided
        parent = None
        if request_data.parent_id:
            parent = db.query(Person).filter(
                Person.uuid == request_data.parent_id, Person.is_deleted.is_(False)).first()
            parent = db.query(Person).filter(
                Person.uuid == request_data.parent_id, Person.is_deleted.is_(False)).first()
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


@payment_router.put(
        "/person/{person_id}", tags=["Payments"],
        status_code=h_status.HTTP_200_OK
    )
def update_person(
    person_id: UUID,
    request_data: UpdatePerson,
    db: Session = Depends(get_db),
):
    """
    Partially update a Person's details
    (account_number, ifsc_code, phone_number, upi_number, parent_id, etc.)
    """
    try:
        # 1) Find the existing person
        person_record = db.query(Person).filter(
            Person.uuid == person_id,
            Person.is_deleted.is_(False)
        ).first()

        if not person_record:
            return PaymentServiceResponse(
                data=None,
                message="Person not found.",
                status_code=404
            ).model_dump()

        # 2) If a new parent_id is provided, check that it exists
        # (and isn't the same as the person's own UUID)
        if request_data.parent_id:
            if request_data.parent_id == person_record.uuid:
                return PaymentServiceResponse(
                    data=None,
                    message="A person cannot be their own parent.",
                    status_code=400
                ).model_dump()

            parent_person = db.query(Person).filter(
                Person.uuid == request_data.parent_id,
                Person.is_deleted.is_(False)
            ).first()
            if not parent_person:
                return PaymentServiceResponse(
                    data=None,
                    message="Parent account not found.",
                    status_code=400
                ).model_dump()

        # 3) Check uniqueness constraints: account_number/ifsc_code or
        # phone_number/upi_number
        # We only apply a uniqueness check if the user
        # is actually updating these fields.

        # 3a) If updating account_number or ifsc_code:
        if (request_data.account_number or request_data.ifsc_code):
            conflict = db.query(Person).filter(
                (Person.account_number == request_data.account_number),
                Person.uuid != person_id,  # exclude self
                Person.is_deleted.is_(False)
            ).first()
            if conflict:
                return PaymentServiceResponse(
                    data=None,
                    status_code=400,
                    message="A person with the same account number or IFSC code already exists."
                ).model_dump()

        # 3b) If updating phone_number or upi_number:
        if (request_data.phone_number or request_data.upi_number):
            conflict = db.query(Person).filter(
                (
                    (Person.phone_number == request_data.phone_number)
                    | (Person.upi_number == request_data.upi_number)
                ),
                Person.uuid != person_id,
                Person.is_deleted.is_(False)
            ).first()
            if conflict:
                return PaymentServiceResponse(
                    data=None,
                    status_code=400,
                    message="A person with the same phone number or UPI number already exists."
                ).model_dump()

        # 4) Update the fields that were provided
        if request_data.name is not None:
            person_record.name = request_data.name
        if request_data.account_number is not None:
            person_record.account_number = request_data.account_number
        if request_data.ifsc_code is not None:
            person_record.ifsc_code = request_data.ifsc_code
        if request_data.phone_number is not None:
            person_record.phone_number = request_data.phone_number
        if request_data.upi_number is not None:
            person_record.upi_number = request_data.upi_number
        if request_data.parent_id is not None:
            person_record.parent_id = request_data.parent_id

        db.commit()
        return PaymentServiceResponse(
            data=str(person_record.uuid),
            message="Person updated successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.put(
        "/person/{person_id}", tags=["Payments"],
        status_code=h_status.HTTP_200_OK
    )
def update_person(
    person_id: UUID,
    request_data: UpdatePerson,
    db: Session = Depends(get_db),
):
    """
    Partially update a Person's details
    (account_number, ifsc_code, phone_number, upi_number, parent_id, etc.)
    """
    try:
        # 1) Find the existing person
        person_record = db.query(Person).filter(
            Person.uuid == person_id,
            Person.is_deleted.is_(False)
        ).first()

        if not person_record:
            return PaymentServiceResponse(
                data=None,
                message="Person not found.",
                status_code=404
            ).model_dump()

        # 2) If a new parent_id is provided, check that it exists
        # (and isn't the same as the person's own UUID)
        if request_data.parent_id:
            if request_data.parent_id == person_record.uuid:
                return PaymentServiceResponse(
                    data=None,
                    message="A person cannot be their own parent.",
                    status_code=400
                ).model_dump()

            parent_person = db.query(Person).filter(
                Person.uuid == request_data.parent_id,
                Person.is_deleted.is_(False)
            ).first()
            if not parent_person:
                return PaymentServiceResponse(
                    data=None,
                    message="Parent account not found.",
                    status_code=400
                ).model_dump()

        # 3) Check uniqueness constraints: account_number/ifsc_code or
        # phone_number/upi_number
        # We only apply a uniqueness check if the user
        # is actually updating these fields.

        # 3a) If updating account_number or ifsc_code:
        if (request_data.account_number or request_data.phone_number):
            conflict = db.query(Person).filter(
                and_(
                    Person.account_number == request_data.account_number,
                    Person.phone_number == request_data.phone_number
                ),
                Person.uuid != person_id,  # exclude self
                Person.is_deleted.is_(False)
            ).first()
            if conflict:
                return PaymentServiceResponse(
                    data=None,
                    status_code=400,
                    message="A person with the same account number already exists."
                ).model_dump()

        # 4) Update the fields that were provided
        if request_data.name is not None:
            person_record.name = request_data.name
        if request_data.account_number is not None:
            person_record.account_number = request_data.account_number
        if request_data.ifsc_code is not None:
            person_record.ifsc_code = request_data.ifsc_code
        if request_data.phone_number is not None:
            person_record.phone_number = request_data.phone_number
        if request_data.upi_number is not None:
            person_record.upi_number = request_data.upi_number
        if request_data.parent_id is not None:
            person_record.parent_id = request_data.parent_id

        db.commit()
        return PaymentServiceResponse(
            data=str(person_record.uuid),
            message="Person updated successfully.",
            status_code=200
        ).model_dump()

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
    has_additional_info: bool,
    list_tag: Optional[ItemListTag] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        new_item = Item(
            name=name,
            category=category,
            list_tag=list_tag,
            has_additional_info=has_additional_info
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
def list_items(
    list_tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        if list_tag is None:
            items = db.query(Item).all()
        elif list_tag == 'khatabook':
            items = db.query(Item).filter(
                or_(
                    Item.list_tag.is_(None),
                    Item.list_tag == 'khatabook'
                )
            ).all()
        elif list_tag == 'payment':
            items = db.query(Item).filter(
                or_(
                    Item.list_tag.is_(None),
                    Item.list_tag == 'payment'
                )
            ).all()
        else:
            return PaymentServiceResponse(
                data=None,
                message="Undefined value of list_tag. Allowed Values ['payment', 'khatabook', null]",
                status_code=400
            ).model_dump()

        items_data = [
            {
                "uuid": str(item.uuid),
                "name": item.name,
                "category": item.category,
                "list_tag": item.list_tag,
                "has_additional_info": item.has_additional_info
            } for item in items
        ]

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



@payment_router.put("/items/{item_uuid}", tags=["Items"], status_code=200)
def update_item(
    item_uuid: UUID,
    payload: UpdateItemSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # if you want to enforce role checks
):
    """
    Update an existing Item's details:
      - name
      - category
      - list_tag
      - has_additional_info

    Returns 404 if item not found.
    """
    try:
        item_record = db.query(Item).filter(Item.uuid == item_uuid).first()
        if not item_record:
            return PaymentServiceResponse(
                data=None,
                message="Item not found.",
                status_code=404
            ).model_dump()

        # Example: Only certain roles can update item (uncomment/adjust as needed)
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
        ]:
            return PaymentServiceResponse(
                data=None,
                status_code=403,
                message="You are not authorized to update this item."
            ).model_dump()

        # Update each field if given
        if payload.name is not None:
            item_record.name = payload.name
        if payload.category is not None:
            item_record.category = payload.category
        if payload.list_tag is not None:
            item_record.list_tag = payload.list_tag
        if payload.has_additional_info is not None:
            item_record.has_additional_info = payload.has_additional_info

        db.commit()
        db.refresh(item_record)

        return PaymentServiceResponse(
            data={
                "uuid": str(item_record.uuid),
                "name": item_record.name,
                "category": item_record.category,
                "list_tag": item_record.list_tag,
                "has_additional_info": item_record.has_additional_info
            },
            message="Item updated successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error updating item: {str(e)}",
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
    response = {"priority_uuid": str(
        new_priority.uuid), "priority": new_priority.priority}
    response = {"priority_uuid": str(
        new_priority.uuid), "priority": new_priority.priority}
    return PaymentServiceResponse(
        data=response,
        message="priority created successfully",
        status_code=201
    ).model_dump()


@payment_router.get("/priority", status_code=200)
def list_priorities(db: Session = Depends(get_db)):
    priorities = db.query(Priority).filter(
        Priority.is_deleted.is_(False)).all()
    response = [{"uuid": str(p.uuid), "priority": p.priority}
                for p in priorities]
    priorities = db.query(Priority).filter(
        Priority.is_deleted.is_(False)).all()
    response = [{"uuid": str(p.uuid), "priority": p.priority}
                for p in priorities]
    return PaymentServiceResponse(
        data=response,
        message="priorities fetched successfully.",
        status_code=200
    ).model_dump()


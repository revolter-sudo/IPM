import os
import traceback
import time
from typing import Optional, List
from uuid import UUID
import uuid
from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    Form,
    Body
)
from fastapi import status as h_status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, case, desc, func
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
    BalanceDetail,
    ProjectItemMap,
    ProjectUserMap,
    ItemCategories,
    Khatabook,
    ItemGroups,
    ItemGroupMap
)
import logging
from src.app.schemas.auth_service_schamas import UserRole
from uuid import uuid4
from src.app.schemas import constants
from src.app.schemas.constants import KHATABOOK_ENTRY_TYPE_CREDIT, KHATABOOK_PAYMENT_TYPE
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
    UpdateItemSchema,
    ItemDetail,
    ItemCategoryCreate,
    ItemCategoryResponse
)
from src.app.notification.notification_service import send_push_notification
from src.app.notification.notification_schemas import NotificationMessage
from src.app.notification.notification_service import send_push_notification
from src.app.notification.notification_schemas import NotificationMessage
from sqlalchemy.orm import aliased
from src.app.services.auth_service import get_current_user
from src.app.services.project_service import create_project_balance_entry
import json
from collections import defaultdict


from src.app.utils.logging_config import get_logger, get_database_logger, get_performance_logger

# Use enhanced logging system
logger = get_logger(__name__)
db_logger = get_database_logger()
perf_logger = get_performance_logger()

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
        logger.info(
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
        if not project:
            return PaymentServiceResponse(
                status_code=404,
                data=None,
                message="Project not found."
            ).model_dump()

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
                # Create a unique filename to avoid collisions
                file_ext = os.path.splitext(file.filename)[1]
                unique_filename = f"{str(uuid4())}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)

                # Save the file
                with open(file_path, "wb") as buffer:
                    buffer.write(file.file.read())

                # Store the relative path in the database
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
            logger.error(
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

    # Prevent editing of khatabook payments
    if payment.status == "khatabook":
        return PaymentServiceResponse(
            message="Khatabook payments cannot be edited.",
            data=None,
            status_code=400
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
        Return the selected person's details regardless of parent-child relationship.
        This ensures the payment shows the actual person that was selected.
        """
        return person
    except Exception as e:
        print(f"Error in get_parent_account_data API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"Error in get_parent_account_data: {str(e)}",
            status_code=500,
        ).model_dump()


def can_edit_payment(status_history: List[str], current_user_role: str, payment_status: str = None) -> bool:
    # Khatabook payments cannot be edited by anyone
    if payment_status == "khatabook" or "khatabook" in status_history:
        return False

    # SiteEngineer and SubContractor can never edit
    if current_user_role in [UserRole.SITE_ENGINEER, UserRole.SUB_CONTRACTOR]:
        return False

    # Project Manager, Admin, Accountant, SuperAdmin can edit in any status except transferred, declined, or khatabook
    if current_user_role in [UserRole.PROJECT_MANAGER, UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.SUPER_ADMIN]:
        if any(status in [PaymentStatus.TRANSFERRED, PaymentStatus.DECLINED, PaymentStatus.KHATABOOK] for status in status_history):
            return False
        return True

    return False


def create_khatabook_entry_for_self_payment(payment: Payment, db: Session, balance_after_entry: float) -> bool:
    """
    Creates a khatabook entry for a self payment when it's approved (transferred).

    Args:
        payment: The Payment object that was approved
        db: Database session
        balance_after_entry: The user's balance after the payment amount was added

    Returns:
        bool: True if khatabook entry was created successfully, False otherwise
    """
    try:
        # Create the khatabook entry
        khatabook_entry = Khatabook(
            amount=payment.amount,
            remarks=f"Self payment approved - {payment.description}" if payment.description else "Self payment approved",
            person_id=payment.person,  # The person receiving the payment
            expense_date=payment.transferred_date or datetime.now(),
            created_by=payment.created_by,
            balance_after_entry=balance_after_entry,  # Balance after the payment was added
            project_id=payment.project_id,
            payment_mode="Bank Transfer",  # Default payment mode for approved payments
            entry_type=KHATABOOK_ENTRY_TYPE_CREDIT  # Self payment entries are Credit
        )

        db.add(khatabook_entry)
        db.flush()

        logger.info(f"Created khatabook entry {khatabook_entry.uuid} for self payment {payment.uuid}")
        return True

    except Exception as e:
        logger.error(f"Error creating khatabook entry for self payment {payment.uuid}: {str(e)}")
        return False


# ========================== Payments API Started =======================================================================
# region Payments API

def build_recent_subquery(db: Session, current_user: User, recent: bool):
    """
    Builds a subquery of Payment UUIDs if `recent` is True.
    Restricts site_eng / sub_con to only see their own Payment records.
    Returns a subquery object.
    """
    recent_status = [PaymentStatus.DECLINED.value, PaymentStatus.TRANSFERRED.value, PaymentStatus.KHATABOOK.value]

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


def get_user_project_ids(db: Session, user_uuid: UUID):
    """
    Get a list of project IDs that the user is assigned to.
    Returns a list of project UUIDs.
    """
    project_mappings = (
        db.query(ProjectUserMap.project_id)
        .filter(ProjectUserMap.user_id == user_uuid)
        .all()
    )
    return [mapping[0] for mapping in project_mappings]

def apply_role_restrictions(query, current_user: User, db: Session = None):
    """
    Apply role-based restrictions to the query:
    - Super Admin, Admin, Accountant: see all payments
    - Site Engineer, Sub Contractor: see only payments they created
    - Project Manager: see only payments from projects they're assigned to

    Special handling for khatabook payments:
    - Only visible to: creator, project manager of the project, admin, accountant, super admin,
      and the person selected in the khatabook payment (if they have a user account)
    """
    from sqlalchemy import or_, and_
    from src.app.database.models import Person

    if current_user.role in [UserRole.SITE_ENGINEER.value, UserRole.SUB_CONTRACTOR.value]:
        # Site Engineers and Sub Contractors can see:
        # 1. Regular payments they created
        # 2. Khatabook payments they created
        # 3. Khatabook payments where they are the selected person
        if db is not None:
            # Get the person record linked to this user (if any)
            user_person = db.query(Person).filter(
                Person.user_id == current_user.uuid,
                Person.is_deleted.is_(False)
            ).first()

            if user_person:
                query = query.filter(
                    or_(
                        # Regular payments they created
                        and_(
                            Payment.created_by == current_user.uuid,
                            Payment.status != "khatabook"
                        ),
                        # Khatabook payments they created
                        and_(
                            Payment.created_by == current_user.uuid,
                            Payment.status == "khatabook"
                        ),
                        # Khatabook payments where they are the selected person
                        and_(
                            Payment.person == user_person.uuid,
                            Payment.status == "khatabook"
                        )
                    )
                )
            else:
                # No linked person, only see payments they created
                query = query.filter(Payment.created_by == current_user.uuid)
        else:
            # No db session, fallback to basic filtering
            query = query.filter(Payment.created_by == current_user.uuid)

    elif current_user.role == UserRole.PROJECT_MANAGER.value and db is not None:
        # Project Managers can see:
        # 1. Regular payments from projects they're assigned to
        # 2. Khatabook payments from projects they're assigned to
        # 3. Khatabook payments where they are the selected person
        project_ids = get_user_project_ids(db, current_user.uuid)

        # Get the person record linked to this user (if any)
        user_person = db.query(Person).filter(
            Person.user_id == current_user.uuid,
            Person.is_deleted.is_(False)
        ).first()

        conditions = []

        if project_ids:
            # Regular payments from their projects
            conditions.append(
                and_(
                    Payment.project_id.in_(project_ids),
                    Payment.status != "khatabook"
                )
            )
            # Khatabook payments from their projects
            conditions.append(
                and_(
                    Payment.project_id.in_(project_ids),
                    Payment.status == "khatabook"
                )
            )

        # Khatabook payments where they are the selected person
        if user_person:
            conditions.append(
                and_(
                    Payment.person == user_person.uuid,
                    Payment.status == "khatabook"
                )
            )

        if conditions:
            query = query.filter(or_(*conditions))
        else:
            # If not assigned to any projects and no linked person, don't show any payments
            query = query.filter(False)

    elif current_user.role in [
        UserRole.ADMIN.value,
        UserRole.ACCOUNTANT.value,
        UserRole.SUPER_ADMIN.value
    ]:
        # Admin, Accountant, Super Admin can see all payments including khatabook
        pass  # No additional filtering needed

    else:
        # For any other roles, apply restrictive filtering
        # They can only see regular payments they created (no khatabook access)
        query = query.filter(
            and_(
                Payment.created_by == current_user.uuid,
                Payment.status != "khatabook"
            )
        )

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
        # Create a list of dictionaries with item name and UUID
        items_data = [
            {"name": p_item.item.name, "uuid": str(p_item.item.uuid)}
            for p_item in payment.payment_items if p_item.item
        ] if payment.payment_items else []

        # Keep the original item_names list for backward compatibility
        item_names = [item["name"] for item in items_data]

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
                # items=[ItemDetail(uuid=item["uuid"], name=item["name"]) for item in items_data],
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
            "edit": can_edit_payment(status_list, current_user.role, payment.status),
            "decline_remark": payment.decline_remark,
            "approval_files": approval_files,
            # ---------- NEW KEYS ----------
            "transferred_from_bank": bank_name,
            "payment_type": KHATABOOK_PAYMENT_TYPE if payment.self_payment else None
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
        """Calculate total amount of payments with appropriate status filtering"""
        # Check if any specific filters are applied (project, item, person, user, status)
        has_specific_filters = any([
            project_id is not None,
            item_id is not None,
            person_id is not None,
            from_uuid is not None,
            to_uuid is not None,
            status is not None  # Include status filter detection
        ])

        # Determine which statuses to include based on filtering context
        if status is not None:
            # When status filter is applied, use only the requested statuses
            # This handles cases like ?status=khatabook correctly
            query = db.query(func.sum(Payment.amount)).filter(
                Payment.is_deleted.is_(False)
                # Status filter will be applied later in the function
            )
        elif has_specific_filters:
            # When filtering by other entities (project, item, person, user), include khatabook payments
            query = db.query(func.sum(Payment.amount)).filter(
                Payment.is_deleted.is_(False),
                Payment.status.in_([
                    PaymentStatus.REQUESTED.value,
                    PaymentStatus.APPROVED.value,
                    PaymentStatus.VERIFIED.value,
                    PaymentStatus.TRANSFERRED.value,
                    PaymentStatus.KHATABOOK.value  # Include khatabook when filtering by entities
                ])
            )
        else:
            # Global totals exclude khatabook payments
            query = db.query(func.sum(Payment.amount)).filter(
                Payment.is_deleted.is_(False),
                Payment.status.in_([
                    PaymentStatus.REQUESTED.value,
                    PaymentStatus.APPROVED.value,
                    PaymentStatus.VERIFIED.value,
                    PaymentStatus.TRANSFERRED.value
                ])
            )

        # Apply the same role-based restrictions as the main query
        query = apply_role_restrictions(query, current_user, db)
        if project_id is not None:
            query = query.filter(Payment.project_id == project_id)
        if status is not None:
            query = query.filter(Payment.status.in_(status))
            # query = query.filter(Payment.status != PaymentStatus.DECLINED.value)
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
        """Calculate total amount of pending payments with appropriate status filtering"""
        # Check if any specific filters are applied (project, item, person, user, status)
        has_specific_filters = any([
            project_id is not None,
            item_id is not None,
            person_id is not None,
            from_uuid is not None,
            to_uuid is not None,
            status is not None  # Include status filter detection
        ])

        # Determine which statuses to include based on filtering context
        if status is not None:
            # When status filter is applied, use only the requested statuses for pending calculation
            # Note: if status=khatabook, this will include khatabook amounts in "pending" total
            query = db.query(func.sum(Payment.amount)).filter(
                Payment.is_deleted.is_(False)
                # Status filter will be applied later in the function
            )
        elif has_specific_filters:
            # When filtering by other entities, include khatabook payments in pending calculation
            # Note: khatabook payments are never truly "pending" but should be included in filtered totals
            query = db.query(func.sum(Payment.amount)).filter(
                Payment.is_deleted.is_(False),
                Payment.status.in_([
                    PaymentStatus.REQUESTED.value,
                    PaymentStatus.APPROVED.value,
                    PaymentStatus.VERIFIED.value,
                    PaymentStatus.KHATABOOK.value  # Include khatabook when filtering by entities
                ])
            )
        else:
            # Global pending totals exclude khatabook payments
            query = db.query(func.sum(Payment.amount)).filter(
                Payment.is_deleted.is_(False),
                Payment.status.in_([
                    PaymentStatus.REQUESTED.value,
                    PaymentStatus.APPROVED.value,
                    PaymentStatus.VERIFIED.value
                ])
            )

        # Apply the same role-based restrictions as the main query
        query = apply_role_restrictions(query, current_user, db)
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
                      [PaymentStatus.TRANSFERRED.value, PaymentStatus.DECLINED.value, PaymentStatus.KHATABOOK.value])  # exclude transferred, declined, and khatabook
            )
            .order_by(Payment.created_at.desc())
        )

        # Apply role-based restrictions
        base = apply_role_restrictions(base, current_user, db)

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

        # Apply role-based restrictions
        base = apply_role_restrictions(base, current_user, db)

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

    # Apply role-based restrictions
    base = apply_role_restrictions(base, current_user, db)

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

# endregion
# ========================== Payments API Finished =======================================================================

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
    logger.info(f"{len(people)} Users were notified for this payment request")
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
        start_time = time.time()

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

        # 2.1) Prevent approval of khatabook payments
        if payment.status == "khatabook":
            return PaymentServiceResponse(
                data=None,
                message="Khatabook payments cannot be approved or modified.",
                status_code=400
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
            "transferred": 4,
            "khatabook": 5  # Khatabook status is final and non-changeable
        }

        def get_order(s: str) -> int:
            return status_order_map.get(s, 0)

        current_order = get_order(payment.status)
        new_order = get_order(status)

        if new_order > current_order:
            payment.status = status

        # If the status is 'transferred' (either new or existing), do the transfer logic
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
                self_payment_start = time.time()
                db_logger.info(f"Processing self payment {payment.uuid} for user {payment.created_by}")

                user_balance = db.query(KhatabookBalance).filter(
                    KhatabookBalance.user_uuid == payment.created_by
                ).first()

                old_balance = 0.0
                if not user_balance:
                    db_logger.info(f"Creating new khatabook balance for user {payment.created_by}")
                    user_balance = KhatabookBalance(
                        user_uuid=payment.created_by,
                        balance=0.0
                    )
                    db.add(user_balance)
                else:
                    old_balance = user_balance.balance
                    db_logger.info(f"User {payment.created_by} current balance: {old_balance}")

                # Increase the user's khatabook balance
                user_balance.balance += payment.amount
                new_balance = user_balance.balance

                # Flush to ensure balance update is persisted in this transaction
                db.flush()

                db_logger.info(
                    f"Updated user {payment.created_by} balance from "
                    f"{old_balance} to {new_balance} (added {payment.amount})"
                )

                # Get the last khatabook entry's balance_after_entry to
                # maintain consistency
                last_entry = db.query(Khatabook).filter(
                    Khatabook.created_by == payment.created_by,
                    Khatabook.is_deleted.is_(False)
                ).order_by(Khatabook.created_at.desc()).first()

                # Calculate balance_after_entry as last entry's balance +
                # payment amount
                last_balance_after_entry = (
                    last_entry.balance_after_entry if last_entry else 0.0
                )
                balance_after_entry = last_balance_after_entry + payment.amount

                db_logger.info(
                    f"Calculated balance_after_entry: "
                    f"{last_balance_after_entry} + {payment.amount} = "
                    f"{balance_after_entry}"
                )

                # Create khatabook entry for the self payment with correct
                # balance
                db_logger.info(f"Attempting to create khatabook entry for self payment {payment.uuid} with balance_after_entry: {balance_after_entry}")
                khatabook_created = create_khatabook_entry_for_self_payment(
                    payment, db, balance_after_entry
                )
                if not khatabook_created:
                    db_logger.error(
                        f"Failed to create khatabook entry for self payment "
                        f"{payment.uuid}. Payment person: {payment.person}, "
                        f"Self payment flag: {payment.self_payment}"
                    )
                else:
                    db_logger.info(
                        f"Successfully created khatabook entry for self "
                        f"payment {payment.uuid}"
                    )

                # Log self-payment processing time
                self_payment_time = time.time() - self_payment_start
                perf_logger.info(f"Self payment processing took {self_payment_time:.4f}s")

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

            # Add to project's actual balance
            project = db.query(Project).filter(Project.uuid == payment.project_id).first()
            if project:
                project.actual_balance += payment.amount
                # Create project balance entry for actual balance
                create_project_balance_entry(
                    db=db,
                    project_id=payment.project_id,
                    adjustment=payment.amount,
                    description=f"Payment deduction for payment {payment.uuid}",
                    current_user=current_user,
                    balance_type="actual"
                )

            # Deduct from item balances if items are associated with this payment
            payment_items = db.query(PaymentItem).filter(
                PaymentItem.payment_id == payment.uuid,
                PaymentItem.is_deleted.is_(False)
            ).all()

            for payment_item in payment_items:
                item = db.query(ProjectItemMap).filter(
                    ProjectItemMap.project_id == payment.project_id,
                    ProjectItemMap.item_id == payment_item.item_id
                ).first()

                if item:
                    # Deduct the full payment amount from each item's balance
                    # Initialize item_balance to 0 if it's None
                    if item.item_balance is None:
                        item.item_balance = 0

                    # Update item balance by deducting the full payment amount
                    item.item_balance -= payment.amount

                    # Log the deduction
                    log_entry = Log(
                        uuid=str(uuid4()),
                        entity="ProjectItemMap",
                        action="DeductBalance",
                        entity_id=item.uuid,
                        performed_by=current_user.uuid,
                    )
                    db.add(log_entry)

        # 6) Handle optional file uploads
        if files:
            upload_dir = constants.UPLOAD_DIR_ADMIN
            os.makedirs(upload_dir, exist_ok=True)
            for file in files:
                # Create a unique filename to avoid collisions
                file_ext = os.path.splitext(file.filename)[1]
                unique_filename = f"{str(uuid4())}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)

                # Save the file
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

        # 2.1) Prevent decline of khatabook payments
        if payment.status == "khatabook":
            return PaymentServiceResponse(
                data=None,
                message="Khatabook payments cannot be declined or modified.",
                status_code=400
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
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
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

        # 3) Check uniqueness constraints only if values are changing
        # 3a) Check account_number uniqueness if being updated and different
        if (request_data.account_number is not None and
                request_data.account_number != person_record.account_number):
            conflict = db.query(Person).filter(
                Person.account_number == request_data.account_number,
                Person.uuid != person_id,  # exclude self
                Person.is_deleted.is_(False)
            ).first()
            if conflict:
                return PaymentServiceResponse(
                    data=None,
                    status_code=400,
                    message="A person with the same account number exists."
                ).model_dump()

        # 3b) Check phone_number uniqueness if being updated and different
        if (request_data.phone_number is not None and
                request_data.phone_number != person_record.phone_number):
            conflict = db.query(Person).filter(
                Person.phone_number == request_data.phone_number,
                Person.uuid != person_id,
                Person.is_deleted.is_(False)
            ).first()
            if conflict:
                return PaymentServiceResponse(
                    data=None,
                    status_code=400,
                    message="A person with the same phone number exists."
                ).model_dump()

        # 3c) Check upi_number uniqueness if being updated and different
        if (request_data.upi_number is not None and
                request_data.upi_number != person_record.upi_number):
            conflict = db.query(Person).filter(
                Person.upi_number == request_data.upi_number,
                Person.uuid != person_id,
                Person.is_deleted.is_(False)
            ).first()
            if conflict:
                return PaymentServiceResponse(
                    data=None,
                    status_code=400,
                    message="A person with the same UPI number exists."
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


# @payment_router.get(
#     "/persons", status_code=h_status.HTTP_200_OK, tags=["Payments"]
# )
# def get_all_persons(
#     name: str = Query(None),
#     phone_number: str = Query(None),
#     account_number: str = Query(None),
#     ifsc_code: str = Query(None),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     try:
#         query = db.query(Person).filter(
#             Person.is_deleted.is_(False),
#             Person.parent_id.is_(None)
#         )

#         if name:
#             query = query.filter(Person.name.ilike(f"%{name}%"))
#         if phone_number:
#             query = query.filter(Person.phone_number == phone_number)
#         if account_number:
#             query = query.filter(Person.account_number == account_number)
#         if ifsc_code:
#             query = query.filter(Person.ifsc_code == ifsc_code)

#         # Exclude the current user's Person record if it exists:
#         query = query.filter(or_(
#             Person.user_id.is_(None),
#             Person.user_id != current_user.uuid
#         ))

#         persons = query.all()
#         persons_data = []

#         for person in persons:
#             persons_data.append(
#                 {
#                     "uuid": person.uuid,
#                     "name": person.name,
#                     "account_number": person.account_number,
#                     "ifsc_code": person.ifsc_code,
#                     "phone_number": person.phone_number,
#                     "parent_id": person.parent_id,
#                     "upi_number": person.upi_number,
#                     "secondary_accounts": [
#                         {
#                             "uuid": child.uuid,
#                             "name": child.name,
#                             "account_number": child.account_number,
#                             "ifsc_code": child.ifsc_code,
#                             "phone_number": child.phone_number,
#                             "upi_number": child.upi_number
#                         }
#                         for child in person.children if not child.is_deleted
#                     ]
#                 }
#             )

#         return PaymentServiceResponse(
#             data=persons_data,
#             message="All persons info fetched successfully.",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         traceback.print_exc()
#         return PaymentServiceResponse(
#             data=None,
#             message=f"An Error Occurred: {str(e)}",
#             status_code=500
#         ).model_dump()

        

# @payment_router.get(
#     "/persons", status_code=h_status.HTTP_200_OK, tags=["Payments"]
# )
# def get_all_persons(
#     name: str = Query(None),
#     phone_number: str = Query(None),
#     account_number: str = Query(None),
#     ifsc_code: str = Query(None),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     try:
#         # Fetch all parent persons with children eagerly loaded
#         persons = db.query(Person).options(
#             joinedload(Person.children)
#         ).filter(
#             Person.is_deleted.is_(False),
#             Person.parent_id.is_(None),
#             or_(Person.user_id.is_(None), Person.user_id != current_user.uuid)
#         ).all()

#         def matches(person: Person) -> bool:
#             """Returns True if this person or any child matches the filter."""
#             def match(p: Person):
#                 return all([
#                     (not name or name.lower() in (p.name or "").lower()),
#                     (not phone_number or p.phone_number == phone_number),
#                     (not account_number or p.account_number == account_number),
#                     (not ifsc_code or p.ifsc_code == ifsc_code)
#                 ])

#             if match(person):
#                 return True
#             for child in person.children:
#                 if not child.is_deleted and match(child):
#                     return True
#             return False

#         # Apply filters in Python
#         filtered_persons = [person for person in persons if matches(person)]

#         # Format result
#         persons_data = []
#         for person in filtered_persons:
#             persons_data.append({
#                 "uuid": person.uuid,
#                 "name": person.name,
#                 "account_number": person.account_number,
#                 "ifsc_code": person.ifsc_code,
#                 "phone_number": person.phone_number,
#                 "parent_id": person.parent_id,
#                 "upi_number": person.upi_number,
#                 "secondary_accounts": [
#                     {
#                         "uuid": child.uuid,
#                         "name": child.name,
#                         "account_number": child.account_number,
#                         "ifsc_code": child.ifsc_code,
#                         "phone_number": child.phone_number,
#                         "upi_number": child.upi_number
#                     }
#                     for child in person.children if not child.is_deleted
#                 ]
#             })

#         return PaymentServiceResponse(
#             data=persons_data,
#             message="All persons info fetched successfully.",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         traceback.print_exc()
#         return PaymentServiceResponse(
#             data=None,
#             message=f"An Error Occurred: {str(e)}",
#             status_code=500
#         ).model_dump()

@payment_router.get(
    "/persons", 
    status_code=h_status.HTTP_200_OK, 
    tags=["Payments"]
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
        # Fetch all parent persons with children eagerly loaded
        persons = db.query(Person).options(
            joinedload(Person.children)
        ).filter(
            Person.is_deleted.is_(False),
            Person.parent_id.is_(None),
            or_(Person.user_id.is_(None), Person.user_id != current_user.uuid)
        ).all()

        def matches(person: Person) -> bool:
            """Returns True if this person or any child matches the filter."""
            def match(p: Person):
                return all([
                    (not name or name.lower() in (p.name or "").lower()),
                    (not phone_number or p.phone_number == phone_number),
                    (not account_number or p.account_number == account_number),
                    (not ifsc_code or p.ifsc_code == ifsc_code)
                ])
            if match(person):
                return True
            for child in person.children:
                if not child.is_deleted and match(child):
                    return True
            return False

        # Apply filters in Python
        filtered_persons = [person for person in persons if matches(person)]

        persons_data = []

        def format_account(person, is_primary, parent_obj=None, children=None):
            return {
                "uuid": person.uuid,
                "name": person.name,
                "account_number": person.account_number,
                "ifsc_code": person.ifsc_code,
                "phone_number": person.phone_number,
                "parent_id": person.parent_id,
                "upi_number": person.upi_number,
                "is_primary": is_primary,
                "parent_account": parent_obj,
                "secondary_accounts": children or []
            }

        for parent in filtered_persons:
            # Gather children for the parent (secondary accounts)
            child_accounts = []
            for child in parent.children:
                if not child.is_deleted:
                    child_accounts.append({
                        "uuid": child.uuid,
                        "name": child.name,
                        "account_number": child.account_number,
                        "ifsc_code": child.ifsc_code,
                        "phone_number": child.phone_number,
                        "upi_number": child.upi_number
                    })

            # Add parent ("primary") account
            persons_data.append(format_account(
                parent,
                is_primary=True,
                parent_obj=None,
                children=child_accounts
            ))

            # Add each child ("secondary") account as top-level
            for child in parent.children:
                if not child.is_deleted:
                    parent_obj = {
                        "uuid": parent.uuid,
                        "name": parent.name,
                        "account_number": parent.account_number,
                        "ifsc_code": parent.ifsc_code,
                        "phone_number": parent.phone_number,
                        "upi_number": parent.upi_number
                    }
                    persons_data.append(format_account(
                        child,
                        is_primary=False,
                        parent_obj=parent_obj,
                        children=[]
                    ))
                    
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
    "/{person_uuid}/remove-from-parent",
    tags=["Payments"],
    status_code=200,
    description="Removes the parent-child link for a given child person, making them an individual (no parent)."
)
def remove_child_from_parent(
    person_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Detach a child from its parent, making it an individual person.
    Only admin/superadmin can perform this action.
    """
    if isinstance(current_user, dict):
        return current_user

    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        return PaymentServiceResponse(
            data=None,
            status_code=403,
            message="Only admin and super admin can perform this action"
        ).model_dump()

    try:
        # Fetch child person
        child = db.query(Person).filter(Person.uuid == person_uuid, Person.is_deleted.is_(False)).first()
        if not child:
            return PaymentServiceResponse(
                data=None,
                status_code=404,
                message="Child person not found"
            ).model_dump()
        if not child.parent_id:
            return PaymentServiceResponse(
                data=None,
                status_code=400,
                message="This person has no parent to detach from"
            ).model_dump()

        prev_parent_id = child.parent_id  # For audit, if needed

        # Remove parent relationship
        child.parent_id = None
        db.commit()
        db.refresh(child)

        return PaymentServiceResponse(
            data={
                "uuid": str(child.uuid),
                "name": child.name,
                "parent_id": child.parent_id,
                "previous_parent_id": str(prev_parent_id),
                "message": "Person is now independent (no parent)."
            },
            status_code=200,
            message="Child successfully detached from parent."
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while detaching child: {str(e)}"
        ).model_dump()


@payment_router.put(
    "/persons/delete",
    status_code=h_status.HTTP_204_NO_CONTENT,
    tags=["Payments"],
)
def delete_person(
    person_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        normalized_name = name.strip().lower()
        # check if an item with the same name already exists
        existing_item = db.query(Item).filter(
            func.lower(Item.name) == normalized_name
            # Item.is_deleted.is_(False)
            ).first()
        
        if existing_item:
            return PaymentServiceResponse(
                data=None,
                message="An item with this name already exists.",
                status_code=400
            ).model_dump()

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


# @payment_router.get("/items", tags=["Items"], status_code=200)
# def list_items(
#     list_tag: Optional[str] = None,
#     db: Session = Depends(get_db)
# ):
#     try:
#         # Base query with ordering by id in descending order
#         base_query = db.query(Item).order_by(desc(Item.id))

#         if list_tag is None:
#             items = base_query.all()
#         elif list_tag == 'khatabook':
#             items = base_query.filter(
#                 or_(
#                     Item.list_tag.is_(None),
#                     Item.list_tag == 'khatabook'
#                 )
#             ).all()
#         elif list_tag == 'payment':
#             items = base_query.filter(
#                 or_(
#                     Item.list_tag.is_(None),
#                     Item.list_tag == 'payment'
#                 )
#             ).all()
#         else:
#             return PaymentServiceResponse(
#                 data=None,
#                 message="Undefined value of list_tag. Allowed Values "
#                         "['payment', 'khatabook', null]",
#                 status_code=400
#             ).model_dump()

#         items_data = [
#             {
#                 "uuid": str(item.uuid),
#                 "name": item.name,
#                 "category": item.category,
#                 "list_tag": item.list_tag,
#                 "has_additional_info": item.has_additional_info,
#                 "created_at": item.created_at
#             } for item in items
#         ]

#         return PaymentServiceResponse(
#             data=items_data,
#             message="All items fetched successfully.",
#             status_code=200
#         ).model_dump()
#     except Exception as e:
#         return PaymentServiceResponse(
#             data=None,
#             message=f"Error fetching items: {str(e)}",
#             status_code=500
#         ).model_dump()



@payment_router.get("/items", tags=["Items"], status_code=200)
def list_items(
    list_tag: Optional[str] = None,
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        query = db.query(Item).order_by(desc(Item.id))

        # Filter by list_tag
        if list_tag == "khatabook":
            query = query.filter(or_(Item.list_tag == 'khatabook', Item.list_tag.is_(None)))
        elif list_tag == "payment":
            query = query.filter(or_(Item.list_tag == 'payment', Item.list_tag.is_(None)))
        elif list_tag not in (None, "payment", "khatabook"):
            return PaymentServiceResponse(
                data=None,
                message="Undefined value of list_tag. Allowed values: ['payment', 'khatabook', null]",
                status_code=400
            ).model_dump()

        # Filter by category
        if category:
            query = query.filter(Item.category.ilike(f"%{category.strip()}%"))

        # Search by item name
        if search:
            query = query.filter(Item.name.ilike(f"%{search.strip()}%"))

        items = query.all()
        items_data = []

        for item in items:
            # Get associated item groups
            mappings = db.query(ItemGroupMap, ItemGroups).join(ItemGroups, ItemGroupMap.item_group_id == ItemGroups.uuid)\
                .filter(
                    ItemGroupMap.item_id == item.uuid,
                    ItemGroupMap.is_deleted == False,
                    ItemGroups.is_deleted == False
                ).all()

            associated_groups = [
                {
                    "group_id": str(group.uuid),
                    "group_name": group.item_groups
                } for _, group in mappings
            ] if mappings else None

            # get payment count
            payment_count = db.query(func.count(PaymentItem.id)).filter(PaymentItem.item_id == item.uuid).scalar() or 0

            items_data.append({
                "uuid": str(item.uuid),
                "name": item.name,
                "category": item.category,
                "list_tag": item.list_tag,
                "has_additional_info": item.has_additional_info,
                "created_at": item.created_at,
                "associated_groups": associated_groups,
                "payment_count": payment_count
            })

        return PaymentServiceResponse(
            data=items_data,
            message="Filtered items fetched successfully.",
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
    current_user: User = Depends(get_current_user),
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
        from sqlalchemy import cast, String
        item_record = db.query(Item).filter(cast(Item.uuid, String) == str(item_uuid)).first()
        if not item_record:
            return PaymentServiceResponse(
                data=None,
                message="Item not found.",
                status_code=404
            ).model_dump()

        # Example: Only certain roles can update item (adjust as needed)
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
        ]:
            return PaymentServiceResponse(
                data=None,
                status_code=403,
                message="You are not authorized to update this item."
            ).model_dump()
        
        # Check for duplicate name (if name is being updated)
        if payload.name and payload.name.strip().lower() != item_record.name.strip().lower():
            normalized_name = payload.name.strip().lower()
            duplicate_item = db.query(Item).filter(
                func.lower(Item.name) == normalized_name,
                Item.uuid != item_uuid  # exclude current item
            ).first()
            if duplicate_item:
                return PaymentServiceResponse(
                    data=None,
                    message="Another item with this name already exists.",
                    status_code=400
                ).model_dump()

        # Update each field if given
        if payload.name is not None:
            item_record.name = payload.name
        if payload.category is not None:
            item_record.category = payload.category
        # Special handling for list_tag - explicitly allow null values
        if hasattr(payload, 'list_tag'):
            item_record.list_tag = None if (payload.list_tag is None or payload.list_tag.lower() in ['none', '']) else payload.list_tag
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
def delete_item(item_uuid: UUID, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
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
def create_priority(priority_name: str, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    new_priority = Priority(priority=priority_name)
    db.add(new_priority)
    db.commit()
    db.refresh(new_priority)
    response = {"priority_uuid": str(
        new_priority.uuid), "priority": new_priority.priority}
    return PaymentServiceResponse(
        data=response,
        message="priority created successfully",
        status_code=201
    ).model_dump()


@payment_router.get("/priority", status_code=200)
def list_priorities(db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    priorities = db.query(Priority).filter(
        Priority.is_deleted.is_(False)).all()
    response = [{"uuid": str(p.uuid), "priority": p.priority}
                for p in priorities]
    return PaymentServiceResponse(
        data=response,
        message="priorities fetched successfully.",
        status_code=200
    ).model_dump()


@payment_router.post(
    "/item-categories", 
    tags=["Item Categories"], 
    status_code=201
)
def create_item_category(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        category_clean = category.strip()

        existing = db.query(ItemCategories).filter(
            ItemCategories.category.ilike(category_clean)
        ).first()

        if existing:
            if existing.is_deleted:
                # Restore soft-deleted category
                existing.is_deleted = False
                existing.updated_by = current_user.uuid
                db.commit()
                db.refresh(existing)

                return PaymentServiceResponse(
                    data={
                        "category_uuid": str(existing.uuid),
                        "category": existing.category
                    },
                    message="Soft-deleted category restored successfully.",
                    status_code=200
                ).model_dump()

            else:
                return PaymentServiceResponse(
                    data=None,
                    message="Category already exists.",
                    status_code=400
                ).model_dump()

        # Create new category
        new_category = ItemCategories(
            uuid=uuid.uuid4(),
            category=category_clean,
            created_by=current_user.uuid
        )
        db.add(new_category)
        db.commit()
        db.refresh(new_category)

        return PaymentServiceResponse(
            data={
                "category_uuid": str(new_category.uuid),
                "category": new_category.category
            },
            message="Item category created successfully.",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error creating category: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.get(
    "/item-categories",
    tags=["Item Categories"],
    status_code=200
)
def get_all_item_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        categories = db.query(ItemCategories).filter(
            ItemCategories.is_deleted == False
        ).order_by(ItemCategories.category.asc()).all()

        result = [
            {
                "category_uuid": str(cat.uuid),
                "category": cat.category
            }
            for cat in categories
        ]

        return PaymentServiceResponse(
            data=result,
            message="Item categories fetched successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        return PaymentServiceResponse(
            data=None,
            message=f"Error fetching categories: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.put(
    "/item-categories/{category_uuid}",
    tags=["Item Categories"],
    status_code=200
)
def update_item_category(
    category_uuid: UUID,
    new_category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        category = db.query(ItemCategories).filter(
            ItemCategories.uuid == category_uuid,
            ItemCategories.is_deleted == False
        ).first()

        if not category:
            return PaymentServiceResponse(
                data=None,
                message="Category not found.",
                status_code=404
            ).model_dump()

        # Check for duplicate name (optional)
        duplicate = db.query(ItemCategories).filter(
            ItemCategories.category.ilike(new_category.strip()),
            ItemCategories.is_deleted == False,
            ItemCategories.uuid != category_uuid
        ).first()

        if duplicate:
            return PaymentServiceResponse(
                data=None,
                message="Another category with the same name already exists.",
                status_code=400
            ).model_dump()

        category.category = new_category.strip()
        db.commit()
        db.refresh(category)

        return PaymentServiceResponse(
            data={
                "category_uuid": str(category.uuid),
                "category": category.category
            },
            message="Item category updated successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error updating category: {str(e)}",
            status_code=500
        ).model_dump()

@payment_router.delete(
    "/item-categories/{category_uuid}",
    tags=["Item Categories"],
    status_code=200
)
def delete_item_category(
    category_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        category = db.query(ItemCategories).filter(
            ItemCategories.uuid == category_uuid,
            ItemCategories.is_deleted == False
        ).first()

        if not category:
            return PaymentServiceResponse(
                data=None,
                message="Category not found.",
                status_code=404
            ).model_dump()

        category.is_deleted = True
        category.updated_by = current_user.uuid  # log who deleted it
        db.commit()

        return PaymentServiceResponse(
            data={
                "category_uuid": str(category.uuid),
                "category": category.category
            },
            message="Item category deleted successfully (soft delete).",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error deleting category: {str(e)}",
            status_code=500
        ).model_dump()

@payment_router.post(
    "/items/group/{group_name}",
    tags=["Item Groups"],
    status_code=201
)
def create_item_group(
    group_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # If current_user is None or not authenticated
        if not current_user or not getattr(current_user, "uuid", None):
            return PaymentServiceResponse(
                data=None,
                message="Unauthorized: User not found.",
                status_code=401
            ).model_dump()

        name_clean = group_name.strip()

        # Check if group exists
        existing = db.query(ItemGroups).filter(
            ItemGroups.item_groups.ilike(name_clean)
        ).first()

        if existing:
            if existing.is_deleted:
                existing.is_deleted = False
                db.commit()
                db.refresh(existing)

                return PaymentServiceResponse(
                    data={
                        "uuid": str(existing.uuid),
                        "group_name": existing.item_groups,
                        "created_by": current_user.name,
                        "created_at": existing.created_at.isoformat()
                    },
                    message="Soft-deleted group restored successfully.",
                    status_code=200
                ).model_dump()

            return PaymentServiceResponse(
                data=None,
                message="Item group already exists.",
                status_code=400
            ).model_dump()

        # Create new
        new_group = ItemGroups(
            uuid=uuid.uuid4(),
            item_groups=name_clean,
            created_by=current_user.uuid
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)

        return PaymentServiceResponse(
            data={
                "uuid": str(new_group.uuid),
                "group_name": new_group.item_groups,
                "created_by": current_user.name,
                "created_at": new_group.created_at.isoformat()
            },
            message="Item group created successfully.",
            status_code=201
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error creating item group: {str(e)}",
            status_code=500
        ).model_dump()

@payment_router.get(
    "/items/groups",
    tags=["Item Groups"],
    status_code=200
)
def get_all_item_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        groups = db.query(ItemGroups).filter(ItemGroups.is_deleted == False).all()

        if not groups:
            return PaymentServiceResponse(
                data=[],
                message="No item groups found.",
                status_code=200
            ).model_dump()

        group_list = []
        for group in groups:
            group_list.append({
                "uuid": str(group.uuid),
                "group_name": group.item_groups,
                "created_by": str(group.created_by),
                "created_at": group.created_at.isoformat()
            })

        return PaymentServiceResponse(
            data=group_list,
            message="Item groups fetched successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        return PaymentServiceResponse(
            data=None,
            message=f"Error fetching item groups: {str(e)}",
            status_code=500
        ).model_dump()

@payment_router.put(
    "/items/group/{group_uuid}",
    tags=["Item Groups"],
    status_code=200
)
def update_item_group(
    group_uuid: UUID,
    new_group_name: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        group = db.query(ItemGroups).filter(
            ItemGroups.uuid == group_uuid,
            ItemGroups.is_deleted == False
        ).first()

        if not group:
            return PaymentServiceResponse(
                data=None,
                message="Item group not found.",
                status_code=404
            ).model_dump()

        name_clean = new_group_name.strip()

        # Check for duplicate
        existing = db.query(ItemGroups).filter(
            ItemGroups.item_groups.ilike(name_clean),
            ItemGroups.uuid != group_uuid,
            ItemGroups.is_deleted == False
        ).first()

        if existing:
            return PaymentServiceResponse(
                data=None,
                message="Another group with the same name already exists.",
                status_code=400
            ).model_dump()

        group.item_groups = name_clean
        # If you have an updated_by field:
        # group.updated_by = current_user.uuid

        db.commit()
        db.refresh(group)

        return PaymentServiceResponse(
            data={
                "uuid": str(group.uuid),
                "group_name": group.item_groups,
                "updated_by": current_user.name,
                "updated_at": group.created_at.isoformat()  # or updated_at if available
            },
            message="Item group updated successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error updating item group: {str(e)}",
            status_code=500
        ).model_dump()

@payment_router.delete(
    "/items/group/{group_uuid}",
    tags=["Item Groups"],
    status_code=200
)
def delete_item_group(
    group_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        group = db.query(ItemGroups).filter(
            ItemGroups.uuid == group_uuid,
            ItemGroups.is_deleted == False
        ).first()

        if not group:
            return PaymentServiceResponse(
                data=None,
                message="Item group not found.",
                status_code=404
            ).model_dump()

        group.is_deleted = True
        # If `updated_by` field exists:
        # group.updated_by = current_user.uuid

        db.commit()

        return PaymentServiceResponse(
            data={
                "uuid": str(group.uuid),
                "group_name": group.item_groups
            },
            message="Item group deleted successfully (soft delete).",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return PaymentServiceResponse(
            data=None,
            message=f"Error deleting item group: {str(e)}",
            status_code=500
        ).model_dump()

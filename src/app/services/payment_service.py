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
from src.app.database.models import Project
from src.app.database.database import get_db
from src.app.database.models import (
    Payment,
    Person,
    User,
    Item,
    PaymentItem,
    PaymentFile
)
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.payment_service_schemas import (
    CreatePerson,
    PaymentsResponse,
    PaymentStatus,
    PersonDetail,
    PaymentServiceResponse
)
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from src.app.services.auth_service import get_current_user
from src.app.services.project_service import create_project_balance_entry
import json

payment_router = APIRouter(prefix="/payments", tags=["Payments"])

class CreatePaymentRequest(BaseModel):
    amount: float
    project_id: UUID
    status: PaymentStatus
    item_uuids: Optional[List[UUID]] = []
    description: Optional[str] = None
    remarks: Optional[str] = None
    person: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 0,
                "project_id": "f82481f7-ec85-4790-8868-aa9a24906d36",
                "status": "approved",
                "item_uuids": [
                    "6f3e55da-1734-42d6-90ef-ae1b3e9ef759",
                    "cc8914b9-33ff-41ac-8a32-73a8829d6579"
                ],
                "description": "string",
                "remarks": "string",
                "person": "e194159d-ce26-43e1-ace0-db4b00d4c43e"
            }
        }


@payment_router.post("", tags=["Payments"], status_code=201)
def create_payment(
    request: str = Form(...),  # Parse request as a JSON string
    files: Optional[List[UploadFile]] = File(None),  # Parse files as UploadFile objects
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a payment request and update project balance. If any operation fails, rollback everything."""
    try:
        # Parse the request JSON string into a dictionary
        try:
            request_data = json.loads(request)
            payment_request = CreatePaymentRequest(**request_data)
        except (json.JSONDecodeError, ValidationError) as e:
            return PaymentServiceResponse(
                status_code=400,
                data=None,
                message=f"Invalid request format: {str(e)}"
            ).model_dump()

        # Ensure files is a list (handle None case)
        files = files or []

        allowed_file_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg", "image/heic"]
        # Validate files
        for file in files:
            if file.content_type not in allowed_file_types:
                return PaymentServiceResponse(
                    status_code=400,
                    data=None,
                    message="Only PDF, PNG, JPEG, JPG, HEIC files are allowed."
                ).model_dump()

        # Check if the project exists
        project = db.query(Project).filter(Project.uuid == payment_request.project_id).first()
        if not project:
            return PaymentServiceResponse(
                status_code=404,
                data=None,
                message="Project not found."
            ).model_dump()

        # Create a new payment
        new_payment = Payment(
            amount=payment_request.amount,
            description=payment_request.description,
            project_id=payment_request.project_id,
            status=payment_request.status.value if hasattr(payment_request.status, 'value') else payment_request.status,
            remarks=payment_request.remarks,
            created_by=current_user.uuid,
            person=payment_request.person,
        )
        db.add(new_payment)
        db.flush()

        # Link items to the payment (only if items exist)
        if payment_request.item_uuids:
            db.add_all([PaymentItem(payment_id=new_payment.uuid, item_id=item_id) for item_id in payment_request.item_uuids])

        # Update the project balance in the ledger
        create_project_balance_entry(
            db=db,
            project_id=payment_request.project_id,
            adjustment=-payment_request.amount,
            description="Payment deduction",
        )

        # Handle multiple file uploads (only if files exist)
        if files:
            upload_dir = constants.UPLOAD_DIR
            os.makedirs(upload_dir, exist_ok=True)

            for file in files:
                file_path = os.path.join(upload_dir, file.filename)
                
                with open(file_path, "wb") as buffer:
                    buffer.write(file.file.read())

                # Save file path in the payment_files table
                new_payment_file = PaymentFile(
                    payment_id=new_payment.uuid,
                    file_path=file_path,
                )
                db.add(new_payment_file)

        # Commit everything at once if all operations succeed
        db.commit()

        return PaymentServiceResponse(
            data={"payment_uuid": new_payment.uuid},
            message="Payment created successfully with multiple files." if files else "Payment created successfully.",
            status_code=201
        ).model_dump()

    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database Error in create_payment API: {str(e)}")
        return PaymentServiceResponse(
            status_code=500,
            data=None,
            message="Database error occurred."
        ).model_dump()

    except Exception as e:
        db.rollback()
        print(f"Error in create_payment API: {str(e)}")
        return PaymentServiceResponse(
            status_code=500,
            data=None,
            message=f"An error occurred: {str(e)}"
        ).model_dump()


# @payment_router.get("", tags=["Payments"], status_code=h_status.HTTP_200_OK)
# def get_all_payments(
#     db: Session = Depends(get_db),
#     amount: Optional[float] = Query(None, description="Filter by payment amount"),
#     project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
#     status: Optional[str] = Query(None, description="Filter by payment status"),
#     start_date: Optional[datetime] = Query(None, description="Filter by start date (created_at)"),
#     end_date: Optional[datetime] = Query(None, description="Filter by end date (created_at)"),
#     recent: Optional[bool] = Query(False, description="Show only last 5 payments if true"),
# ):
#     try:
#         # Step 1: Base Query to Fetch Payment UUIDs if 'recent' is enabled
#         base_query = db.query(Payment.uuid).filter(Payment.is_deleted.is_(False))

#         if recent:
#             base_query = base_query.order_by(desc(Payment.created_at)).limit(5).subquery()

#         query = (
#             db.query(Payment)
#             .outerjoin(PaymentFile)
#             .outerjoin(PaymentItem, Payment.uuid == PaymentItem.payment_id)
#             .outerjoin(Item, PaymentItem.item_id == Item.uuid)
#             .options(joinedload(Payment.payment_files), joinedload(Payment.payment_items).joinedload(PaymentItem.item))
#             .filter(Payment.is_deleted.is_(False))
#         )

#         if recent:
#             query = query.filter(Payment.uuid.in_(db.query(base_query.c.uuid)))

#         # Apply additional filters dynamically
#         if amount is not None:
#             query = query.filter(Payment.amount == amount)
#         if project_id is not None:
#             query = query.filter(Payment.project_id == project_id)
#         if status is not None:
#             query = query.filter(Payment.status == status)
#         if start_date is not None:
#             query = query.filter(Payment.created_at >= start_date)
#         if end_date is not None:
#             query = query.filter(Payment.created_at <= end_date)

#         payments = query.all()
#         payments_data = []

#         for payment in payments:
#             file_paths = [file.file_path for file in payment.payment_files] if payment.payment_files else []

#             # Fetch items associated with the payment
#             item_names = [payment_item.item.name for payment_item in payment.payment_items] if payment.payment_items else []

#             payments_data.append(
#                 PaymentsResponse(
#                     uuid=payment.uuid,
#                     amount=payment.amount,
#                     description=payment.description,
#                     project_id=payment.project_id,
#                     files=file_paths,
#                     items=item_names,  # Include item names
#                     remarks=payment.remarks,
#                     status=payment.status,
#                     created_by=payment.created_by,
#                     person=payment.person,
#                     created_at=payment.created_at.strftime("%Y-%m-%d"),
#                 ).model_dump()
#             )

#         return PaymentServiceResponse(
#             data=payments_data,
#             message="Recent Payments fetched successfully." if recent else "All Payments fetched successfully.",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         print(f"Error in get_all_payments API: {str(e)}")
#         return PaymentServiceResponse(
#             data=None,
#             message=f"An Error Occurred: {str(e)}",
#             status_code=500
#         ).model_dump()


@payment_router.get("", tags=["Payments"], status_code=h_status.HTTP_200_OK)
def get_all_payments(
    db: Session = Depends(get_db),
    amount: Optional[float] = Query(None, description="Filter by payment amount"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (created_at)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (created_at)"),
    recent: Optional[bool] = Query(False, description="Show only last 5 payments if true"),
    person_id: Optional[UUID] = Query(None, description="Filter by person ID"),
    item_id: Optional[UUID] = Query(None, description="Filter by item ID")
):
    """
    Fetches payments, optionally filtering by amount, project, status,
    date range, person, item, and optionally returning only the most recent 5.
    Also returns person name, project name, and created_by user name along with their UUIDs.
    """
    try:
        # If "recent" is enabled, get just the last 5 payment UUIDs
        base_query = db.query(Payment.uuid).filter(Payment.is_deleted.is_(False))
        if recent:
            base_query = base_query.order_by(desc(Payment.created_at)).limit(5).subquery()

        # Join Payment with Project, Person, User, PaymentFile, PaymentItem, and Item
        query = (
            db.query(
                Payment,
                Project.name.label("project_name"),
                Person.name.label("person_name"),
                User.name.label("user_name")
            )
            .outerjoin(Project, Payment.project_id == Project.uuid)
            .outerjoin(Person, Payment.person == Person.uuid)
            .outerjoin(User, Payment.created_by == User.uuid)
            .outerjoin(PaymentFile)
            .outerjoin(PaymentItem, Payment.uuid == PaymentItem.payment_id)
            .outerjoin(Item, PaymentItem.item_id == Item.uuid)
            .filter(Payment.is_deleted.is_(False))
        )

        # Apply the "recent" filter if needed
        if recent:
            query = query.filter(Payment.uuid.in_(db.query(base_query.c.uuid)))

        # Apply additional filters
        if amount is not None:
            query = query.filter(Payment.amount == amount)
        if project_id is not None:
            query = query.filter(Payment.project_id == project_id)
        if status is not None:
            query = query.filter(Payment.status == status)
        if start_date is not None:
            query = query.filter(Payment.created_at >= start_date)
        if end_date is not None:
            query = query.filter(Payment.created_at <= end_date)
        if person_id is not None:
            query = query.filter(Payment.person == person_id)
        if item_id is not None:
            query = query.filter(PaymentItem.item_id == item_id)

        # Execute and retrieve
        results = query.all()
        payments_data = []

        # results is a list of tuples: (Payment, project_name, person_name, user_name)
        for row in results:
            payment = row[0]
            project_name = row.project_name
            person_name = row.person_name
            user_name = row.user_name

            file_paths = [f.file_path for f in payment.payment_files] if payment.payment_files else []
            item_names = [p_item.item.name for p_item in payment.payment_items] if payment.payment_items else []

            payments_data.append(
                PaymentsResponse(
                    uuid=payment.uuid,
                    amount=payment.amount,
                    description=payment.description,
                    # Return project as an object with both ID and name
                    project={
                        "uuid": str(payment.project_id),
                        "name": project_name
                    },
                    # Return person as an object with both ID and name
                    person={
                        "uuid": str(payment.person) if payment.person else None,
                        "name": person_name
                    },
                    # Return user as an object with both ID and name
                    created_by={
                        "uuid": str(payment.created_by),
                        "name": user_name
                    },
                    files=file_paths,
                    items=item_names,
                    remarks=payment.remarks,
                    status=payment.status,
                    created_at=payment.created_at.strftime("%Y-%m-%d"),
                ).model_dump()
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


@payment_router.put("/approve")
def approve_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        """Approve a payment request."""
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return PaymentServiceResponse(
                data=None,
                message=constants.CANT_APPROVE_PAYMENT,
                status_code=403
            ).model_dump()

        payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
        if not payment:
            return PaymentServiceResponse(
                data=None,
                message=constants.PAYMENT_NOT_FOUND,
                status_code=404
            ).model_dump()

        payment.status = PaymentStatus.approved.value
        db.commit()
        return PaymentServiceResponse(
            data=None,
            message="Payment approved successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        print(f"Error in approve_payment API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.put("/decline")
def decline_payment(
    payment_id: UUID,
    remarks: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        """Decline a payment request with remarks."""
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return PaymentServiceResponse(
                data=None,
                message=constants.CANT_DECLINE_PAYMENTS,
                status_code=403
            ).model_dump()

        payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
        if not payment:
            return PaymentServiceResponse(
                data=None,
                message=constants.PAYMENT_NOT_FOUND,
                status_code=404
            ).model_dump()

        payment.status = PaymentStatus.declined.value
        payment.remarks = remarks
        db.commit()
        return PaymentServiceResponse(
            data=None,
            message="Payment declined with remarks",
            status_code=200
        ).model_dump()
    except Exception as e:
        print(f"Error in decline_payment API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        )


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
        existing_person = db.query(Person).filter(
            (Person.account_number == request_data.account_number) |
            (Person.ifsc_code == request_data.ifsc_code)
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
            parent_id=request_data.parent_id  # Link to parent account
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
):
    try:
        query = db.query(
            Person
        ).filter(
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
                    "secondary_accounts": [
                        {
                            "uuid": child.uuid,
                            "name": child.name,
                            "account_number": child.account_number,
                            "ifsc_code": child.ifsc_code,
                            "phone_number": child.phone_number
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
def delete_person(person_uuid: UUID, db: Session = Depends(get_db)):
    try:
        person = db.query(Person).filter(Person.uuid == person_uuid).first()

        if not person:
            raise HTTPException(
                status_code=h_status.HTTP_404_NOT_FOUND,
                detail="Person Does Not Exist",
            )
        person.is_deleted = True
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
def create_item(name: str, category: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        new_item = Item(name=name, category=category)
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
        items_data = [{"uuid": str(item.uuid), "name": item.name, "category": item.category} for item in items]

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
    


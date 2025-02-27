import os
import shutil
import traceback
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi import status as h_status
from sqlalchemy.orm import Session, joinedload
from src.app.database.models import Project
from src.app.database.database import get_db
from src.app.database.models import (
    Payment,
    Person,
    User,
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
from src.app.services.auth_service import get_current_user
from src.app.services.project_service import create_project_balance_entry

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


@payment_router.post("", tags=["Payments"], status_code=h_status.HTTP_201_CREATED)
def create_payment(
    amount: float,
    project_id: UUID,
    status: PaymentStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    description: str = None,
    remarks: str = None,
    person: UUID = None,
    files: List[UploadFile] = File(None),  # Accept multiple files
):
    try:
        """Create a payment request and update project balance."""
        allowed_file_types = ["application/pdf", "image/png", "image/jpeg", "image/jpg", "image/heic"]

        # Validate files
        if files:
            for file in files:
                if file.content_type not in allowed_file_types:
                    return PaymentServiceResponse(
                        status_code=400,
                        data=None,
                        message="Only PDF, PNG, JPEG, JPG, HEIC files are allowed"
                    ).model_dump()

        # Check if the project exists
        project = db.query(Project).filter(Project.uuid == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Create a new payment
        new_payment = Payment(
            amount=amount,
            description=description,
            project_id=project_id,
            status=status.value,
            remarks=remarks,
            created_by=current_user.uuid,
            person=person,
        )

        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)

        # Update the project balance in the ledger
        create_project_balance_entry(
            db=db,
            project_id=project_id,
            adjustment=-amount,
            description="Payment deduction",
        )

        # Handle multiple file uploads
        upload_dir = constants.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Save file path in the payment_files table
            new_payment_file = PaymentFile(
                payment_id=new_payment.uuid,
                file_path=file_path,
            )
            db.add(new_payment_file)

        db.commit()

        return PaymentServiceResponse(
            data={"payment_uuid": new_payment.uuid},
            message="Payment created successfully with multiple files.",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        print(f"Error in create_payment API: {str(e)}")
        return PaymentServiceResponse(
            data=None,
            message=f"An Error Occurred: {str(e)}",
            status_code=500
        ).model_dump()


@payment_router.get("", tags=["Payments"], status_code=h_status.HTTP_200_OK)
def get_all_payments(
    db: Session = Depends(get_db),
    amount: Optional[float] = Query(None, description="Filter by payment amount"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (created_at)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (created_at)"),
    recent: Optional[bool] = Query(False, description="Show only last 5 payments if true"),
):
    try:
        # Step 1: Base Query (fetch latest 5 payments first if recent flag is enabled)
        base_query = db.query(Payment.uuid).filter(Payment.is_deleted.is_(False))

        if recent:
            base_query = base_query.order_by(desc(Payment.created_at)).limit(5).subquery()

        # Step 2: Main Query to Fetch Payments
        query = db.query(Payment).outerjoin(PaymentFile).options(joinedload(Payment.payment_files))

        if recent:
            query = query.filter(Payment.uuid.in_(db.query(base_query.c.uuid)))

        # Apply additional filters dynamically
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

        payments = query.all()
        payments_data = []

        for payment in payments:
            file_paths = [file.file_path for file in payment.payment_files] if payment.payment_files else []

            payments_data.append(
                PaymentsResponse(
                    uuid=payment.uuid,
                    amount=payment.amount,
                    description=payment.description,
                    project_id=payment.project_id,
                    files=file_paths if file_paths else [],
                    remarks=payment.remarks,
                    status=payment.status,
                    created_by=payment.created_by,
                    person=payment.person,
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
            status_code=200
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
        query = db.query(Person).filter(Person.is_deleted.is_(False))

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

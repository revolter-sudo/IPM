import os
import shutil
import traceback
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi import status as h_status
from sqlalchemy.orm import Session
from src.app.database.models import Project
from src.app.database.database import get_db
from src.app.database.models import Payment, Person, User
from src.app.schemas import constants
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas.payment_service_schemas import (
    CreatePerson,
    PaymentsResponse,
    PaymentStatus,
    PersonDetail,
    PaymentServiceResponse
)
from src.app.services.auth_service import get_current_user
from src.app.services.project_service import create_project_balance_entry

payment_router = APIRouter(prefix="/payments", tags=["Payments"])


@payment_router.post(
    "", tags=["Payments"], status_code=h_status.HTTP_201_CREATED
)
def create_payment(
    amount: float,
    project_id: UUID,
    status: PaymentStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    description: str = None,
    remarks: str = None,
    person: UUID = None,
    file: UploadFile = File(None),
):
    try:
        """Create a payment request and update project balance."""
        if file and file.filename:
            if file.content_type not in ["application/pdf"]:
                return PaymentServiceResponse(
                    status_code=400,
                    data=None,
                    message=constants.ONLY_PDFS_ALLOWED
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

        # Handle file upload if present
        if file and file.filename:
            os.makedirs(constants.UPLOAD_DIR, exist_ok=True)
            file_path = f"{constants.UPLOAD_DIR}/{file.filename}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            new_payment.file = file_path
            db.commit()

        return PaymentServiceResponse(
            data={"payment_uuid": new_payment.uuid},
            message="Payment created successfully.",
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
    amount: Optional[float] = Query(
        None, description="Filter by payment amount"
    ),
    description: Optional[str] = Query(
        None, description="Filter by description"
    ),
    project_id: Optional[UUID] = Query(
        None, description="Filter by project ID"
    ),
    created_by: Optional[UUID] = Query(None, description="Filter by creator"),
    status: Optional[str] = Query(
        None, description="Filter by payment status"
    ),
    remarks: Optional[str] = Query(None, description="Filter by remarks"),
    person: Optional[UUID] = Query(None, description="Filter by person UUID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (created_at)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (created_at)"),

):
    try:
        query = db.query(
            Payment.uuid,
            Payment.amount,
            Payment.description,
            Payment.project_id,
            Payment.file,
            Payment.remarks,
            Payment.status,
            Payment.created_by,
            Payment.person,
            Payment.created_at,
        ).filter(Payment.is_deleted.is_(False))

        # Apply filters dynamically based on provided query parameters
        if amount is not None:
            query = query.filter(Payment.amount == amount)
        if description is not None:
            query = query.filter(Payment.description.ilike(f"%{description}%"))
        if project_id is not None:
            query = query.filter(Payment.project_id == project_id)
        if created_by is not None:
            query = query.filter(Payment.created_by == created_by)
        if status is not None:
            query = query.filter(Payment.status == status)
        if remarks is not None:
            query = query.filter(Payment.remarks.ilike(f"%{remarks}%"))
        if person is not None:
            query = query.filter(Payment.person == person)
        if start_date is not None:
            query = query.filter(Payment.created_at >= start_date)
        if end_date is not None:
            query = query.filter(Payment.created_at <= end_date)

        payments = query.all()

        payments_data = [
            PaymentsResponse(
                uuid=payment.uuid,
                amount=payment.amount,
                description=payment.description,
                project_id=payment.project_id,
                file=payment.file,
                remarks=payment.remarks,
                status=payment.status,
                created_by=payment.created_by,
                created_at=payment.created_at.strftime("%Y-%m-%d"),
                person=payment.person,
            ).model_dump()
            for payment in payments
        ]
        return PaymentServiceResponse(
            data=payments_data,
            message="All Payments fetched successfully.",
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
        existing_person = (
            db.query(Person)
            .filter(
                (Person.account_number == request_data.account_number)
                | (Person.ifsc_code == request_data.ifsc_code)
            )
            .first()
        )

        if existing_person:
            return PaymentServiceResponse(
                data=None,
                status_code=400,
                message=constants.PERSON_EXISTS
            ).model_dump()

        new_person = Person(
            name=request_data.name,
            account_number=request_data.account_number,
            ifsc_code=request_data.ifsc_code,
            phone_number=request_data.phone_number,
        )

        db.add(new_person)
        db.flush()

        generated_uuid = new_person.uuid

        db.commit()
        return PaymentServiceResponse(
            data=str(generated_uuid),
            message="Create person successfully.",
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
        query = db.query(
            Person.uuid,
            Person.name,
            Person.account_number,
            Person.ifsc_code,
            Person.phone_number,
        ).filter(Person.is_deleted.is_(False))

        if name:
            query = query.filter(Person.name.ilike(f"%{name}%"))
        if phone_number:
            query = query.filter(Person.phone_number == phone_number)
        if account_number:
            query = query.filter(Person.account_number == account_number)
        if ifsc_code:
            query = query.filter(Person.ifsc_code == ifsc_code)

        persons = query.all()
        persons_data = [
            PersonDetail(
                uuid=person.uuid,
                name=person.name,
                account_number=person.account_number,
                ifsc_code=person.ifsc_code,
                phone_number=person.phone_number,
            ).model_dump()
            for person in persons
        ]
        return PaymentServiceResponse(
            data=persons_data,
            message="All persons info fetched successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        traceback.print_exc()
        print(f"Error in get_all_persons API: {str(e)}")
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

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import shutil
from src.app.database.database import get_db
from src.app.database.models import Payment, User
from src.app.schemas.payment_service_schemas import (
    PaymentStatus
)
from src.app.services.auth_service import get_current_user
import os
from src.app.schemas.auth_service_schamas import UserRole
from src.app.schemas import constants

payment_router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@payment_router.post(
        "/",
        tags=["Payments"],
        status_code=status.HTTP_201_CREATED
    )
def create_payment(
    amount: float,
    project_id: UUID,
    status: PaymentStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    description: str = None,
    remarks: str = None,
    file: UploadFile = File(None)
):
    """Create a payment request."""
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(
            status_code=400,
            detail=constants.ONLY_PDFS_ALLOWED
        )

    new_payment = Payment(
        amount=amount,
        description=description,
        project_id=project_id,
        status=status.value,
        remarks=remarks,
        created_by=current_user.uuid
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    if file:
        os.makedirs(constants.UPLOAD_DIR, exist_ok=True)
        file_path = f"{constants.UPLOAD_DIR}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    new_payment.file = file_path
    db.commit()

    return new_payment


@payment_router.put("/{payment_id}/approve")
def approve_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve a payment request."""
    if current_user.role not in [
        UserRole.SUPER_ADMIN.value,
        UserRole.ADMIN.value,
        UserRole.PROJECT_MANAGER.value
    ]:
        raise HTTPException(
            status_code=403,
            detail=constants.CANT_APPROVE_PAYMENT
        )

    payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=404,
            detail=constants.PAYMENT_NOT_FOUND
        )

    payment.status = PaymentStatus.approved.value
    db.commit()
    return {"message": "Payment approved successfully"}


@payment_router.put("/{payment_id}/decline")
def decline_payment(
    payment_id: UUID,
    remarks: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Decline a payment request with remarks."""
    if current_user.role not in [
        UserRole.SUPER_ADMIN.value,
        UserRole.ADMIN.value,
        UserRole.PROJECT_MANAGER.value
    ]:
        raise HTTPException(
            status_code=403,
            detail=constants.CANT_DECLINE_PAYMENTS
        )

    payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=404,
            detail=constants.PAYMENT_NOT_FOUND
        )

    payment.status = PaymentStatus.declined.value
    payment.remarks = remarks
    db.commit()
    return {"message": "Payment declined with remarks"}


@payment_router.delete("/{payment_id}")
def delete_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a payment request."""
    payment = db.query(Payment).filter(Payment.uuid == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=404,
            detail=constants.PAYMENT_NOT_FOUND
        )

    payment.is_deleted = True
    db.commit()
    return {"message": "Payment request deleted successfully"}

from src.app.sms_service.verify_sms import send_otp, check_otp
from phonenumbers import parse, is_possible_number, format_number, PhoneNumberFormat
from src.app.sms_service.schemas import ForgotPasswordOTPRequest, ForgotPasswordOTPVerify, ForgotPasswordOTPVerifyOnly, ForgotPasswordResetOnly
from src.app.services.auth_service import get_db, AuthServiceResponse
from src.app.database.models import User
from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from passlib.context import CryptContext

sms_service_router = APIRouter(prefix="/sms_service")

pwd_context = CryptContext(
    schemes=["bcrypt"], bcrypt__default_rounds=12, deprecated="auto"
)


def _e164(indian_number: int) -> str:
    p = parse(str(indian_number), "IN")
    if not is_possible_number(p):
        raise HTTPException(status_code=400, detail="Invalid phone number")
    return format_number(p, PhoneNumberFormat.E164)

@sms_service_router.post("/forgot_password/request_otp", tags=["SMS Service"])
def forgot_password_request_otp(payload: ForgotPasswordOTPRequest,
                                db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.phone == payload.phone,
        User.is_deleted.is_(False)
    ).first()
    if not user:
        return AuthServiceResponse(
            data=None,
            status_code=404,
            message="No user found with this phone number."
        ).model_dump()

    send_otp(_e164(payload.phone))          # fire-and-forget
    return AuthServiceResponse(
        data=None,
        message="OTP sent successfully",
        status_code=200
    ).model_dump()


# @sms_service_router.post("/forgot_password/verify_otp", tags=["SMS Service"])
# def forgot_password_verify_otp(payload: ForgotPasswordOTPVerify,
#                                db: Session = Depends(get_db)):
#     if not check_otp(_e164(payload.phone), payload.otp):
#         return AuthServiceResponse(
#             data=None,
#             status_code=400,
#             message="Invalid or expired OTP"
#         ).model_dump()

#     user = db.query(User).filter(
#         User.phone == payload.phone,
#         User.is_deleted.is_(False)
#     ).first()
#     if not user:
#         return AuthServiceResponse(
#             data=None,
#             status_code=404,
#             message="User not found"
#         ).model_dump()

#     user.password_hash = pwd_context.hash(payload.new_password)
#     db.commit()
#     return AuthServiceResponse(
#         data={"uuid": str(user.uuid)},
#         message="Password reset successfully",
#         status_code=200
#     ).model_dump()

@sms_service_router.post("/forgot_password/verify_otp", tags=["SMS Service"])
def verify_otp(payload: ForgotPasswordOTPVerifyOnly, db: Session = Depends(get_db)):
    if not check_otp(_e164(payload.phone), payload.otp):
        return AuthServiceResponse(
            data=None,
            status_code=400,
            message="Invalid or expired OTP"
        ).model_dump()

    user = db.query(User).filter(
        User.phone == payload.phone,
        User.is_deleted.is_(False)
    ).first()

    if not user:
        return AuthServiceResponse(
            data=None,
            status_code=404,
            message="User not found"
        ).model_dump()

    return AuthServiceResponse(
        data={"uuid": str(user.uuid)},
        status_code=200,
        message="OTP verified, you can now reset your password"
    ).model_dump()

@sms_service_router.post("/forgot_password/reset_password", tags=["SMS Service"])
def reset_password(payload: ForgotPasswordResetOnly, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.uuid == payload.uuid,
        User.is_deleted.is_(False)
    ).first()

    if not user:
        return AuthServiceResponse(
            data=None,
            status_code=404,
            message="Invalid or expired session. Please re-verify."
        ).model_dump()

    user.password_hash = pwd_context.hash(payload.new_password)
    db.commit()

    return AuthServiceResponse(
        data=None,
        status_code=200,
        message="Password reset successfully"
    ).model_dump()

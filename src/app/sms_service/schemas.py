from pydantic import BaseModel


class ForgotPasswordOTPRequest(BaseModel):
    phone: int


class ForgotPasswordOTPVerify(BaseModel):
    phone: int
    otp: str
    new_password: str

class ForgotPasswordOTPVerifyOnly(BaseModel):
    phone: str
    otp: str

class ForgotPasswordResetOnly(BaseModel):
    uuid: str
    new_password: str
from pydantic import BaseModel


class ForgotPasswordOTPRequest(BaseModel):
    phone: int


class ForgotPasswordOTPVerify(BaseModel):
    phone: int
    otp: str
    new_password: str

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    phone: int
    password: str
    role: str


class UserLogin(BaseModel):
    phone: int
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

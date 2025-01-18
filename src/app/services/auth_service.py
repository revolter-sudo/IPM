from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from typing import List
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from src.app.database.database import get_db
from src.app.database.models import User
from src.app.schemas.auth_service_schamas import (
    Token,
    UserCreate,
    UserResponse,
    UserRole
)
from uuid import UUID
from sqlalchemy import and_
import logging

# Router Setup
auth_router = APIRouter(prefix="/auth")

# Password Hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    bcrypt__default_rounds=12,
    deprecated="auto"
)


# JWT Configuration
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

# OAuth2 scheme for Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Utility Functions
def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


# Dependency for Role-based Access
def get_current_user(
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(User).filter(
            and_(
                User.uuid == payload.get("sub"),
                User.is_deleted.is_(False),
                User.is_active.is_(True)
            )
        ).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication"
            )
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")


def superadmin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="SuperAdmin privileges required"
        )
    return current_user


# Routes
@auth_router.post(
        "/register",
        response_model=Token,
        tags=["Users"],
        status_code=201
    )
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required)
):
    db_user = db.query(User).filter(
        and_(
            User.phone == user.phone,
            User.is_deleted.is_(False),
            User.is_active.is_(True)
        )
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Phone already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        phone=user.phone,
        password_hash=hashed_password,
        role=user.role.value,
        is_deleted=False,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": str(new_user.uuid)})
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post(
        "/login",
        response_model=Token,
        status_code=201,
        tags=["Users"]
    )
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(
        and_(
            User.phone == int(form_data.username),
            User.is_deleted.is_(False),
            User.is_active.is_(True)
        )
    ).first()
    if not db_user or not verify_password(
        form_data.password,
        db_user.password_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Incorrect phone or password"
        )

    access_token = create_access_token(data={"sub": str(db_user.uuid)})
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.put(
        "/delete/{user_uuid}",
        status_code=204,
        tags=["Users"]
    )
def delete_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required)
):
    try:
        user_data = db.query(User).filter(
            and_(
                User.uuid == user_uuid,
                User.is_deleted.is_(False),
                User.is_active.is_(True)
            )
        ).first()
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User does not exist"
            )

        if user_data.role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="SuperAdmin user cannot be deleted."
            )

        user_data.is_deleted = True
        db.commit()
        db.refresh(user_data)

        return {"result": "User successfully deleted."}

    except Exception as e:
        logging.error(f"Error in delete_user API: {str(e)}")
        raise e


@auth_router.put(
    "/deactivate/{user_uuid}",
    status_code=204,
    tags=["Users"]
)
def deactivate_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required)
):
    try:
        user_data = db.query(User).filter(
            and_(
                User.uuid == user_uuid,
                User.is_deleted.is_(False),
                User.is_active.is_(True)
            )
        ).first()
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User does not exist"
            )

        if user_data.role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="SuperAdmin user cannot be deactivated."
            )

        user_data.is_active = False
        db.commit()
        db.refresh(user_data)

        return {"result": "User successfully deactivated."}
    except Exception as e:
        logging.error(f"Error in deactivate_user API: {str(e)}")
        raise e


@auth_router.put(
    "/activate/{user_uuid}",
    status_code=204,
    tags=["Users"]
)
def activate_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required)
):
    try:
        user_data = db.query(User).filter(
            and_(
                User.uuid == user_uuid,
                User.is_deleted.is_(False),
                User.is_active.is_(True)
            )
        ).first()
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User does not exist"
            )

        if user_data.role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=403,
                detail="SuperAdmin user cannot be activated."
            )

        user_data.is_active = True
        db.commit()
        db.refresh(user_data)

        return {"result": "User successfully activated."}
    except Exception as e:
        logging.error(f"Error in activate_user API: {str(e)}")
        raise e


@auth_router.get(
    "/users",
    tags=["Users"]
)
def list_all_active_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        user_response_data = [
            UserResponse(
                uuid=user.uuid,
                name=user.name,
                phone=user.phone,
                role=user.role,
            ).to_dict()
            for user in users
        ]
        return {"result": user_response_data}
    except Exception as e:
        logging.error(f"Error in list_all_active_users API: {str(e)}")
        raise e


@auth_router.get(
    "/user/{user_uuid}",
    tags=["Users"]
)
def get_user_info(user_uuid: UUID, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(
            and_(
                User.uuid == user_uuid,
                User.is_active.is_(True)
            )
        ).first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User does not exist"
            )

        user_response = UserResponse(
            uuid=user.uuid,
            name=user.name,
            phone=user.phone,
            role=user.role
        )
        return {"result": user_response}
    except Exception as e:
        logging.error(f"Error in get_user_info API: {str(e)}")
        raise e

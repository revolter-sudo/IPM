import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import and_
from sqlalchemy.orm import Session
from uuid import uuid4
from src.app.database.database import get_db
from src.app.database.models import User, Log
from src.app.schemas.auth_service_schamas import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
    AuthServiceResponse
)

# Router Setup
auth_router = APIRouter(prefix="/auth")

# Password Hashing
pwd_context = CryptContext(
    schemes=["bcrypt"], bcrypt__default_rounds=12, deprecated="auto"
)
# print("================================")
# print(f"Password Hash -> {pwd_context.hash('supersecurepassword')}")
# print("================================")

# JWT Configuration
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

bearer_scheme = HTTPBearer()
# OAuth2 scheme for Bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Utility Functions
def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    token = credentials.credentials  # Extract token from Authorization header
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = payload.get("sub")

        if not user_uuid:
            return AuthServiceResponse(
                data=None,
                status_code=401,
                message="Invalid authentication token"
            ).model_dump()

        user = (
            db.query(User)
            .filter(
                User.uuid == user_uuid,
                User.is_deleted.is_(False),
                User.is_active.is_(True),
            )
            .first()
        )

        if not user:
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User Not Found"
            ).model_dump()

        return user

    except JWTError:
        return AuthServiceResponse(
            data=None,
            status_code=401,
            message="Invalid authentication"
        ).model_dump()


def superadmin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPER_ADMIN:
        return AuthServiceResponse(
                data=None,
                status_code=403,
                message="SuperAdmin privileges required"
            ).model_dump()
    return current_user


# Routes
@auth_router.post(
    "/register",
    tags=["Users"],
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
) -> dict:
    db_user = (
        db.query(User)
        .filter(
            and_(
                User.phone == user.phone,
                User.is_deleted.is_(False),
                User.is_active.is_(True),
            )
        )
        .first()
    )
    if db_user:
        return AuthServiceResponse(
                data=None,
                status_code=400,
                message="Phone already registered"
            ).model_dump()
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        phone=user.phone,
        password_hash=hashed_password,
        role=user.role.value,
        is_deleted=False,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    access_token = create_access_token(data={"sub": str(new_user.uuid)})
    response = {"access_token": access_token, "token_type": "bearer"}
    return AuthServiceResponse(
        data=response,
        message="User reginstered successfully",
        status_code=201
    ).model_dump()


@auth_router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    tags=["Users"]
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
) -> dict:
    db_user = (
        db.query(User)
        .filter(
            User.phone == login_data.phone,
            User.is_deleted.is_(False),
            User.is_active.is_(True),
        )
        .first()
    )

    if not db_user or not verify_password(
        login_data.password, db_user.password_hash
    ):
        return AuthServiceResponse(
                data=None,
                status_code=400,
                message="Incorrect phone or password"
            ).model_dump()
    user_data = UserResponse(
        uuid=db_user.uuid,
        name=db_user.name,
        phone=db_user.phone,
        role=db_user.role
    ).to_dict()
    access_token = create_access_token(data={"sub": str(db_user.uuid)})
    response = {
        "access_token": access_token,
        "token_type": "bearer",
        "user_data": user_data
    }
    return AuthServiceResponse(
        data=response,
        message="User logged in successfully",
        status_code=201
    ).model_dump()


@auth_router.put(
        "/delete",
        status_code=status.HTTP_201_CREATED,
        tags=["Users"]
    )
def delete_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    try:
        user_data = (
            db.query(User)
            .filter(
                and_(
                    User.uuid == user_uuid,
                    User.is_deleted.is_(False),
                    User.is_active.is_(True),
                )
            )
            .first()
        )
        if not user_data:
            raise HTTPException(status_code=404, detail="User does not exist")

        if user_data.role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=403, detail="SuperAdmin user cannot be deleted."
            )

        user_data.is_deleted = True
        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Delete",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(user_data)
        return AuthServiceResponse(
            data=None,
            message="User deleted successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in delete_user API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in delete_user API: {str(e)}"
        ).model_dump()


@auth_router.put("/deactivate", status_code=status.HTTP_200_OK, tags=["Users"])
def deactivate_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    try:
        user_data = (
            db.query(User)
            .filter(
                and_(
                    User.uuid == user_uuid,
                    User.is_deleted.is_(False),
                    User.is_active.is_(True),
                )
            )
            .first()
        )
        if not user_data:
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User does not exist"
            ).model_dump()

        if user_data.role == UserRole.SUPER_ADMIN:
            return AuthServiceResponse(
                data=None,
                status_code=403,
                message="SuperAdmin user cannot be deactivated."
            ).model_dump()

        user_data.is_active = False
        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Deactivate",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(user_data)
        return AuthServiceResponse(
            data=None,
            message="User deactivated successfully.",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in deactivate_user API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in deactivate_user API: {str(e)}"
        ).model_dump()


@auth_router.put("/activate", status_code=status.HTTP_200_OK, tags=["Users"])
def activate_user(
    user_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    try:
        user_data = (
            db.query(User)
            .filter(
                and_(
                    User.uuid == user_uuid,
                    User.is_deleted.is_(False),
                )
            )
            .first()
        )
        if not user_data:
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User does not exist"
            ).model_dump()

        if user_data.role == UserRole.SUPER_ADMIN:
            return AuthServiceResponse(
                data=None,
                status_code=403,
                message="SuperAdmin user cannot be activated."
            ).model_dump()

        user_data.is_active = True
        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Activate",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(user_data)
        return AuthServiceResponse(
            data=None,
            message="User activated successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in activate_user API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in activate_user API: {str(e)}"
        ).model_dump()


@auth_router.get("/users", status_code=status.HTTP_200_OK, tags=["Users"])
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
        return AuthServiceResponse(
            data=user_response_data,
            message="All users fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in list_all_active_users API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in list_all_active_users API: {str(e)}"
        ).model_dump()


@auth_router.get("/user", tags=["Users"])
def get_user_info(user_uuid: UUID, db: Session = Depends(get_db)):
    try:
        user = (
            db.query(User)
            .filter(and_(User.uuid == user_uuid, User.is_active.is_(True)))
            .first()
        )

        if not user:
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User does not exist"
            ).model_dump()

        user_response = UserResponse(
            uuid=user.uuid, name=user.name, phone=user.phone, role=user.role
        )
        return AuthServiceResponse(
            data=user_response,
            message="User info fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        logging.error(f"Error in get_user_info API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in get_user_info API: {str(e)}"
        ).model_dump()

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Security,
    status,
    UploadFile,
    File,
    Query
)
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
from src.app.database.models import User, Log, Person, UserTokenMap
from src.app.schemas.auth_service_schamas import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
    AuthServiceResponse,
    ForgotPasswordRequest,
    UserLogout,
    UserEdit
)
from src.app.notification.notification_service import (
    subscribe_news,
    unsubscribe_news
)
from src.app.schemas import constants
import os
from typing import Optional

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


@auth_router.post("/upload_photo", tags=["Users"])
def upload_user_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a photo for the current user and updates `photo_path`.
    Returns the path/URL so the frontend can load it.
    """
    try:
        # 1) Define your upload directory (following your pattern in payment_service.py)
        upload_dir = os.path.join(constants.UPLOAD_DIR, "users")  # e.g. "uploads/users"
        os.makedirs(upload_dir, exist_ok=True)

        # 2) Create a unique filename or use the original filename
        #    e.g. "abc1234_filename.jpg"
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{str(uuid4())}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)

        # 3) Save the file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        # 4) Update user.photo_path.
        #    If you have a HOST_URL to build a public URL, you can do that too.
        # current_user.photo_path = file_path
        current_user.photo_path = f"{constants.HOST_URL}/uploads/payments/users/{unique_filename}"
        # Alternatively, you can store the final URL if you have a static server for images:

        db.commit()
        db.refresh(current_user)

        return AuthServiceResponse(
            data={"photo_path": current_user.photo_path},
            message="User photo uploaded successfully.",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return AuthServiceResponse(
            data=None,
            message=f"An error occurred: {str(e)}",
            status_code=500
        ).model_dump()


@auth_router.post("/forgot_password", tags=["Users"])
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Resets a user's password, given a phone number and a new password.
    In production, you would typically verify OTP or email link, but
    here it's a simple, direct reset for demonstration.
    """
    # 1) Find user by phone
    user = (
        db.query(User)
        .filter(
            User.phone == payload.phone,
            User.is_deleted.is_(False)
        )
        .first()
    )
    if not user:
        return AuthServiceResponse(
            data=None,
            status_code=404,
            message="No user found with this phone number."
        ).model_dump()

    # 2) Hash and set new password
    hashed = pwd_context.hash(payload.new_password)
    user.password_hash = hashed
    db.commit()
    db.refresh(user)

    # 3) Return success
    return AuthServiceResponse(
        data={
            "uuid": str(user.uuid),
            "phone": user.phone
        },
        message="Password reset successfully",
        status_code=200
    ).model_dump()


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
    db.flush()

    new_person = Person(
        name=user.person.name,
        phone_number=user.person.phone_number,
        account_number=user.person.account_number,
        ifsc_code=user.person.ifsc_code,
        user_id=new_user.uuid
    )
    db.add(new_person)
    db.commit()
    db.refresh(new_user)
    db.refresh(new_person)
    access_token = create_access_token(data={"sub": str(new_user.uuid)})
    response = {"access_token": access_token, "token_type": "bearer"}
    return AuthServiceResponse(
        data=response,
        message="User reginstered successfully",
        status_code=201
    ).model_dump()


def check_or_add_token(
    user_id: UUID,
    fcm_token: str,
    device_id: int,
    db: Session
):
    try:
        data = db.query(UserTokenMap).filter(
            UserTokenMap.device_id == device_id
        ).first()
        if data:
            data.fcm_token = fcm_token
        else:
            user_token_data = UserTokenMap(
                user_id=user_id,
                fcm_token=fcm_token,
                device_id=device_id,
            )
            db.add(user_token_data)
        db.commit()
    except Exception as e:
        db.rollback()
        return AuthServiceResponse(
            data=None,
            message=f"Error while check_or_add_token: {str(e)}",
            status_code=500
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

    # Restrict login to only superadmin and admin roles
    if db_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
        return AuthServiceResponse(
            data=None,
            status_code=403,
            message="Only admin can access"
        ).model_dump()

    user_data = UserResponse(
        uuid=db_user.uuid,
        name=db_user.name,
        phone=db_user.phone,
        role=db_user.role,
        photo_path=db_user.photo_path
    ).to_dict()
    access_token = create_access_token(data={"sub": str(db_user.uuid)})
    if login_data.fcm_token:
        check_or_add_token(
            user_id=db_user.uuid,
            fcm_token=login_data.fcm_token,
            device_id=login_data.device_id,
            db=db
        )
        subscribe_news(
            tokens=login_data.fcm_token,
            topic=db_user.uuid
        )
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


@auth_router.post(
        "/logout",
        status_code=status.HTTP_201_CREATED,
        tags=["Users"]
)
def logout_user(
    user_data: UserLogout,
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(
            User.uuid == user_data.user_id,
            User.is_deleted.is_(False)
        ).first()
        if not user:
            return AuthServiceResponse(
                data=None,
                message="User Does not exist",
                status_code=404
            ).model_dump()
        user_token = db.query(UserTokenMap.fcm_token).filter(
            UserTokenMap.device_id == user_data.device_id
        ).first()
        if user_token:
            unsubscribe_news(
                tokens=user_token[0],
                topic=str(user.uuid)
            )
            logging.info("User unsubscribed successfully.")
        else:
            logging.info("Issue in unsubscribing user.")
        return AuthServiceResponse(
            data=None,
            message="User Logged Out Successfully!",
            status_code=201
        ).model_dump()

    except Exception as e:
        return AuthServiceResponse(
            data=None,
            message=f"Error in logout_user API: {str(e)}",
            status_code=200
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
        users = db.query(User).filter(
            User.is_active.is_(True),
            User.is_deleted.is_(False)
        ).all()

        user_response_data = []
        for user in users:
            person_data = None
            if user.person:
                person_data = {
                    "uuid": str(user.person.uuid),
                    "name": user.person.name,
                    "account_number": user.person.account_number,
                    "ifsc_code": user.person.ifsc_code,
                    "phone_number": user.person.phone_number,
                }

            user_response_data.append({
                "uuid": str(user.uuid),
                "name": user.name,
                "phone": user.phone,
                "role": user.role,
                "photo_path": user.photo_path,
                "person": person_data
            })

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
            message=f"Error fetching users: {str(e)}"
        ).model_dump()


# @auth_router.get("/user", tags=["Users"])
# def get_user_info(user_uuid: UUID, db: Session = Depends(get_db)):
#     try:
#         user = (
#             db.query(User)
#             .filter(and_(User.uuid == user_uuid, User.is_active.is_(True)))
#             .first()
#         )

#         if not user:
#             return AuthServiceResponse(
#                 data=None,
#                 status_code=404,
#                 message="User does not exist"
#             ).model_dump()

#         person_data = None
#         if user.person:
#             person_data = {
#                 "uuid": str(user.person.uuid),
#                 "name": user.person.name,
#                 "account_number": user.person.account_number,
#                 "ifsc_code": user.person.ifsc_code,
#                 "phone_number": user.person.phone_number,
#             }

#         user_response = {
#             "uuid": str(user.uuid),
#             "name": user.name,
#             "phone": user.phone,
#             "role": user.role,
#             "photo_path": user.photo_path,
#             "person": person_data
#         }

#         return AuthServiceResponse(
#             data=user_response,
#             message="User info fetched successfully",
#             status_code=200
#         ).model_dump()

#     except Exception as e:
#         logging.error(f"Error in get_user_info API: {str(e)}")
#         return AuthServiceResponse(
#             data=None,
#             status_code=500,
#             message=f"Error fetching user info: {str(e)}"
#         ).model_dump()


@auth_router.get("/user", tags=["Users"])
def get_user_info(user_uuid: UUID, db: Session = Depends(get_db)):
    try:
        user = (
            db.query(User)
            .filter(
                User.uuid == user_uuid,
                User.is_active.is_(True),
                User.is_deleted.is_(False)  # <- optionally ensure not deleted
            )
            .first()
        )

        if not user:
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User does not exist"
            ).model_dump()

        # If user has a linked Person row, gather its data (including children)
        person_data = None
        if user.person:
            person_record = user.person
            person_data = {
                "uuid": str(person_record.uuid),
                "name": person_record.name,
                "account_number": person_record.account_number,
                "ifsc_code": person_record.ifsc_code,
                "phone_number": person_record.phone_number,
                "parent_id": person_record.parent_id,
                "upi_number": person_record.upi_number,
                "secondary_accounts": [
                    {
                        "uuid": str(child.uuid),
                        "name": child.name,
                        "account_number": child.account_number,
                        "ifsc_code": child.ifsc_code,
                        "phone_number": child.phone_number,
                        "upi_number": child.upi_number
                    }
                    for child in person_record.children
                ]
            }

        user_response = {
            "uuid": str(user.uuid),
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "photo_path": user.photo_path,
            "person": person_data
        }

        return AuthServiceResponse(
            data=user_response,
            message="User info fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred: {str(e)}"
        ).model_dump()


@auth_router.put(
    "/edit-user/{user_uuid}",
    tags=["Users"],
    status_code=status.HTTP_200_OK
)
def edit_user(
    user_uuid: UUID,
    user_data: UserEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required),
):
    """
    Edit user information including person data.
    Only superadmin can edit users.
    """
    try:
        # Find the user
        user = db.query(User).filter(
            User.uuid == user_uuid,
            User.is_deleted.is_(False)
        ).first()

        if not user:
            return AuthServiceResponse(
                data=None,
                status_code=404,
                message="User not found"
            ).model_dump()

        # Update user fields if provided
        if user_data.name:
            user.name = user_data.name

        if user_data.phone:
            # Check if phone is already used by another user
            existing_user = db.query(User).filter(
                User.phone == user_data.phone,
                User.uuid != user_uuid,
                User.is_deleted.is_(False)
            ).first()

            if existing_user:
                return AuthServiceResponse(
                    data=None,
                    status_code=400,
                    message="Phone number already in use by another user"
                ).model_dump()

            user.phone = user_data.phone

        if user_data.role:
            user.role = user_data.role.value

        # Update person data if provided
        if user_data.person:
            # Get or create person record
            person = user.person

            if not person:
                # Create new person if it doesn't exist
                person = Person(user_id=user.uuid)
                db.add(person)
                db.flush()

            # Update person fields
            if user_data.person.name:
                person.name = user_data.person.name

            if user_data.person.account_number:
                person.account_number = user_data.person.account_number

            if user_data.person.ifsc_code:
                person.ifsc_code = user_data.person.ifsc_code

            if user_data.person.phone_number:
                person.phone_number = user_data.person.phone_number

            if user_data.person.upi_number:
                person.upi_number = user_data.person.upi_number

            if user_data.person.parent_id:
                person.parent_id = user_data.person.parent_id

        # Create log entry
        log_entry = Log(
            uuid=str(uuid4()),
            entity="User",
            action="Edit",
            entity_id=user_uuid,
            performed_by=current_user.uuid,
        )
        db.add(log_entry)

        # Commit changes
        db.commit()
        db.refresh(user)

        # Prepare response
        person_data = None
        if user.person:
            person_data = {
                "uuid": str(user.person.uuid),
                "name": user.person.name,
                "account_number": user.person.account_number,
                "ifsc_code": user.person.ifsc_code,
                "phone_number": user.person.phone_number,
                "upi_number": user.person.upi_number
            }

        return AuthServiceResponse(
            data={
                "uuid": str(user.uuid),
                "name": user.name,
                "phone": user.phone,
                "role": user.role,
                "photo_path": user.photo_path,
                "person": person_data
            },
            message="User updated successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        db.rollback()
        logging.error(f"Error in edit_user API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error updating user: {str(e)}"
        ).model_dump()


@auth_router.get("/persons", status_code=status.HTTP_200_OK, tags=["Persons"])
def get_persons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    name: Optional[str] = Query(None, description="Filter by name"),
    phone: Optional[str] = Query(None, description="Filter by phone number"),
):
    """
    Get all persons with optional filters. This endpoint provides a simplified view
    of persons for frontend dropdowns and selections.
    """
    try:
        query = db.query(Person).filter(
            Person.is_deleted.is_(False),
        )

        # Apply filters if provided
        if name:
            query = query.filter(Person.name.ilike(f"%{name}%"))
        if phone:
            query = query.filter(Person.phone_number == phone)

        persons = query.all()
        persons_data = []

        for person in persons:
            persons_data.append({
                "uuid": str(person.uuid),
                "name": person.name,
                "phone_number": person.phone_number,
                "account_number": person.account_number,
                "ifsc_code": person.ifsc_code,
                "upi_number": person.upi_number
            })

        return AuthServiceResponse(
            data=persons_data,
            message="Persons fetched successfully",
            status_code=200
        ).model_dump()
    except Exception as e:
        db.rollback()
        logging.error(f"Error in get_persons API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching persons: {str(e)}"
        ).model_dump()

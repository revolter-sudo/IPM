from uuid import UUID
from datetime import datetime, timedelta
from src.app.utils.logging_config import get_logger

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
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload
from uuid import uuid4
from src.app.database.database import get_db, settings
from src.app.database.models import User, Log, Person, UserTokenMap , UserData
from src.app.schemas.auth_service_schamas import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
    AuthServiceResponse,
    ForgotPasswordRequest,
    UserLogout,
    UserEdit,
    OutsideUserLogin,
    PersonWithRole,
    RoleBasedPersonQueryRequest,
    RoleBasedPersonQueryResponse,
    UpdatePersonRoleRequest,
    UpdatePersonRoleResponse
)
from src.app.notification.notification_service import (
    subscribe_news,
    unsubscribe_news
)
from src.app.schemas import constants
import os
import redis
from typing import Optional
from fastapi import Request

# Initialize logger
logger = get_logger(__name__)

# Redis client for token blacklisting
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=int(settings.REDIS_PORT),
        decode_responses=True
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis client initialized for token blacklisting")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Token blacklisting disabled.")
    redis_client = None

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


# Token Blacklisting Functions
def blacklist_token(jti: str, exp_timestamp: int):
    """Add token to blacklist until its natural expiration"""
    if redis_client:
        try:
            # Calculate TTL (time to live) until token expires
            current_time = datetime.utcnow().timestamp()
            ttl = max(int(exp_timestamp - current_time), 1)
            redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
            logger.info(f"Token {jti} blacklisted for {ttl} seconds")
        except Exception as e:
            logger.error(f"Failed to blacklist token {jti}: {e}")


def is_token_blacklisted(jti: str) -> bool:
    """Check if token is blacklisted"""
    if redis_client:
        try:
            return redis_client.exists(f"blacklist:{jti}")
        except Exception as e:
            logger.error(f"Failed to check blacklist for token {jti}: {e}")
    return False


# Utility Functions
def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, request_ip: str = None):
    to_encode = data.copy()
    jti = str(uuid4())  # Unique token identifier for blacklisting
    iat = datetime.utcnow()  # Issued at timestamp

    # Always add JTI and IAT for security
    to_encode.update({
        "jti": jti,
        "iat": iat
    })

    # Environment-based token expiration
    if settings.ENVIRONMENT.upper() == "LOCAL":
        # No expiration for LOCAL environment
        logger.info(f"Created LOCAL token with JTI: {jti} (no expiration)")
    else:
        # Use configured expiration for other environments (DEV, STAGING, PROD)
        expire_minutes = settings.JWT_TOKEN_EXPIRE_MINUTES
        if expire_minutes > 0:
            expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
            to_encode.update({"exp": expire})
            logger.info(f"Created token with JTI: {jti}, expires in {expire_minutes} minutes")

        # Optional: Add IP binding for extra security
        if request_ip and settings.ENABLE_IP_VALIDATION:
            to_encode.update({"ip": request_ip})
            logger.info(f"Token {jti} bound to IP: {request_ip}")

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    token = credentials.credentials  # Extract token from Authorization header
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_uuid = payload.get("sub")
        jti = payload.get("jti")  # Token identifier

        if not user_uuid:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        # Check if token is blacklisted
        if jti and is_token_blacklisted(jti):
            logger.warning(f"Blacklisted token used: {jti}")
            raise HTTPException(
                status_code=401,
                detail="Token has been revoked"
            )

        # Optional: Validate IP binding
        if settings.ENABLE_IP_VALIDATION:
            token_ip = payload.get("ip")
            # Note: You'd need to get current request IP here
            # This is a placeholder for IP validation logic

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
            raise HTTPException(
                status_code=404,
                detail="User Not Found"
            )

        return user

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication"
        )


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
        upload_dir = os.path.join(constants.UPLOAD_DIR, "users")  # e.g. "uploads/payments/users"
        os.makedirs(upload_dir, exist_ok=True)

        # 2) Create a unique filename or use the original filename
        #    e.g. "abc1234_filename.jpg"
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{str(uuid4())}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)

        # 3) Save the file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        # 4) Update user.photo_path with the URL that will be accessible through nginx
        current_user.photo_path = f"{constants.HOST_URL}/uploads/payments/users/{unique_filename}"

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
def forgot_password(
    payload: ForgotPasswordRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

    # Try to find existing person by phone_number or account_number
    existing_person = db.query(Person).filter(
        (Person.phone_number == user.person.phone_number) &
        (Person.account_number == user.person.account_number)
    ).first()

    if existing_person:
        # Link existing person to new user
        existing_person.user_id = new_user.uuid
        db.add(existing_person)
        db.commit()
        db.refresh(new_user)
        db.refresh(existing_person)
        person_to_return = existing_person
    else:
        # Create new person as before
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
        person_to_return = new_person

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
    # current_user: User = Depends(get_current_user),
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

    # # Restrict login to only superadmin and admin roles
    # if db_user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
    #     return AuthServiceResponse(
    #         data=None,
    #         status_code=403,
    #         message="Only admin can access"
    #     ).model_dump()

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
        logger.error(f"Error in delete_user API: {str(e)}")
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
):
    try:
        # Extract and blacklist the current token
        token = credentials.credentials
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                blacklist_token(jti, exp)
                logger.info(f"Token {jti} blacklisted during logout")
        except Exception as e:
            logger.warning(f"Failed to blacklist token during logout: {e}")

        user = db.query(User).filter(
            User.uuid == user_data.user_id
        ).first()

        user_token = db.query(UserTokenMap.fcm_token).filter(
            UserTokenMap.device_id == user_data.device_id
        ).first()
        if user_token:
            unsubscribe_news(
                tokens=user_token[0],
                topic=str(user.uuid)
            )
            logger.info("User unsubscribed successfully.")
        else:
            logger.info("Issue in unsubscribing user.")

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
        logger.error(f"Error in deactivate_user API: {str(e)}")
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
        logger.error(f"Error in activate_user API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error in activate_user API: {str(e)}"
        ).model_dump()


@auth_router.get("/users", status_code=status.HTTP_200_OK, tags=["Users"])
def list_all_active_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        users = db.query(User).filter(
            User.is_active.is_(True),
            User.is_deleted.is_(False)
        ).order_by(User.id.desc()).all()

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
        logger.error(f"Error in list_all_active_users API: {str(e)}")
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
#                 "uuid": user.person.uuid,
#                 "name": user.person.name,
#                 "account_number": user.person.account_number,
#                 "ifsc_code": user.person.ifsc_code,
#                 "phone_number": user.person.phone_number,
#             }

#         user_response = {
#             "uuid": user.uuid,
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
#         logger.error(f"Error in get_user_info API: {str(e)}")
#         return AuthServiceResponse(
#             data=None,
#             status_code=500,
#             message=f"Error fetching user info: {str(e)}"
#         ).model_dump()


@auth_router.get("/user", tags=["Users"])
def get_user_info(
    user_uuid: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
        logger.error(f"Error in edit_user API: {str(e)}")
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
        logger.error(f"Error in get_persons API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching persons: {str(e)}")
    

@auth_router.post(
    '/register_and_save_user',
    tags=['non-user']
)
def register_and_outside_user(
    data: OutsideUserLogin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    phone = str(data.phone_number)
    existing = db.query(UserData).filter(UserData.phone_number == phone).first()
    if existing:
        return AuthServiceResponse(
            data=None,
            message=(
                "You’ve already submitted a request with this number, "
                "our team is looking into it and will reach out shortly."
            ),
            status_code=200
        )
    try:
        user_data = UserData(
            name=data.name,
            email=data.email,
            phone_number=str(data.phone_number),
            password=data.password
        )
        db.add(user_data)
        db.commit()
        db.refresh(user_data)
        return AuthServiceResponse(
            data=None,
            message="We have received your request, our team will reach out to you soon.",
            status_code=201
        )
    except Exception as e:
        db.rollback()
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred: {str(e)}"
        ).model_dump()


@auth_router.get(
    '/outside_users',
    status_code=status.HTTP_200_OK,
    tags=['non-user']
)
def list_outside_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(superadmin_required)
):
    """
    List all outside users who have registered through the register_and_outside_user endpoint.
    Only accessible by SuperAdmin users.
    """
    try:
        outside_users = db.query(UserData).all()

        outside_users_data = []
        for user in outside_users:
            outside_users_data.append({
                "uuid": str(user.uuid),
                "name": user.name,
                "email": user.email,
                "phone_number": user.phone_number,
                "password": user.password,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })

        return AuthServiceResponse(
            data=outside_users_data,
            message="Outside users fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logger.error(f"Error in list_outside_users API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching outside users: {str(e)}"
        ).model_dump()


@auth_router.get("/persons/by-role", status_code=status.HTTP_200_OK, tags=["Persons"])
def get_persons_by_role(
    role: UserRole = Query(..., description="Role to filter persons by"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all persons with a specific role from two sources:
    1. Person records that have the specified role directly assigned
    2. Person records linked to Users who have the specified role

    Results are combined and deduplicated to avoid returning the same Person twice.
    Access is restricted to Admin, Super Admin, and Project Manager roles.

    Args:
        role: UserRole enum value to filter persons by
        db: Database session
        current_user: Current authenticated user

    Returns:
        JSON response with list of PersonWithRole objects

    Raises:
        403: If user doesn't have required permissions
        400: If invalid role is provided
        500: If database error occurs
    """
    try:
        # Validate current user
        if not current_user or not hasattr(current_user, 'role'):
            return AuthServiceResponse(
                data=None,
                message="Invalid user session",
                status_code=401
            ).model_dump()

        # Check if current user has permission to access this endpoint
        if current_user.role not in [
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return AuthServiceResponse(
                data=None,
                message="Access denied. Admin, Super Admin, or Project Manager privileges required.",
                status_code=403
            ).model_dump()

        # Validate role parameter
        if not role:
            return AuthServiceResponse(
                data=None,
                message="Role parameter is required",
                status_code=400
            ).model_dump()

        # Convert role enum to string value for database query
        role_value = role.value

        # Query 1: Get persons with the role directly assigned
        try:
            persons_with_direct_role = db.query(Person).filter(
                Person.role == role_value,
                Person.is_deleted.is_(False)
            ).all()
        except Exception as e:
            logger.error(f"Error querying persons with direct role '{role_value}': {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error retrieving persons with direct role assignment",
                status_code=500
            ).model_dump()

        # Query 2: Get persons linked to users with the specified role
        try:
            persons_with_user_role = db.query(Person).join(
                User, Person.user_id == User.uuid
            ).filter(
                User.role == role_value,
                User.is_deleted.is_(False),
                User.is_active.is_(True),
                Person.is_deleted.is_(False)
            ).all()
        except Exception as e:
            logger.error(f"Error querying persons with user role '{role_value}': {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error retrieving persons with user role assignment",
                status_code=500
            ).model_dump()

        # Combine results and deduplicate by person UUID
        combined_persons = {}

        # Add persons with direct role
        try:
            for person in persons_with_direct_role:
                if not person or not hasattr(person, 'uuid'):
                    logger.warning(f"Invalid person object found in direct role query")
                    continue

                person_data = PersonWithRole(
                    uuid=person.uuid,
                    name=person.name or "",
                    phone_number=person.phone_number or "",
                    account_number=person.account_number,
                    ifsc_code=person.ifsc_code,
                    upi_number=person.upi_number,
                    role=person.role or role_value,
                    role_source="person",
                    user_id=person.user_id
                )
                combined_persons[str(person.uuid)] = person_data
        except Exception as e:
            logger.error(f"Error processing persons with direct role: {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error processing persons with direct role assignment",
                status_code=500
            ).model_dump()

        # Add persons with user role (only if not already added)
        try:
            for person in persons_with_user_role:
                if not person or not hasattr(person, 'uuid'):
                    logger.warning(f"Invalid person object found in user role query")
                    continue

                person_uuid_str = str(person.uuid)
                if person_uuid_str not in combined_persons:
                    # Get the user's role for this person
                    user = None
                    if person.user_id:
                        try:
                            user = db.query(User).filter(User.uuid == person.user_id).first()
                        except Exception as e:
                            logger.warning(f"Error fetching user for person {person.uuid}: {str(e)}")

                    person_data = PersonWithRole(
                        uuid=person.uuid,
                        name=person.name or "",
                        phone_number=person.phone_number or "",
                        account_number=person.account_number,
                        ifsc_code=person.ifsc_code,
                        upi_number=person.upi_number,
                        role=user.role if user else role_value,
                        role_source="user",
                        user_id=person.user_id
                    )
                    combined_persons[person_uuid_str] = person_data
        except Exception as e:
            logger.error(f"Error processing persons with user role: {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error processing persons with user role assignment",
                status_code=500
            ).model_dump()

        # Convert to list and sort by name
        try:
            result_persons = list(combined_persons.values())
            result_persons.sort(key=lambda x: x.name if x.name else "")
        except Exception as e:
            logger.error(f"Error sorting results: {str(e)}")
            result_persons = list(combined_persons.values())

        # Create response
        try:
            return RoleBasedPersonQueryResponse(
                data=result_persons,
                message=f"Persons with role '{role_value}' fetched successfully. Found {len(result_persons)} persons.",
                status_code=200
            ).to_dict()
        except Exception as e:
            logger.error(f"Error creating response: {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error formatting response data",
                status_code=500
            ).model_dump()

    except Exception as e:
        logger.error(f"Error in get_persons_by_role API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error fetching persons by role: {str(e)}"
        ).model_dump()


@auth_router.put("/persons/{person_id}/role", status_code=status.HTTP_200_OK, tags=["Persons"])
def update_person_role(
    person_id: UUID,
    request_data: UpdatePersonRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add or update role for an existing person.

    This endpoint allows authorized users to assign or remove roles from persons.
    Setting role to null will remove the role assignment.

    Access is restricted to Admin and Super Admin roles only.

    Args:
        person_id: UUID of the person to update
        request_data: UpdatePersonRoleRequest containing the role to assign
        db: Database session
        current_user: Current authenticated user

    Returns:
        JSON response with updated person information

    Raises:
        400: If person not found or invalid role
        401: If user session is invalid
        403: If user doesn't have required permissions
        500: If database error occurs
    """
    try:
        # Validate current user
        if not current_user or not hasattr(current_user, 'role'):
            return AuthServiceResponse(
                data=None,
                message="Invalid user session",
                status_code=401
            ).model_dump()

        # Check if current user has permission to update person roles
        # Only Admin and Super Admin can assign roles to persons
        if current_user.role not in [
            UserRole.ADMIN.value,
            UserRole.SUPER_ADMIN.value,
        ]:
            return AuthServiceResponse(
                data=None,
                message="Access denied. Admin or Super Admin privileges required.",
                status_code=403
            ).model_dump()

        # Validate person_id parameter
        if not person_id:
            return AuthServiceResponse(
                data=None,
                message="Person ID is required",
                status_code=400
            ).model_dump()

        # Find the person to update
        try:
            person = db.query(Person).filter(
                Person.uuid == person_id,
                Person.is_deleted.is_(False)
            ).first()
        except Exception as e:
            logger.error(f"Error querying person {person_id}: {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error retrieving person data",
                status_code=500
            ).model_dump()

        if not person:
            return AuthServiceResponse(
                data=None,
                message="Person not found or has been deleted",
                status_code=404
            ).model_dump()

        # Get the role value (can be None to remove role)
        role_value = request_data.role.value if request_data.role else None

        # Update the person's role
        try:
            old_role = person.role
            person.role = role_value
            db.commit()
            db.refresh(person)
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating person role for {person_id}: {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error updating person role",
                status_code=500
            ).model_dump()

        # Prepare response data
        try:
            response_data = {
                "person_id": str(person.uuid),
                "name": person.name,
                "phone_number": person.phone_number,
                "old_role": old_role,
                "new_role": role_value,
                "updated_by": str(current_user.uuid),
                "updated_at": datetime.now().isoformat()
            }

            message = f"Person role updated successfully."
            if role_value:
                message += f" Role set to '{role_value}'."
            else:
                message += " Role removed."

            return UpdatePersonRoleResponse(
                data=response_data,
                message=message,
                status_code=200
            ).to_dict()
        except Exception as e:
            logger.error(f"Error creating response for person {person_id}: {str(e)}")
            return AuthServiceResponse(
                data=None,
                message="Error formatting response data",
                status_code=500
            ).model_dump()

    except Exception as e:
        logger.error(f"Error in update_person_role API: {str(e)}")
        return AuthServiceResponse(
            data=None,
            status_code=500,
            message=f"Error updating person role: {str(e)}"
        ).model_dump()
